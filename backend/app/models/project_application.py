from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import ApplicationStatus


class ProjectApplication(TimestampMixin, Base):
    __tablename__ = "project_applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    status: Mapped[str] = mapped_column(Text, nullable=False, default=ApplicationStatus.PENDING.value)

    message: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship()
    user: Mapped["User"] = relationship()

    __table_args__ = (
        UniqueConstraint("project_id", "user_id", name="uq_project_applications_project_user"),
        CheckConstraint(
            "status IN ('PENDING','ACCEPTED','REJECTED','WITHDRAWN')",
            name="ck_project_applications_status",
        ),
    )
