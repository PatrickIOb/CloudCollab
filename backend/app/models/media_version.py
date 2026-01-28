from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Index, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class MediaVersion(TimestampMixin, Base):
    __tablename__ = "media_versions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    segment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("segments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    media_type: Mapped[str] = mapped_column(Text, nullable=False)
    version_number: Mapped[int] = mapped_column(Integer, nullable=False)

    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    file_url: Mapped[str] = mapped_column(Text, nullable=False)
    file_mime: Mapped[str | None] = mapped_column(Text, nullable=True)
    duration_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    uploaded_by: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    project: Mapped["Project"] = relationship(
        back_populates="media_versions",
        foreign_keys=[project_id],
    )
    segment: Mapped["Segment | None"] = relationship(back_populates="media_versions")
    uploader: Mapped["User"] = relationship(back_populates="uploaded_media")
    comments: Mapped[list["Comment"]] = relationship(back_populates="media_version")

    __table_args__ = (
        CheckConstraint("media_type IN ('VIDEO','AUDIO')", name="ck_media_versions_media_type"),
        CheckConstraint("version_number >= 1", name="ck_media_versions_version_number"),
        CheckConstraint("duration_seconds IS NULL OR duration_seconds >= 0", name="ck_media_versions_duration_seconds"),
        UniqueConstraint("project_id", "segment_id", "media_type", "version_number", name="uq_media_versions_version"),
        Index("ix_media_versions_project_type", "project_id", "media_type"),
        Index("ix_media_versions_project_segment", "project_id", "segment_id"),
    )
