from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.project import Project
from app.models.media_version import MediaVersion
from app.models.project_member import ProjectMember
from app.models.enums import MediaType, ProjectVisibility, ProjectMemberStatus

from app.schemas.media_version import VideoVersionCreate, MediaVersionOut, SetActiveVideoVersion

router = APIRouter(prefix="/projects", tags=["media-versions"])

# Swagger UI helper: ensure Authorization header works even for optional-auth endpoints
swagger_bearer_scheme = HTTPBearer(auto_error=False)


def get_project_or_404(db: Session, project_id: UUID) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def is_active_member(db: Session, project_id: UUID, user_id: UUID) -> bool:
    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
        ProjectMember.status == ProjectMemberStatus.ACTIVE.value,
    )
    return db.scalar(stmt) is not None


def is_invited_member(db: Session, project_id: UUID, user_id: UUID) -> bool:
    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
        ProjectMember.status == ProjectMemberStatus.INVITED.value,
    )
    return db.scalar(stmt) is not None


def ensure_can_view_project(db: Session, project: Project, user: User | None) -> None:
    """
    Viewing rule (same spirit as get_project):
    - PUBLIC project: anyone can view
    - otherwise: owner, ACTIVE member, or INVITED member can view
    """
    if project.visibility == ProjectVisibility.PUBLIC.value:
        return

    if user is None:
        raise HTTPException(status_code=403, detail="Not allowed")

    if project.owner_id == user.id:
        return

    if is_active_member(db, project.id, user.id):
        return

    if is_invited_member(db, project.id, user.id):
        return

    raise HTTPException(status_code=403, detail="Not allowed")


@router.post(
    "/{project_id:uuid}/video-versions",
    response_model=MediaVersionOut,
    status_code=status.HTTP_201_CREATED,
)
def create_video_version(
    project_id: UUID,
    data: VideoVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new VIDEO MediaVersion for a project.
    Owner only.

    Server assigns:
    - version_number = max(existing VIDEO versions) + 1

    MVP behavior:
    - sets project.active_media_version_id to the newly created version
    """
    project = get_project_or_404(db, project_id)

    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Owner only")

    # next version number per project for VIDEO
    stmt = select(func.coalesce(func.max(MediaVersion.version_number), 0)).where(
        MediaVersion.project_id == project.id,
        MediaVersion.media_type == MediaType.VIDEO.value,
    )
    max_v = db.scalar(stmt) or 0
    next_v = int(max_v) + 1

    mv = MediaVersion(
        project_id=project.id,
        segment_id=None,
        cue_id=None,
        media_type=MediaType.VIDEO.value,
        version_number=next_v,
        title=data.title,
        description=data.description,
        file_url=data.file_url,
        file_mime=data.file_mime,
        duration_seconds=data.duration_seconds,
        uploaded_by=current_user.id,
    )

    db.add(mv)
    db.commit()
    db.refresh(mv)

    # set active
    project.active_media_version_id = mv.id
    db.commit()

    return mv


@router.get(
    "/{project_id:uuid}/video-versions",
    response_model=list[MediaVersionOut],
)
def list_video_versions(
    project_id: UUID,
    db: Session = Depends(get_db),
    _credentials=Depends(swagger_bearer_scheme),
    current_user: User | None = Depends(get_current_user_optional),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """
    List VIDEO versions of a project.

    Visibility:
    - PUBLIC projects: readable by anyone
    - otherwise: owner/active/invited
    """
    project = get_project_or_404(db, project_id)
    ensure_can_view_project(db, project, current_user)

    stmt = (
        select(MediaVersion)
        .where(
            MediaVersion.project_id == project.id,
            MediaVersion.media_type == MediaType.VIDEO.value,
        )
        .order_by(MediaVersion.version_number.desc())
        .limit(limit)
        .offset(offset)
    )
    return db.scalars(stmt).all()


@router.patch(
    "/{project_id:uuid}/active-video-version",
    response_model=MediaVersionOut,
)
def set_active_video_version(
    project_id: UUID,
    data: SetActiveVideoVersion,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Select which VIDEO version is active on the project.
    Owner only.
    """
    project = get_project_or_404(db, project_id)

    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Owner only")

    mv = db.get(MediaVersion, data.video_version_id)
    if not mv or mv.project_id != project.id:
        raise HTTPException(status_code=404, detail="Media version not found")

    if mv.media_type != MediaType.VIDEO.value:
        raise HTTPException(status_code=400, detail="active version must be a VIDEO media version")

    project.active_media_version_id = mv.id
    db.commit()
    db.refresh(mv)
    return mv
