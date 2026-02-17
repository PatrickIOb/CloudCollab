from __future__ import annotations
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session,joinedload

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.enums import ProjectMemberStatus, NotificationType

from app.schemas.project_member import ProjectMemberInvite, ProjectMemberListItemOut, ProjectMemberOut
from app.auth.permissions import ensure_owner_or_active_member
from app.services.notify import create_notification



router = APIRouter(prefix="/projects", tags=["project-members"])


def get_project_or_404(db: Session, project_id: UUID) -> Project:
    # Helper function to get project or raise 404

    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


@router.get("/{project_id:uuid}/members", response_model=list[ProjectMemberListItemOut])
# List members of a project, only for owner and active members

def list_members(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(db, project_id)
    ensure_owner_or_active_member(db, project, current_user.id)

    stmt = (
        select(ProjectMember)
        .where(ProjectMember.project_id == project_id)
        .options(joinedload(ProjectMember.user))
    )
    return db.scalars(stmt).all()

@router.post("/{project_id:uuid}/members/invite", response_model=ProjectMemberOut, status_code=201)
# Invite a user to become a member of the project, only for owner

def invite_member(
    project_id: UUID,
    data: ProjectMemberInvite,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(db, project_id)

    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Owner only")

    user = db.scalar(select(User).where(User.username == data.username))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if user.id == project.owner_id:
        raise HTTPException(status_code=400, detail="Owner cannot be invited")

    member = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user.id,
        )
    )

    if member:
        member.role = data.role.value
        member.status = ProjectMemberStatus.INVITED.value
        db.commit()
        db.refresh(member)
        return member

    member = ProjectMember(
        project_id=project_id,
        user_id=user.id,
        role=data.role.value,
        status=ProjectMemberStatus.INVITED.value,
    )
    db.add(member)

    #Notify the user about the invite
    create_notification(
        db,
        recipient_id=user.id,
        actor_id=current_user.id,
        project_id=project_id,
        type=NotificationType.INVITE_RECEIVED.value,
        payload={
            "target": {
                "project_id": str(project_id),
                "project_title": project.title,
            },
            "meta": {
                "member_role": data.role.value,
            },
        },
    )

    db.commit()
    db.refresh(member)
    return member


@router.post("/{project_id:uuid}/members/accept", response_model=ProjectMemberOut)
# Accept an invite to become a member of the project, only for the invited user

def accept_invite(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(db, project_id)

    member = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id,
        )
    )
    if not member or member.status != ProjectMemberStatus.INVITED.value:
        raise HTTPException(status_code=404, detail="Invite not found")

    member.status = ProjectMemberStatus.ACTIVE.value

    # Notify the project owner about the accepted invite and load project for notification payload

    create_notification(
        db,
        recipient_id=project.owner_id,
        actor_id=current_user.id,
        project_id=project_id,
        type=NotificationType.INVITE_ACCEPTED.value,
        payload={
            "target": {
                "project_id": str(project_id),
                "project_title": project.title,
            }
        },
    )


    db.commit()
    db.refresh(member)
    return member


@router.delete("/{project_id:uuid}/members/{user_id:uuid}", status_code=204)
# Remove a member from the project, only for owner

def remove_member(
    project_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(db, project_id)

    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Owner only")

    if user_id == project.owner_id:
        raise HTTPException(status_code=400, detail="Cannot remove owner")

    member = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == user_id,
        )
    )
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")

    member.status = ProjectMemberStatus.REMOVED.value
    db.commit()
    return None
