from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.security import HTTPBearer
from sqlalchemy import select, or_
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.models.project import Project
from app.models.user import User
from app.schemas.project import ProjectOut, ProjectCreate, ProjectUpdate
from app.auth.dependencies import get_current_user, get_current_user_optional
from app.models.enums import ProjectVisibility, ProjectCategory, ProjectStatus
from app.auth.permissions import is_invited_member, is_active_member

# Optional Bearer-Scheme nur für Swagger/OpenAPI,
# damit Swagger den Authorization Header auch bei public routes mitsendet.
swagger_bearer_scheme = HTTPBearer(auto_error=False)


# Helper functions 
def get_project_or_404(db: Session, project_id: UUID) -> Project:
    # Projekt anhand der ID holen, oder 404 werfen

    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def require_owner(project: Project, current_user: User):
    # Prüfen ob der aktuelle User der Besitzer des Projekts ist, sonst 403 werfen

    if project.owner_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed")


router = APIRouter(prefix="/projects", tags=["projects"])


@router.get("", response_model=list[ProjectOut])
# Alle PUBLIC Projekte auflisten, öffentlich zugänglich
def list_projects(
    db: Session = Depends(get_db),

    # Suche/Filter:
    username: str | None = Query(default=None),
    q: str | None = Query(default=None, min_length=1),
    category: ProjectCategory | None = None,
    status: ProjectStatus | None = None,

    # Pagination:
    limit: int = Query(default=20, ge=1, le=50),
    offset: int = Query(default=0, ge=0),
):
    stmt = (
        select(Project)
        .where(Project.visibility == ProjectVisibility.PUBLIC.value)
        .options(joinedload(Project.owner))
    )

    if username:
        user = db.scalar(select(User).where(User.username == username))
        if not user:
            return [] # Kein User mit dem username -> leere Ergebnisliste
        stmt = stmt.where(Project.owner_id == user.id)


    # Textsuche: title ODER description
    if q:
        like = f"%{q}%"
        stmt = stmt.where(
            or_(
                Project.title.ilike(like),
                Project.description.ilike(like),
            )
        )

    # category filter (Enum -> String)
    if category:
        stmt = stmt.where(Project.category == category.value)

    # status filter (Enum -> String)
    if status:
        stmt = stmt.where(Project.status == status.value)

    # Sort + Pagination
    stmt = (
        stmt.order_by(Project.created_at.desc())
        .limit(limit)
        .offset(offset)
    )

    return db.scalars(stmt).all()



@router.get("/me", response_model=list[ProjectOut])
# Alle eigenen Projekte auflisten, nur für authentifizierte User
def list_my_projects(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = (
        select(Project)
        .where(Project.owner_id == current_user.id)
        .options(joinedload(Project.owner))
    )
    return db.scalars(stmt).all()



from app.auth.permissions import is_active_member  # neu
# optional: später nehmen wir ensure_can_view_project statt inline checks

@router.get("/{project_id:uuid}", response_model=ProjectOut)
# Projektdetails, öffentlich zugänglich
def get_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    _credentials = Depends(swagger_bearer_scheme),  # <-- NUR für Swagger Header
    current_user: User | None = Depends(get_current_user_optional),
):
    project = db.scalar(
        select(Project)
        .where(Project.id == project_id)
        .options(joinedload(Project.owner))
    )

    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    is_public = project.visibility == ProjectVisibility.PUBLIC.value
    is_owner = current_user is not None and project.owner_id == current_user.id

    # active member check
    is_active = (
        current_user is not None
        and is_active_member(db, project.id, current_user.id)
    )

    # invited member check (preview access for invited users, even before accepting the invite)
    is_invited = (
        current_user is not None
        and is_invited_member(db, project.id, current_user.id)
    )

    # Publices Projects can be viewed by anyone
    if is_public:
        return project


    # PRIVATE / UNLISTED Projects can only be viewed by owner or active members:
    if current_user is None:
        raise HTTPException(status_code=404, detail="Project not found")

    if not (is_owner or is_active or is_invited):
        raise HTTPException(status_code=403, detail="Not allowed")

    return project



@router.post("", response_model=ProjectOut, status_code=status.HTTP_201_CREATED)
# Projekt erstellen, nur für authentifizierte User
def create_project(
    data: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    project = Project(
        owner_id=current_user.id,
        title=data.title,
        description=data.description,
        category=data.category.value,       # DB speichert Text -> wir speichern den Enum-Wert
        sub_category=data.sub_category,
        status=data.status.value,           # ebenso
        visibility=data.visibility.value,   # ebenso
    )

    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@router.patch("/{project_id:uuid}", response_model=ProjectOut)
# Projekt updaten, nur für Besitzer des Projekts
def update_project(
    project_id: UUID,
    data: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(db, project_id)
    require_owner(project, current_user)

    # Nur Felder updaten, die wirklich mitgeschickt wurden
    update_data = data.model_dump(exclude_unset=True)

    # Enum -> String für DB (weil DB Text + CheckConstraint)
    if "category" in update_data:
        update_data["category"] = update_data["category"].value
    if "status" in update_data:
        update_data["status"] = update_data["status"].value
    if "visibility" in update_data:
        update_data["visibility"] = update_data["visibility"].value

    for key, value in update_data.items():
        setattr(project, key, value)

    db.commit()
    db.refresh(project)
    return project


@router.delete("/{project_id:uuid}", status_code=status.HTTP_204_NO_CONTENT)
# Projekt löschen, nur für Besitzer des Projekts
def delete_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    project = get_project_or_404(db, project_id)
    require_owner(project, current_user)

    db.delete(project)
    db.commit()
    return
