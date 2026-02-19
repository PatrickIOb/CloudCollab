from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import ProjectCategory, ProjectStatus, ProjectVisibility
from app.schemas.common import UserSummaryOut



class ProjectCreate(BaseModel):
    # Alle Felder außer description und sub_category sind Pflichtfelder, da in der DB als NOT NULL definiert.

    title: str = Field(..., min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=5000)

    # DB verlangt category als drop-down mit festen Werten 
    category: ProjectCategory


    # sub_category bleibt optional da danach nicht gefiltert wird
    sub_category: str | None = Field(default=None, max_length=120)

    # status 
    # default ist DRAFT (passt zur DB-Logik)
    status: ProjectStatus = ProjectStatus.DRAFT

    # visibility default ist PUBLIC 
    visibility: ProjectVisibility = ProjectVisibility.PUBLIC


class ProjectOut(BaseModel):
    # Schema für Projektausgabe, alle Felder wie in DB

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    owner_id: UUID

    owner: UserSummaryOut | None = None  # Optionales Feld für die Ausgabe, damit wir den Ownernamen in der Projektliste haben

    title: str = Field(..., min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=5000)

    category: ProjectCategory
    sub_category: str | None = Field(default=None, max_length=120)
    status: ProjectStatus
    visibility: ProjectVisibility

    active_media_version_id: UUID | None = None 

    created_at: datetime
    updated_at: datetime


class ProjectUpdate(BaseModel):
    # Schema zum updaten eines Projekts. Alle Felder optional damit nur benötigte Felder aktualisiert werden können.

    title: str | None = Field(default=None, min_length=3, max_length=120)
    description: str | None = Field(default=None, max_length=5000)
    category: ProjectCategory | None = None
    sub_category: str | None = None
    status: ProjectStatus | None = None
    visibility: ProjectVisibility | None = None