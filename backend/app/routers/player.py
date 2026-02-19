from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload, selectinload

from app.database import get_db
from app.auth.dependencies import get_current_user_optional
from app.models.user import User
from app.models.project import Project
from app.models.media_version import MediaVersion
from app.models.music_cue import MusicCue
from app.models.comment import Comment
from app.models.project_member import ProjectMember
from app.models.enums import (
    MediaType,
    ProjectVisibility,
    ProjectMemberStatus,
    CommentType,
)

from app.schemas.player import PlayerPageOut


router = APIRouter(prefix="/projects", tags=["player"])
swagger_bearer_scheme = HTTPBearer(auto_error=False)


def get_project_or_404(db: Session, project_id: UUID) -> Project:
    """Fetch project or raise 404."""
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def is_active_member(db: Session, project_id: UUID, user_id: UUID) -> bool:
    """True if user is an ACTIVE project member."""
    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
        ProjectMember.status == ProjectMemberStatus.ACTIVE.value,
    )
    return db.scalar(stmt) is not None


def is_invited_member(db: Session, project_id: UUID, user_id: UUID) -> bool:
    """True if user is INVITED to the project."""
    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
        ProjectMember.status == ProjectMemberStatus.INVITED.value,
    )
    return db.scalar(stmt) is not None


def can_view_timeline_comments(db: Session, project: Project, user: User | None) -> bool:
    """
    Timeline comments are private collaboration notes.

    Rule:
    - Only owner / ACTIVE members / INVITED members can view them,
      regardless of project visibility (even if PUBLIC).
    """
    if user is None:
        return False
    if project.owner_id == user.id:
        return True
    if is_active_member(db, project.id, user.id):
        return True
    if is_invited_member(db, project.id, user.id):
        return True
    return False


def ensure_can_view_project(db: Session, project: Project, user: User | None) -> None:
    """
    Project viewing rule:
    - PUBLIC: anyone can view
    - PRIVATE/UNLISTED: owner/ACTIVE/INVITED only
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


@router.get("/{project_id:uuid}/player", response_model=PlayerPageOut)
def get_player_page(
    project_id: UUID,
    db: Session = Depends(get_db),
    _credentials=Depends(swagger_bearer_scheme),
    current_user: User | None = Depends(get_current_user_optional),
    timeline_limit: int = Query(default=200, ge=1, le=500),
    timeline_offset: int = Query(default=0, ge=0),
    public_limit: int = Query(default=50, ge=1, le=200),
    public_offset: int = Query(default=0, ge=0),
):
    """
    Player-page aggregator endpoint for React.

    Always returns (if allowed to view project):
    - project
    - active VIDEO media version
    - cues for that active video version (active audio + all audio versions)

    Returns timeline comments ONLY for:
    - owner / ACTIVE members / INVITED members
    (otherwise: [] even if project is PUBLIC)

    Returns public comments for PUBLIC projects (readable by anyone).
    """
    project = get_project_or_404(db, project_id)
    ensure_can_view_project(db, project, current_user)

    if project.active_media_version_id is None:
        raise HTTPException(status_code=409, detail="Project has no active video version yet")

    active_video = db.get(MediaVersion, project.active_media_version_id)
    if not active_video or active_video.project_id != project.id:
        raise HTTPException(status_code=409, detail="Active media version is invalid for this project")
    if active_video.media_type != MediaType.VIDEO.value:
        raise HTTPException(status_code=409, detail="Active media version is not a VIDEO")

    cues_stmt = (
        select(MusicCue)
        .where(
            MusicCue.project_id == project.id,
            MusicCue.video_version_id == active_video.id,
        )
        .options(
            joinedload(MusicCue.active_audio_version),
            selectinload(MusicCue.audio_versions),
        )
        .order_by(MusicCue.start_seconds.asc(), MusicCue.created_at.asc())
    )
    cues = db.scalars(cues_stmt).all()

    # Timeline comments (private collab notes): only for members/owner/invited
    timeline_comments: list[Comment] = []
    if can_view_timeline_comments(db, project, current_user):
        timeline_stmt = (
            select(Comment)
            .where(
                Comment.project_id == project.id,
                Comment.media_version_id == active_video.id,
                Comment.comment_type == CommentType.TIMELINE.value,
            )
            .options(
                joinedload(Comment.author),
                joinedload(Comment.parent),
            )
            .order_by(Comment.created_at.asc())
            .limit(timeline_limit)
            .offset(timeline_offset)
        )
        timeline_comments = db.scalars(timeline_stmt).all()

    # Public comments: only for PUBLIC projects (readable by anyone)
    public_comments: list[Comment] = []
    if project.visibility == ProjectVisibility.PUBLIC.value:
        public_stmt = (
            select(Comment)
            .where(
                Comment.project_id == project.id,
                Comment.comment_type == CommentType.PUBLIC.value,
            )
            .options(
                joinedload(Comment.author),
                joinedload(Comment.parent),
            )
            .order_by(Comment.created_at.desc())
            .limit(public_limit)
            .offset(public_offset)
        )
        public_comments = db.scalars(public_stmt).all()

    return PlayerPageOut(
        project=project,
        active_video=active_video,
        cues=cues,
        timeline_comments=timeline_comments,
        public_comments=public_comments,
    )
