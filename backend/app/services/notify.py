from __future__ import annotations

from uuid import UUID
from sqlalchemy.orm import Session

from app.models.notification import Notification


def create_notification(
    db: Session,
    *,
    recipient_id: UUID,
    type: str,
    actor_id: UUID | None = None,
    project_id: UUID | None = None,
    payload: dict | None = None,
) -> Notification:
    n = Notification(
        recipient_id=recipient_id,
        actor_id=actor_id,
        project_id=project_id,
        type=type,
        payload=payload,
        is_read=False,
    )
    db.add(n)
    return n
