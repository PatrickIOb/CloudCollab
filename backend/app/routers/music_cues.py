from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database import get_db
from app.auth.dependencies import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.project import Project
from app.models.music_cue import MusicCue
from app.models.media_version import MediaVersion
from app.models.project_member import ProjectMember
from app.models.enums import (
    MediaType,
    ProjectMemberRole,
    ProjectMemberStatus,
    ProjectVisibility,
)

from app.schemas.music_cue import MusicCueCreate, MusicCueUpdate, MusicCueOut


router = APIRouter(prefix="/projects", tags=["music-cues"])

# Swagger helper: keeps the "Authorize" button usable even on optional-auth routes.
swagger_bearer_scheme = HTTPBearer(auto_error=False)


def get_project_or_404(db: Session, project_id: UUID) -> Project:
    """
    Fetch a project by id or raise 404.
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def is_active_member(db: Session, project_id: UUID, user_id: UUID) -> bool:
    """
    Returns True if user is an ACTIVE member of the project.
    """
    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
        ProjectMember.status == ProjectMemberStatus.ACTIVE.value,
    )
    return db.scalar(stmt) is not None


def is_invited_member(db: Session, project_id: UUID, user_id: UUID) -> bool:
    """
    Returns True if user is INVITED to the project.
    (Used for allowing viewing private projects to invited users.)
    """
    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
        ProjectMember.status == ProjectMemberStatus.INVITED.value,
    )
    return db.scalar(stmt) is not None


def ensure_owner_or_active_member(db: Session, project: Project, user_id: UUID) -> None:
    """
    Write permission for cues (collaboration data).

    MVP rule:
    - owner can manage
    - ACTIVE members can manage
    """
    if project.owner_id == user_id:
        return

    if not is_active_member(db, project.id, user_id):
        raise HTTPException(status_code=403, detail="Not allowed")


def ensure_can_view_project(db: Session, project: Project, user: User | None) -> None:
    """
    Viewing rule (same logic as projects):
    - PUBLIC: anyone can view
    - PRIVATE/UNLISTED: only owner, ACTIVE member, or INVITED member can view
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


def ensure_can_upload_audio(db: Session, project: Project, user: User) -> None:
    """
    Audio uploads for cues should be done by composers (or owner).

    MVP rule:
    - owner can upload
    - ACTIVE member with role COMPOSER can upload
    """
    if project.owner_id == user.id:
        return

    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project.id,
        ProjectMember.user_id == user.id,
        ProjectMember.status == ProjectMemberStatus.ACTIVE.value,
    )
    member = db.scalar(stmt)

    if member is None:
        raise HTTPException(status_code=403, detail="Not allowed")

    if member.role != ProjectMemberRole.COMPOSER.value:
        raise HTTPException(status_code=403, detail="Only composers can upload audio")


def get_video_version_or_404(db: Session, video_version_id: UUID) -> MediaVersion:
    """
    Fetch a MediaVersion and ensure it is a VIDEO media version.
    """
    mv = db.get(MediaVersion, video_version_id)
    if not mv:
        raise HTTPException(status_code=404, detail="Video version not found")
    if mv.media_type != MediaType.VIDEO.value:
        raise HTTPException(status_code=400, detail="video_version_id must reference a VIDEO media version")
    return mv


@router.post(
    "/{project_id:uuid}/video-versions/{video_version_id:uuid}/cues",
    response_model=MusicCueOut,
    status_code=201,
)
def create_music_cue(
    project_id: UUID,
    video_version_id: UUID,
    data: MusicCueCreate,
    db: Session = Depends(get_db),
    _credentials=Depends(swagger_bearer_scheme),
    current_user: User = Depends(get_current_user),
):
    """
    Create a cue for a specific VIDEO media version.

    A cue defines a time range on the video timeline where music can play.
    Audio versions for the cue are uploaded separately (and can be versioned).
    """
    project = get_project_or_404(db, project_id)
    ensure_owner_or_active_member(db, project, current_user.id)

    video_mv = get_video_version_or_404(db, video_version_id)

    # Safety: ensure the referenced video version belongs to this project
    if video_mv.project_id != project.id:
        raise HTTPException(status_code=400, detail="Video version does not belong to this project")

    cue = MusicCue(
        project_id=project.id,
        video_version_id=video_version_id,
        label=data.label,
        start_seconds=data.start_seconds,
        end_seconds=data.end_seconds,
    )
    db.add(cue)
    db.commit()
    db.refresh(cue)

    # Response model includes expansions; for a new cue there are none yet.
    return MusicCueOut(
        **cue.__dict__,
        active_audio_version=None,
        audio_versions=[],
    )


@router.get(
    "/{project_id:uuid}/video-versions/{video_version_id:uuid}/cues",
    response_model=list[MusicCueOut],
)
def list_music_cues(
    project_id: UUID,
    video_version_id: UUID,
    db: Session = Depends(get_db),
    _credentials=Depends(swagger_bearer_scheme),
    current_user: User | None = Depends(get_current_user_optional),
    limit: int = Query(default=100, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
):
    """
    List cues for a given VIDEO version.

    Returns each cue with:
    - active_audio_version (selected audio for playback)
    - audio_versions (all uploaded audio versions for this cue)

    Visibility:
    - PUBLIC project: anyone can read (no login required)
    - PRIVATE/UNLISTED: owner/ACTIVE/INVITED only
    """
    project = get_project_or_404(db, project_id)
    ensure_can_view_project(db, project, current_user)

    video_mv = get_video_version_or_404(db, video_version_id)
    if video_mv.project_id != project.id:
        raise HTTPException(status_code=400, detail="Video version does not belong to this project")

    stmt = (
        select(MusicCue)
        .where(
            MusicCue.project_id == project.id,
            MusicCue.video_version_id == video_version_id,
        )
        .options(
            # single relation -> joinedload is fine
            joinedload(MusicCue.active_audio_version),
            # collection relation -> use selectinload to avoid duplicated rows
            selectinload(MusicCue.audio_versions),
        )
        .order_by(MusicCue.start_seconds.asc(), MusicCue.created_at.asc())
        .limit(limit)
        .offset(offset)
    )

    return db.scalars(stmt).all()


@router.patch(
    "/{project_id:uuid}/cues/{cue_id:uuid}",
    response_model=MusicCueOut,
)
def update_music_cue(
    project_id: UUID,
    cue_id: UUID,
    data: MusicCueUpdate,
    db: Session = Depends(get_db),
    _credentials=Depends(swagger_bearer_scheme),
    current_user: User = Depends(get_current_user),
):
    """
    Patch cue fields:
    - label
    - start_seconds / end_seconds
    - active_audio_version_id (select which uploaded audio version is active)

    Permissions:
    - owner OR ACTIVE member
    """
    project = get_project_or_404(db, project_id)
    ensure_owner_or_active_member(db, project, current_user.id)

    cue = db.get(MusicCue, cue_id)
    if not cue or cue.project_id != project.id:
        raise HTTPException(status_code=404, detail="Cue not found")

    patch = data.model_dump(exclude_unset=True)

    # Handle active audio selection (if included)
    if "active_audio_version_id" in patch:
        new_active_id = patch.pop("active_audio_version_id")

        if new_active_id is None:
            cue.active_audio_version_id = None
        else:
            mv = db.get(MediaVersion, new_active_id)
            if not mv or mv.project_id != project.id:
                raise HTTPException(status_code=400, detail="Invalid active_audio_version_id")

            if mv.cue_id != cue.id:
                raise HTTPException(status_code=400, detail="active_audio_version_id must belong to this cue")

            if mv.media_type != MediaType.AUDIO.value:
                raise HTTPException(status_code=400, detail="active_audio_version_id must reference an AUDIO media version")

            cue.active_audio_version_id = mv.id

    # Apply remaining patch fields (label/range)
    for k, v in patch.items():
        setattr(cue, k, v)

    # Range safety
    if cue.end_seconds < cue.start_seconds:
        raise HTTPException(status_code=422, detail="end_seconds must be >= start_seconds")

    db.commit()

    # Re-query to ensure relationships are loaded in response
    stmt = (
        select(MusicCue)
        .where(MusicCue.id == cue.id)
        .options(
            joinedload(MusicCue.active_audio_version),
            selectinload(MusicCue.audio_versions),
        )
    )
    return db.scalar(stmt)
