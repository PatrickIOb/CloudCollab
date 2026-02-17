from __future__ import annotations

from uuid import UUID
from datetime import datetime
from pydantic import BaseModel, ConfigDict

from app.models.enums import NotificationType
from app.schemas.common import UserSummaryOut


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    type: NotificationType
    is_read: bool

    payload: dict | None = None

    created_at: datetime

    actor: UserSummaryOut | None = None


class NotificationMarkRead(BaseModel):
    is_read: bool = True
