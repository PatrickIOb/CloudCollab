from __future__ import annotations

from uuid import UUID
from pydantic import BaseModel, ConfigDict


class UserSummaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    username: str
    display_name: str
    avatar_url: str | None = None
