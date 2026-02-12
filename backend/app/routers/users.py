# app/routers/users.py
from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.enums import ProjectVisibility, ProjectStatus

from app.models.composer_profile import ComposerProfile
from app.models.filmmaker_profile import FilmmakerProfile

from app.schemas.user import UserPublicProfileOut, UserMeOut, UserMeUpdate
from app.schemas.project import ProjectOut


# /users/... (private + utility)
router = APIRouter(prefix="/users", tags=["users"])

# /u/... (public shareable)
public_router = APIRouter(tags=["users"])


def get_user_or_404(db: Session, user_id: UUID) -> User:
    user = db.get(User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def get_user_by_username_or_404(db: Session, username: str) -> User:
    stmt = select(User).where(User.username == username)
    user = db.scalar(stmt)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


def fetch_public_projects(db: Session, owner_id: UUID, limit: int, offset: int):
    stmt = (
        select(Project)
        .where(
            Project.owner_id == owner_id,
            Project.visibility == ProjectVisibility.PUBLIC.value,
        )
        .order_by(Project.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return db.scalars(stmt).all()


def fetch_portfolio_projects(db: Session, owner_id: UUID, limit: int, offset: int):
    stmt = (
        select(Project)
        .where(
            Project.owner_id == owner_id,
            Project.visibility == ProjectVisibility.PUBLIC.value,
            Project.status == ProjectStatus.COMPLETED.value,
        )
        .order_by(Project.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return db.scalars(stmt).all()


# ---------- PUBLIC (username) ----------

@public_router.get("/u/{username}", response_model=UserPublicProfileOut)
def get_public_user_profile_by_username(
    username: str,
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    user = get_user_by_username_or_404(db, username)
    public_projects = fetch_public_projects(db, user.id, limit, offset)

    return UserPublicProfileOut(
        **user.__dict__,
        public_projects=public_projects,
    )


@public_router.get("/u/{username}/portfolio", response_model=list[ProjectOut])
def get_user_portfolio_by_username(
    username: str,
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    user = get_user_by_username_or_404(db, username)
    return fetch_portfolio_projects(db, user.id, limit, offset)


# ---------- OPTIONAL PUBLIC (uuid) ----------

@router.get("/{user_id:uuid}", response_model=UserPublicProfileOut)
def get_public_user_profile_by_id(
    user_id: UUID,
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    user = get_user_or_404(db, user_id)
    public_projects = fetch_public_projects(db, user.id, limit, offset)

    return UserPublicProfileOut(
        **user.__dict__,
        public_projects=public_projects,
    )


@router.get("/{user_id:uuid}/portfolio", response_model=list[ProjectOut])
def get_user_portfolio_by_id(
    user_id: UUID,
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    user = get_user_or_404(db, user_id)
    return fetch_portfolio_projects(db, user.id, limit, offset)


# ---------- ME (auth) ----------

@router.get("/me", response_model=UserMeOut)
def get_my_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(default=50, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    stmt = (
        select(Project)
        .where(Project.owner_id == current_user.id)
        .order_by(Project.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    projects = db.scalars(stmt).all()

    return UserMeOut(
        **current_user.__dict__,
        projects=projects,
    )


@router.patch("/me", response_model=UserMeOut)
def update_my_profile(
    data: UserMeUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    update_data = data.model_dump(exclude_unset=True)

    # IMPORTANT: does NOT allow username changes here (keeps share links stable)
    update_data.pop("username", None)

    # enums -> string for TEXT columns
    if "availability_status" in update_data and update_data["availability_status"] is not None:
        update_data["availability_status"] = update_data["availability_status"].value

    if "role" in update_data and update_data["role"] is not None:
        update_data["role"] = update_data["role"].value

    composer_patch = update_data.pop("composer_profile", None)
    filmmaker_patch = update_data.pop("filmmaker_profile", None)

    for key, value in update_data.items():
        setattr(current_user, key, value)

    # composer profile patch
    if composer_patch is not None:
        prof = current_user.composer_profile
        if prof is None:
            prof = ComposerProfile(user_id=current_user.id)
            db.add(prof)
            current_user.composer_profile = prof

        if "primary_focus" in composer_patch and composer_patch["primary_focus"] is not None:
            composer_patch["primary_focus"] = composer_patch["primary_focus"].value

        for k, v in composer_patch.items():
            setattr(prof, k, v)

    # filmmaker profile patch
    if filmmaker_patch is not None:
        prof = current_user.filmmaker_profile
        if prof is None:
            prof = FilmmakerProfile(user_id=current_user.id)
            db.add(prof)
            current_user.filmmaker_profile = prof

        for k, v in filmmaker_patch.items():
            setattr(prof, k, v)

    db.commit()
    db.refresh(current_user)

    # attach projects
    stmt = (
        select(Project)
        .where(Project.owner_id == current_user.id)
        .order_by(Project.created_at.desc())
        .limit(50)
        .offset(0)
    )
    projects = db.scalars(stmt).all()

    return UserMeOut(
        **current_user.__dict__,
        projects=projects,
    )

from sqlalchemy import or_

@public_router.get("/u/{username}/projects", response_model=list[ProjectOut])
# Alle öffentlichen Projekte eines Users auflisten, öffentlich zugänglich für Projekt Tab eines Userprofils

def get_user_public_projects_by_username(
    username: str,
    db: Session = Depends(get_db),
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
    q: str | None = Query(default=None),
    status: str | None = Query(default=None),
    category: str | None = Query(default=None),
):
    user = get_user_by_username_or_404(db, username)

    stmt = select(Project).where(
        Project.owner_id == user.id,
        Project.visibility == ProjectVisibility.PUBLIC.value,
    )

    # optional search (title + description)
    if q:
        stmt = stmt.where(
            or_(
                Project.title.ilike(f"%{q}%"),
                Project.description.ilike(f"%{q}%"),
            )
        )

    # optional filters (string compare because DB stores Enum.value as text)
    if status:
        stmt = stmt.where(Project.status == status)
    if category:
        stmt = stmt.where(Project.category == category)

    stmt = stmt.order_by(Project.created_at.desc()).limit(limit).offset(offset)
    return db.scalars(stmt).all()
