from __future__ import annotations

from uuid import UUID
from pydantic import BaseModel, ConfigDict

from app.models.enums import ApplicationStatus
from app.schemas.common import UserSummaryOut


class ProjectApplicationCreate(BaseModel):
    message: str | None = None


class ProjectApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    user_id: UUID
    status: ApplicationStatus
    message: str | None = None

    user: UserSummaryOut