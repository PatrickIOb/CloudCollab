from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class Segment(TimestampMixin, Base):
    __tablename__ = "segments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)

    start_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)
    end_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    tags: Mapped[str | None] = mapped_column(Text, nullable=True)

    project: Mapped["Project"] = relationship(back_populates="segments")
    media_versions: Mapped[list["MediaVersion"]] = relationship(back_populates="segment")
    comments: Mapped[list["Comment"]] = relationship(back_populates="segment")

    __table_args__ = (
        CheckConstraint("start_seconds IS NULL OR start_seconds >= 0", name="ck_segments_start_seconds"),
        CheckConstraint("end_seconds IS NULL OR end_seconds >= 0", name="ck_segments_end_seconds"),
        CheckConstraint(
            "start_seconds IS NULL OR end_seconds IS NULL OR end_seconds >= start_seconds",
            name="ck_segments_time_range",
        ),
    )
