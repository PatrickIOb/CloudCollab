from __future__ import annotations

from enum import Enum


class ProjectStatus(str, Enum):
    DRAFT = "DRAFT"
    ACTIVE = "ACTIVE"
    COMPLETED = "COMPLETED"


class ProjectVisibility(str, Enum):
    PRIVATE = "PRIVATE"
    UNLISTED = "UNLISTED"
    PUBLIC = "PUBLIC"


class ProjectCategory(str, Enum):
    NARRATIVE_FILM = "NARRATIVE_FILM"
    ACTION_SPORTS = "ACTION_SPORTS"
    EXPERIMENTAL = "EXPERIMENTAL"


class MemberRole(str, Enum):
    OWNER = "OWNER"
    CONTRIBUTOR = "CONTRIBUTOR"


class MediaType(str, Enum):
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"


class AvailabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    LIMITED = "LIMITED"
    UNAVAILABLE = "UNAVAILABLE"
