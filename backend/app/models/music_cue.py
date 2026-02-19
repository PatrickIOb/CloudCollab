from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, ForeignKey, Integer, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class MusicCue(TimestampMixin, Base):
    """
    MusicCue = an audio placement on a specific VIDEO media version.

    A cue belongs to:
      - a project
      - a specific video media version (video_version_id)

    A cue defines when an audio should play (start/end seconds).
    Multiple AUDIO MediaVersions can be uploaded for the same cue (versions),
    and the cue can point to one active audio version (active_audio_version_id).

    This matches your rule:
      - when a new video media version exists, music must be uploaded again
        -> because cues are tied to a specific video_version_id.
    """

    __tablename__ = "music_cues"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    project_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("projects.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # The VIDEO MediaVersion this cue belongs to.
    video_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media_versions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    label: Mapped[str | None] = mapped_column(Text, nullable=True)

    start_seconds: Mapped[int] = mapped_column(Integer, nullable=False)
    end_seconds: Mapped[int] = mapped_column(Integer, nullable=False)

    # Which AUDIO MediaVersion is currently selected for playback at this cue.
    active_audio_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("media_versions.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    project: Mapped["Project"] = relationship(back_populates="music_cues")

    # We don't enforce "media_type=VIDEO" via DB constraint; we enforce it in code.
    video_version: Mapped["MediaVersion"] = relationship(
        foreign_keys=[video_version_id],
    )

    active_audio_version: Mapped["MediaVersion | None"] = relationship(
        foreign_keys=[active_audio_version_id],
        post_update=True,
    )

    audio_versions: Mapped[list["MediaVersion"]] = relationship(
        back_populates="cue",
        cascade="all, delete-orphan",
        foreign_keys="MediaVersion.cue_id",
    )

    __table_args__ = (
        CheckConstraint("start_seconds >= 0", name="ck_music_cues_start_seconds"),
        CheckConstraint("end_seconds >= 0", name="ck_music_cues_end_seconds"),
        CheckConstraint("end_seconds >= start_seconds", name="ck_music_cues_time_range"),
    )
