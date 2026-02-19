from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from app.models.enums import CommentType
from app.schemas.common import UserSummaryOut


class CommentCreate(BaseModel):
    """
    Request payload for creating a comment.
    - comment_type controls the permission rules (TIMELINE vs PUBLIC).
    - timecode_seconds is optional and used for timeline markers.
    - parent_id allows replies / threads.
    - media_version_id is optional; for TIMELINE/PUBLIC we will default it to the project's active VIDEO version if omitted.
    - segment_id is optional and reserved for later scene workflows.
    """
    comment_type: CommentType = CommentType.TIMELINE
    body: str = Field(..., min_length=1, max_length=5000)

    timecode_seconds: int | None = Field(default=None, ge=0)

    parent_id: UUID | None = None
    media_version_id: UUID | None = None
    segment_id: UUID | None = None


class CommentOut(BaseModel):
    """
    Response model for comments, including author summary for UI rendering.
    """
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    project_id: UUID

    comment_type: CommentType
    body: str
    timecode_seconds: int | None

    parent_id: UUID | None
    media_version_id: UUID | None
    segment_id: UUID | None

    created_at: datetime
    updated_at: datetime

    author: UserSummaryOut
