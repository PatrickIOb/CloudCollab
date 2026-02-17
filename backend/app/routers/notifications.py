from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, update, func
from sqlalchemy.orm import Session, joinedload

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.notification import Notification
from app.schemas.notification import NotificationOut, NotificationMarkRead

router = APIRouter(prefix="/notifications", tags=["notifications"])


@router.get("", response_model=list[NotificationOut])
def list_my_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
):
    stmt = (
        select(Notification)
        .where(Notification.recipient_id == current_user.id)
        .options(joinedload(Notification.actor))
        .order_by(Notification.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    if unread_only:
        stmt = stmt.where(Notification.is_read == False)  # noqa: E712

    return db.scalars(stmt).all()

@router.get("/unread-count")
def unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(func.count()).select_from(Notification).where(
        Notification.recipient_id == current_user.id,
        Notification.is_read == False,  # noqa: E712
    )
    count = db.scalar(stmt) or 0
    return {"unread_count": int(count)}


@router.patch("/{notification_id:uuid}", response_model=NotificationOut)
def mark_notification_read(
    notification_id: UUID,
    data: NotificationMarkRead,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    notif = db.get(Notification, notification_id)
    if not notif or notif.recipient_id != current_user.id:
        raise HTTPException(status_code=404, detail="Notification not found")

    notif.is_read = data.is_read
    db.commit()

    # reload with actor for response
    notif = db.scalar(
        select(Notification)
        .where(Notification.id == notification_id)
        .options(joinedload(Notification.actor))
    )
    return notif


@router.post("/read-all", status_code=204)
def mark_all_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.execute(
        update(Notification)
        .where(Notification.recipient_id == current_user.id, Notification.is_read == False)  # noqa: E712
        .values(is_read=True)
    )
    db.commit()
    return None


@router.post("/read-by-project/{project_id:uuid}", status_code=204)
def mark_read_by_project(
    project_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    db.execute(
        update(Notification)
        .where(
            Notification.recipient_id == current_user.id,
            Notification.project_id == project_id,
            Notification.is_read == False,  # noqa: E712
        )
        .values(is_read=True)
    )
    db.commit()
    return None
