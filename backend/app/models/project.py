from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import ProjectStatus, ProjectVisibility


class Project(TimestampMixin, Base):
    __tablename__ = "projects"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    owner_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    category: Mapped[str] = mapped_column(Text, nullable=False)
    sub_category: Mapped[str | None] = mapped_column(Text, nullable=True)

    status: Mapped[str] = mapped_column(Text, nullable=False, default=ProjectStatus.DRAFT.value)
    visibility: Mapped[str] = mapped_column(Text, nullable=False, default=ProjectVisibility.PRIVATE.value)

    active_media_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media_versions.id", ondelete="SET NULL"),
        nullable=True,
    )

    owner: Mapped["User"] = relationship(back_populates="owned_projects")
    members: Mapped[list["ProjectMember"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    segments: Mapped[list["Segment"]] = relationship(back_populates="project", cascade="all, delete-orphan")
    media_versions: Mapped[list["MediaVersion"]] = relationship(
        back_populates="project",
        cascade="all, delete-orphan",
        foreign_keys="MediaVersion.project_id",
    )
    comments: Mapped[list["Comment"]] = relationship(back_populates="project", cascade="all, delete-orphan")

    active_media_version: Mapped["MediaVersion | None"] = relationship(
        foreign_keys=[active_media_version_id],
        post_update=True,
    )

    __table_args__ = (
        CheckConstraint("category IN ('NARRATIVE_FILM','ACTION_SPORTS','EXPERIMENTAL')", name="ck_projects_category"),
        CheckConstraint("status IN ('DRAFT','ACTIVE','COMPLETED')", name="ck_projects_status"),
        CheckConstraint("visibility IN ('PRIVATE','UNLISTED','PUBLIC')", name="ck_projects_visibility"),
    )
