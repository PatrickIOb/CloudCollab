from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.security import HTTPBearer
from sqlalchemy import select, or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.auth.dependencies import get_current_user, get_current_user_optional
from app.models.user import User
from app.models.project import Project
from app.models.media_version import MediaVersion
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


def get_video_media_version_or_400(db: Session, project: Project, media_version_id: UUID | None) -> UUID:
    """
    Resolve the VIDEO media_version_id a comment should attach to.

    Rules:
    - If media_version_id is provided: it must exist, belong to the project and be a VIDEO version.
    - If media_version_id is None: we default to project.active_media_version_id.
    - If the project has no active VIDEO version, we raise 400 (client must upload/activate a video first).
    """
    target_id = media_version_id or project.active_media_version_id
    if target_id is None:
        raise HTTPException(status_code=400, detail="Project has no active video version")

    mv = db.get(MediaVersion, target_id)
    if not mv or mv.project_id != project.id:
        raise HTTPException(status_code=400, detail="Invalid media_version_id for this project")

    if mv.media_type != "VIDEO":
        raise HTTPException(status_code=400, detail="Comments can only attach to VIDEO media versions")

    return mv.id


@router.get("/{project_id:uuid}/comments", response_model=list[CommentOut])
def list_comments(
    project_id: UUID,
    media_version_id: UUID | None = Query(default=None),
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

    Version scoping:
    - TIMELINE + PUBLIC are scoped to a VIDEO media_version.
    - If media_version_id is omitted, we default to the project's active VIDEO version.
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

    # Default behavior:
    # - TIMELINE and PUBLIC comments are scoped to a VIDEO media version.
    # - If media_version_id is omitted, we default to the project's active VIDEO version.
    conditions = [
        Comment.project_id == project_id,
        Comment.comment_type == comment_type.value,
    ]

    if comment_type in (CommentType.TIMELINE, CommentType.PUBLIC):
        target_media_version_id = get_video_media_version_or_400(db, project, media_version_id)

        # Backwards-compatible: older comments may have NULL media_version_id
        # (created before media_versions existed). We still include them, but all new
        # comments will be version-scoped by create_comment().
        conditions.append(
            or_(
                Comment.media_version_id == target_media_version_id,
                Comment.media_version_id.is_(None),
            )
        )

    stmt = (
        select(Comment)
        .where(*conditions)
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
    - TIMELINE/PUBLIC comments are always attached to a VIDEO media_version (defaults to project's active video)
    """
    project = get_project_or_404(db, project_id)

    if data.comment_type == CommentType.PUBLIC:
        # Public comments behave like YouTube: only for public + completed projects.
        if not (
            project.visibility == ProjectVisibility.PUBLIC.value
            and project.status == ProjectStatus.COMPLETED.value
        ):
            raise HTTPException(
                status_code=403,
                detail="Public comments only allowed on public completed projects",
            )
    else:
        # Timeline comments are collaboration-only.
        if not is_owner_or_active_member(db, project, current_user.id):
            raise HTTPException(status_code=403, detail="Not allowed")

    # Resolve the target VIDEO media version for this comment.
    # - TIMELINE comments always belong to a specific VIDEO version (default: active video).
    # - PUBLIC comments always belong to the active VIDEO version (the "final" version users see).
    if data.comment_type == CommentType.TIMELINE:
        target_media_version_id = get_video_media_version_or_400(db, project, data.media_version_id)
    else:
        # PUBLIC
        target_media_version_id = get_video_media_version_or_400(db, project, None)
        if data.media_version_id is not None and data.media_version_id != target_media_version_id:
            raise HTTPException(status_code=400, detail="Public comments must target the active video version")

    # Validate parent/reply
    if data.parent_id is not None:
        parent = db.get(Comment, data.parent_id)
        if not parent or parent.project_id != project_id:
            raise HTTPException(status_code=404, detail="Parent comment not found")

        if parent.comment_type != data.comment_type.value:
            raise HTTPException(status_code=400, detail="Reply type must match parent comment type")

        # Replies must stay within the same media version thread.
        # Legacy parent comments might have NULL media_version_id (created before media_versions existed);
        # we allow replying but the new reply will still be attached to the resolved target version.
        if parent.media_version_id is not None and parent.media_version_id != target_media_version_id:
            raise HTTPException(status_code=400, detail="Reply must target the same media_version_id as parent")

    comment = Comment(
        project_id=project_id,
        author_id=current_user.id,
        comment_type=data.comment_type.value,
        body=data.body,
        timecode_seconds=data.timecode_seconds,
        parent_id=data.parent_id,
        media_version_id=target_media_version_id,
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


@router.delete("/{project_id:uuid}/comments/{comment_id:uuid}", status_code=status.HTTP_204_NO_CONTENT)
def delete_comment(
    project_id: UUID,
    comment_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Delete a comment.

    Permissions:
    - The comment author can delete their own comment.
    - The project owner can delete any comment on their project (moderation).

    Notes:
    - Replies/children are removed automatically by DB-level ON DELETE CASCADE on parent_id.
    """
    project = get_project_or_404(db, project_id)

    comment = db.get(Comment, comment_id)
    if not comment or comment.project_id != project_id:
        raise HTTPException(status_code=404, detail="Comment not found")

    is_author = comment.author_id == current_user.id
    is_owner = project.owner_id == current_user.id

    if not (is_author or is_owner):
        raise HTTPException(status_code=403, detail="Not allowed")

    db.delete(comment)
    db.commit()
    return
