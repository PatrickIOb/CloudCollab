from __future__ import annotations
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.project_member import ProjectMember
from app.models.enums import ProjectVisibility, ProjectMemberStatus


def is_active_member(db: Session, project_id: UUID, user_id: UUID) -> bool:
    # Check if user is an ACTIVE member of the project

    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
        ProjectMember.status == ProjectMemberStatus.ACTIVE.value,
    )
    return db.scalar(stmt) is not None


def is_invited_member(db: Session, project_id: UUID, user_id: UUID) -> bool:
    # Check if user is an INVITED member of the project for preview access to the project before accepting the invite
    
    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
        ProjectMember.status == ProjectMemberStatus.INVITED.value,
    )
    return db.scalar(stmt) is not None


def ensure_owner_or_active_member(db: Session, project, user_id: UUID):
    # Ensure that user is owner or ACTIVE member of the project or raise 403

    if project.owner_id == user_id:
        return
    if not is_active_member(db, project.id, user_id):
        raise HTTPException(status_code=403, detail="Not allowed")


def ensure_can_view_project(db: Session, project, user_id: UUID | None):
    # Ensure that the project can be viewed by the user (public or owner/active member) or raise 404 
    # to not reveal existence of private projects

    if project.visibility == ProjectVisibility.PUBLIC.value:
        return

    if user_id is None:
        raise HTTPException(status_code=404, detail="Project not found")

    ensure_owner_or_active_member(db, project, user_id)
