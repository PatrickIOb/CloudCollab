from __future__ import annotations

from pydantic import BaseModel, ConfigDict
from typing import Any

from app.schemas.project import ProjectOut
from app.schemas.media_version import MediaVersionOut
from app.schemas.music_cue import MusicCueOut
from app.schemas.comment import CommentOut


class PlayerPageOut(BaseModel):
    """
    Payload for the React "Player Page".

    - Project basics
    - Active VIDEO media version (the one to play)
    - Music cues for that active video version (including active audio + all audio versions per cue)
    - Timeline comments (collaboration notes) for the active video version
    - Public comments (optional)

    Notes:
    - Timeline comments require auth (owner/member/invited) unless project is PUBLIC.
    - Public comments can be readable without auth for PUBLIC projects.
    """
    model_config = ConfigDict(from_attributes=True)

    project: ProjectOut
    active_video: MediaVersionOut
    cues: list[MusicCueOut]
    timeline_comments: list[CommentOut]
    public_comments: list[CommentOut]
