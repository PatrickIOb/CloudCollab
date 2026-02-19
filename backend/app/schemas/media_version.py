from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import MediaType


class VideoVersionCreate(BaseModel):
    """
    Payload to create a new VIDEO media version for a project.
    - version_number is assigned by the server (auto-increment per project).
    - file_url points to where the file is stored (S3/Cloudflare/etc later).
    """
    title: str | None = Field(default=None, max_length=200)
    description: str | None = None
    file_url: str
    file_mime: str | None = Field(default=None, max_length=100)
    duration_seconds: int | None = Field(default=None, ge=0)


class SetActiveVideoVersion(BaseModel):
    """
    Select which VIDEO version is currently active on the project.
    """
    video_version_id: UUID


class MediaVersionOut(BaseModel):
    """
    Minimal-but-complete output schema for MediaVersion.
    Used by:
    - project details (active video)
    - listing versions in UI
    - MusicCues later (audio_versions, active audio selection)
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID

    # kept for future / cues
    segment_id: UUID | None
    cue_id: UUID | None

    media_type: str
    version_number: int

    title: str | None
    description: str | None

    file_url: str
    file_mime: str | None
    duration_seconds: int | None

    uploaded_by: UUID

    created_at: datetime
    updated_at: datetime
