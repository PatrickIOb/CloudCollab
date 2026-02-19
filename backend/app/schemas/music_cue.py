from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.schemas.media_version import MediaVersionOut


class MusicCueCreate(BaseModel):
    """
    Create a cue for a specific video version.

    A cue defines a time range (start/end seconds) on the video timeline
    where an audio track (music) can be overlaid during playback.
    """
    label: str | None = Field(default=None, max_length=200)
    start_seconds: int = Field(..., ge=0)
    end_seconds: int = Field(..., ge=0)


class MusicCueUpdate(BaseModel):
    """
    Patch cue fields:
    - label: rename cue
    - start_seconds/end_seconds: adjust playback range
    - active_audio_version_id: choose which uploaded audio version is active
    """
    label: str | None = Field(default=None, max_length=200)
    start_seconds: int | None = Field(default=None, ge=0)
    end_seconds: int | None = Field(default=None, ge=0)
    active_audio_version_id: UUID | None = None


class MusicCueOut(BaseModel):
    """
    Cue details for UI playback:
    - where it plays (start/end)
    - which audio is active
    - which audio versions exist
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID
    video_version_id: UUID

    label: str | None
    start_seconds: int
    end_seconds: int

    active_audio_version_id: UUID | None
    created_at: datetime
    updated_at: datetime

    # Expansions for UI convenience:
    active_audio_version: MediaVersionOut | None = None
    audio_versions: list[MediaVersionOut] = Field(default_factory=list)
