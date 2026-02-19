from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select, func
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth.dependencies import get_current_user
from app.models.user import User
from app.models.project import Project
from app.models.music_cue import MusicCue
from app.models.media_version import MediaVersion
from app.models.project_member import ProjectMember
from app.models.enums import MediaType, ProjectMemberStatus, ProjectMemberRole

from app.schemas.media_version import MediaVersionOut

router = APIRouter(prefix="/projects", tags=["music-cues"])


class CueAudioUpload(BaseModel):
    """
    Payload to upload a new AUDIO version for a specific MusicCue.

    Notes:
    - file_url points to your storage (later S3/R2/etc).
    - version_number is assigned by the server (auto-increment per cue).
    """
    file_url: str
    file_mime: str | None = Field(default=None, max_length=100)
    duration_seconds: int | None = Field(default=None, ge=0)
    title: str | None = Field(default=None, max_length=200)
    description: str | None = None


def get_project_or_404(db: Session, project_id: UUID) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def is_active_member(db: Session, project_id: UUID, user_id: UUID) -> ProjectMember | None:
    """
    Returns the ProjectMember row if the user is an ACTIVE member, else None.
    """
    stmt = select(ProjectMember).where(
        ProjectMember.project_id == project_id,
        ProjectMember.user_id == user_id,
        ProjectMember.status == ProjectMemberStatus.ACTIVE.value,
    )
    return db.scalar(stmt)


def ensure_can_upload_cue_audio(db: Session, project: Project, user: User) -> None:
    """
    Permission rule for cue-audio uploads (MVP):
    - Owner can upload
    - ACTIVE COMPOSER members can upload
    """
    if project.owner_id == user.id:
        return

    member = is_active_member(db, project.id, user.id)
    if not member:
        raise HTTPException(status_code=403, detail="Not allowed")

    if member.role != ProjectMemberRole.COMPOSER.value:
        raise HTTPException(status_code=403, detail="Only composers can upload cue audio")


@router.post(
    "/{project_id:uuid}/cues/{cue_id:uuid}/audio-versions",
    response_model=MediaVersionOut,
    status_code=status.HTTP_201_CREATED,
)
def upload_audio_version_for_cue(
    project_id: UUID,
    cue_id: UUID,
    data: CueAudioUpload,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Upload a new AUDIO MediaVersion for a MusicCue.

    Rules:
    - Only owner or ACTIVE COMPOSER members can upload.
    - Audio versions are versioned per cue (version_number increments).
    - Older versions are NOT deleted.
    - If cue has no active_audio_version yet, the first upload becomes active automatically.
    """
    project = get_project_or_404(db, project_id)
    ensure_can_upload_cue_audio(db, project, current_user)

    cue = db.get(MusicCue, cue_id)
    if not cue or cue.project_id != project.id:
        raise HTTPException(status_code=404, detail="Cue not found")

    # Determine next version_number for AUDIO versions for this cue
    stmt = select(func.coalesce(func.max(MediaVersion.version_number), 0)).where(
        MediaVersion.project_id == project.id,
        MediaVersion.cue_id == cue.id,
        MediaVersion.media_type == MediaType.AUDIO.value,
    )
    max_v = db.scalar(stmt) or 0
    next_v = int(max_v) + 1

    mv = MediaVersion(
        project_id=project.id,
        segment_id=None,          # segments are optional later
        cue_id=cue.id,            # IMPORTANT: tie audio to cue
        media_type=MediaType.AUDIO.value,
        version_number=next_v,
        title=data.title,
        description=data.description,
        file_url=data.file_url,
        file_mime=data.file_mime,
        duration_seconds=data.duration_seconds,
        uploaded_by=current_user.id,
    )

    db.add(mv)
    db.commit()
    db.refresh(mv)

    # Auto-select latest upload as active
    cue.active_audio_version_id = mv.id
    db.commit()

    return mv
