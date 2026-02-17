from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import ProjectMemberRole, ProjectMemberStatus


class ProjectMember(TimestampMixin, Base):
    __tablename__ = "project_members"

    # Composite PK: one row per (project, user)
    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        primary_key=True,
    )

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    role: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=ProjectMemberRole.CONTRIBUTOR.value,
    )

    status: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=ProjectMemberStatus.INVITED.value,
    )

    project: Mapped["Project"] = relationship(back_populates="members")
    user: Mapped["User"] = relationship(back_populates="memberships")

    __table_args__ = (
        CheckConstraint(
            "role IN ('COMPOSER','FILMMAKER','CONTRIBUTOR')",
            name="ck_project_members_role",
        ),
        CheckConstraint(
            "status IN ('INVITED','ACTIVE','REMOVED')",
            name="ck_project_members_status",
        ),
    )
