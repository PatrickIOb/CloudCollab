# app/routers/comments.py
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.security import HTTPBearer
from sqlalchemy import select, or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.auth.dependencies import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.project import Project
from app.models.comment import Comment
from app.models.project_member import ProjectMember
from app.models.enums import (
    CommentType,
    ProjectVisibility,
    ProjectStatus,
    ProjectMemberStatus,
)

from app.schemas.comment import CommentCreate, CommentOut
from app.services.notify import create_notification
from app.models.enums import NotificationType


# for sending optional Bearer token in Swagger/OpenAPI, so that it works for both public and private routes.
swagger_bearer_scheme = HTTPBearer(auto_error=False)

router = APIRouter(prefix="/projects", tags=["comments"])


def get_project_or_404(db: Session, project_id: UUID) -> Project:
    """
    Load a project or raise 404. This is used for both public and private rules.
    """
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def is_owner_or_active_member(db: Session, project: Project, user_id: UUID) -> bool:
    """
    Returns True if user is project owner or an ACTIVE member.
    Used for TIMELINE comments (collaboration).
    """
    if project.owner_id == user_id:
        return True

    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project.id,
        ProjectMember.user_id == user_id,
        ProjectMember.status == ProjectMemberStatus.ACTIVE.value,
    )
    return db.scalar(stmt) is not None


def get_active_member_user_ids(db: Session, project_id: UUID) -> list[UUID]:
    """
    Returns a list of user_ids for ACTIVE members of a project (excluding owner).
    """
    stmt = select(ProjectMember.user_id).where(
        ProjectMember.project_id == project_id,
        ProjectMember.status == ProjectMemberStatus.ACTIVE.value,
    )
    return list(db.scalars(stmt).all())


def ensure_public_comments_allowed(project: Project) -> None:
    """
    Public comments are only allowed on PUBLIC + COMPLETED projects.
    For all other projects, we hide them (404) to avoid leaking private projects.
    """
    if not (
        project.visibility == ProjectVisibility.PUBLIC.value
        and project.status == ProjectStatus.COMPLETED.value
    ):
        raise HTTPException(status_code=404, detail="Project not found")


@router.get("/{project_id:uuid}/comments", response_model=list[CommentOut])
def list_comments(
    project_id: UUID,
    comment_type: CommentType = Query(default=CommentType.PUBLIC),
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    _credentials = Depends(swagger_bearer_scheme),
    current_user: User | None = Depends(get_current_user_optional),
):
    """
    List comments for a project.

    - PUBLIC comments: visible to everyone ONLY if project is PUBLIC + COMPLETED.
    - TIMELINE comments: visible only to owner + ACTIVE members.
    """
    project = get_project_or_404(db, project_id)

    if comment_type == CommentType.PUBLIC:
        ensure_public_comments_allowed(project)
    else:
        # TIMELINE
        if current_user is None:
            # Don't leak private project existence
            raise HTTPException(status_code=404, detail="Project not found")
        if not is_owner_or_active_member(db, project, current_user.id):
            raise HTTPException(status_code=403, detail="Not allowed")

    stmt = (
        select(Comment)
        .where(
            Comment.project_id == project_id,
            Comment.comment_type == comment_type.value,
        )
        .options(joinedload(Comment.author))
        .order_by(Comment.created_at.asc())
        .limit(limit)
        .offset(offset)
    )
    return db.scalars(stmt).all()


@router.post("/{project_id:uuid}/comments", response_model=CommentOut, status_code=201)
def create_comment(
    project_id: UUID,
    data: CommentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create a new comment.

    Rules:
    - PUBLIC: allowed for any logged-in user, but ONLY on PUBLIC + COMPLETED projects.
    - TIMELINE: allowed only for project owner + ACTIVE members (collaboration).

    Replies:
    - parent_id must belong to same project
    - reply must match the parent's comment_type
    """
    project = get_project_or_404(db, project_id)

    if data.comment_type == CommentType.PUBLIC:
        # Public comments behave like YouTube: only for public + completed projects.
        if not (
            project.visibility == ProjectVisibility.PUBLIC.value
            and project.status == ProjectStatus.COMPLETED.value
        ):
            raise HTTPException(status_code=403, detail="Public comments only allowed on public completed projects")
    else:
        # Timeline comments are collaboration-only.
        if not is_owner_or_active_member(db, project, current_user.id):
            raise HTTPException(status_code=403, detail="Not allowed")

    # Validate parent/reply
    if data.parent_id is not None:
        parent = db.get(Comment, data.parent_id)
        if not parent or parent.project_id != project_id:
            raise HTTPException(status_code=404, detail="Parent comment not found")

        if parent.comment_type != data.comment_type.value:
            raise HTTPException(status_code=400, detail="Reply type must match parent comment type")

    comment = Comment(
        project_id=project_id,
        author_id=current_user.id,
        comment_type=data.comment_type.value,
        body=data.body,
        timecode_seconds=data.timecode_seconds,
        parent_id=data.parent_id,
        media_version_id=data.media_version_id,
        segment_id=data.segment_id,
    )

    db.add(comment)
    db.commit()
    db.refresh(comment)

# -------------------------
    # Notifications

    payload = {
        "target": {
            "project_id": str(project.id),
            "project_title": project.title,
        },
        "meta": {
            "comment_id": str(comment.id),
            "comment_type": data.comment_type.value,
            "timecode_seconds": data.timecode_seconds,
            "parent_id": str(data.parent_id) if data.parent_id else None,
        },
    }

    # Determine recipients based on comment type
    recipients: set[UUID] = set()

    if data.comment_type == CommentType.PUBLIC:
        # Notify owner for public feedback (if not self)
        if project.owner_id != current_user.id:
            recipients.add(project.owner_id)

        notif_type = NotificationType.COMMENT_PUBLIC_CREATED.value

    else:
        # TIMELINE: notify owner + ACTIVE members (excluding author)
        if project.owner_id != current_user.id:
            recipients.add(project.owner_id)

        for uid in get_active_member_user_ids(db, project.id):
            if uid != current_user.id:
                recipients.add(uid)

        # If this is a reply, also notify parent author (useful in threads)
        notif_type = NotificationType.COMMENT_TIMELINE_CREATED.value
        if data.parent_id is not None:
            parent = db.get(Comment, data.parent_id)
            if parent and parent.author_id != current_user.id:
                recipients.add(parent.author_id)
                notif_type = NotificationType.COMMENT_REPLY_CREATED.value

    # Create notifications
    for rid in recipients:
        create_notification(
            db,
            recipient_id=rid,
            actor_id=current_user.id,
            project_id=project.id,
            type=notif_type,
            payload=payload,
        )

    db.commit()


    # Reload author relation for UI-friendly response
    comment = db.scalar(
        select(Comment)
        .where(Comment.id == comment.id)
        .options(joinedload(Comment.author))
    )
    return comment
