from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin
from app.models.enums import CommentType


class Comment(TimestampMixin, Base):
    """
    A comment belongs to a project and can optionally reference:
    - a specific media_version (e.g. feedback for video v2 or audio v3)
    - a segment (optional feature for later scene-based workflows)
    - a parent comment (replies / threads)

    We support two comment modes:
    - TIMELINE: collaboration comments (timecode-based) for owner + ACTIVE members
    - PUBLIC: public comments on PUBLIC + COMPLETED projects
    """

    __tablename__ = "comments"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    project_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Optional (future): attach comment to a "scene"/segment
    segment_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("segments.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Optional: attach comment to a specific media version (video/audio)
    media_version_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("media_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    author_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Threading / replies (optional)
    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("comments.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )

    # TIMELINE or PUBLIC
    comment_type: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        default=CommentType.TIMELINE.value,
    )

    body: Mapped[str] = mapped_column(Text, nullable=False)

    # Time marker in seconds (SoundCloud-style). Optional.
    # For PUBLIC comments this is usually NULL.
    timecode_seconds: Mapped[int | None] = mapped_column(Integer, nullable=True)

    # Relationships
    project: Mapped["Project"] = relationship(back_populates="comments")
    segment: Mapped["Segment | None"] = relationship(back_populates="comments")
    media_version: Mapped["MediaVersion | None"] = relationship(back_populates="comments")
    author: Mapped["User"] = relationship(back_populates="comments")
    parent: Mapped["Comment | None"] = relationship(
        "Comment",
        foreign_keys=[parent_id],
        remote_side=[id],
        back_populates="replies",
    )

    replies: Mapped[list["Comment"]] = relationship(
        "Comment",
        foreign_keys=[parent_id],
        back_populates="parent",
        cascade="all, delete-orphan",
    )


    __table_args__ = (
        CheckConstraint(
            "timecode_seconds IS NULL OR timecode_seconds >= 0",
            name="ck_comments_timecode_seconds",
        ),
        CheckConstraint(
            "comment_type IN ('TIMELINE','PUBLIC')",
            name="ck_comments_type",
        ),
    )
