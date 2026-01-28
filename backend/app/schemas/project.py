from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ProjectOut(BaseModel):
    id: UUID
    owner_id: UUID
    title: str
    description: str | None
    category: str
    status: str
    visibility: str
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
