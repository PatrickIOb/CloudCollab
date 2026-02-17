from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.project_member import ProjectMember
from app.models.project_application import ProjectApplication

from app.models.enums import (
    ApplicationStatus,
    ProjectVisibility,
    ProjectMemberStatus,
    ProjectMemberRole,
)

from app.schemas.project_application import ProjectApplicationCreate, ProjectApplicationOut

router = APIRouter(prefix="/projects", tags=["project-applications"])


def get_project_or_404(db: Session, project_id: UUID) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project

def load_application_with_user_or_404(db: Session, app_id: UUID) -> ProjectApplication:
    app = db.scalar(
        select(ProjectApplication)
        .where(ProjectApplication.id == app_id)
        .options(joinedload(ProjectApplication.user))
    )
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")
    return app


@router.post("/{project_id:uuid}/apply", response_model=ProjectApplicationOut, status_code=201)
def apply_to_project(
    project_id: UUID,
    data: ProjectApplicationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(db, project_id)

    # Apply only for PUBLIC projects
    if project.visibility != ProjectVisibility.PUBLIC.value:
        raise HTTPException(status_code=403, detail="Applications are only allowed for public projects")

    if project.owner_id == current_user.id:
        raise HTTPException(status_code=400, detail="Owner cannot apply")

    # already ACTIVE member?
    active_member = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == current_user.id,
            ProjectMember.status == ProjectMemberStatus.ACTIVE.value,
        )
    )
    if active_member:
        raise HTTPException(status_code=409, detail="Already a member")

    # already applied?
    existing_app = db.scalar(
        select(ProjectApplication).where(
            ProjectApplication.project_id == project_id,
            ProjectApplication.user_id == current_user.id,
        )
    )
    if existing_app:
        raise HTTPException(status_code=409, detail="Already applied")

    app = ProjectApplication(
        project_id=project_id,
        user_id=current_user.id,
        status=ApplicationStatus.PENDING.value,
        message=data.message,
    )
    db.add(app)
    db.commit()
    db.refresh(app)
    return load_application_with_user_or_404(db, app.id)


@router.post("/{project_id:uuid}/withdraw", response_model=ProjectApplicationOut)
def withdraw_application(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    app = db.scalar(
        select(ProjectApplication).where(
            ProjectApplication.project_id == project_id,
            ProjectApplication.user_id == current_user.id,
        )
    )
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.status != ApplicationStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Only pending applications can be withdrawn")

    app.status = ApplicationStatus.WITHDRAWN.value
    db.commit()

    return load_application_with_user_or_404(db, app.id)


@router.get("/{project_id:uuid}/applications", response_model=list[ProjectApplicationOut])
def list_applications(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(db, project_id)

    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Owner only")

    stmt = (
        select(ProjectApplication)
        .where(ProjectApplication.project_id == project_id)
        .options(joinedload(ProjectApplication.user))
    )
    return db.scalars(stmt).all()


@router.post("/{project_id:uuid}/applications/{app_id:uuid}/accept", response_model=ProjectApplicationOut)
def accept_application(
    project_id: UUID,
    app_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(db, project_id)
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Owner only")

    app = db.get(ProjectApplication, app_id)
    if not app or app.project_id != project_id:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.status != ApplicationStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Application is not pending")

    # Upsert membership -> ACTIVE
    member = db.scalar(
        select(ProjectMember).where(
            ProjectMember.project_id == project_id,
            ProjectMember.user_id == app.user_id,
        )
    )

    if member:
        member.role = ProjectMemberRole.CONTRIBUTOR.value
        member.status = ProjectMemberStatus.ACTIVE.value
    else:
        member = ProjectMember(
            project_id=project_id,
            user_id=app.user_id,
            role=ProjectMemberRole.CONTRIBUTOR.value,
            status=ProjectMemberStatus.ACTIVE.value,
        )
        db.add(member)

    app.status = ApplicationStatus.ACCEPTED.value
    db.commit()

    # re-query with user for response
    return load_application_with_user_or_404(db, app.id)


@router.post("/{project_id:uuid}/applications/{app_id:uuid}/reject", response_model=ProjectApplicationOut)
def reject_application(
    project_id: UUID,
    app_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(db, project_id)
    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Owner only")

    app = db.get(ProjectApplication, app_id)
    if not app or app.project_id != project_id:
        raise HTTPException(status_code=404, detail="Application not found")

    if app.status != ApplicationStatus.PENDING.value:
        raise HTTPException(status_code=400, detail="Application is not pending")

    app.status = ApplicationStatus.REJECTED.value
    db.commit()

    return load_application_with_user_or_404(db, app.id)
