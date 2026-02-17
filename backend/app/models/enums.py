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


class MemberRole(str, Enum):
    OWNER = "OWNER"
    CONTRIBUTOR = "CONTRIBUTOR"


class MediaType(str, Enum):
    VIDEO = "VIDEO"
    AUDIO = "AUDIO"


class ProjectCategory(str, Enum):
    NARRATIVE_FILM = "NARRATIVE_FILM"
    EXPERIMENTAL = "EXPERIMENTAL"
    ACTION_SPORTS = "ACTION_SPORTS"
    MOTION_GRAPHICS = "MOTION_GRAPHICS"
    REELS = "REELS" 


class AvailabilityStatus(str, Enum):
    AVAILABLE = "AVAILABLE"
    LIMITED = "LIMITED"
    BUSY = "BUSY"


class UserRole(str, Enum):
    FILMMAKER = "FILMMAKER"
    COMPOSER = "COMPOSER"
    BOTH = "BOTH"


class PrimaryFocus(str, Enum):
    INSTRUMENTAL = "INSTRUMENTAL"
    ELECTRONIC = "ELECTRONIC"
    HYBRID = "HYBRID"


class ProjectMemberRole(str, Enum):
    COMPOSER = "COMPOSER"
    FILMMAKER = "FILMMAKER"
    CONTRIBUTOR = "CONTRIBUTOR"


class ProjectMemberStatus(str, Enum):
    INVITED = "INVITED"
    ACTIVE = "ACTIVE"
    REMOVED = "REMOVED"


class ApplicationStatus(str, Enum):
    PENDING = "PENDING"
    ACCEPTED = "ACCEPTED"
    REJECTED = "REJECTED"
    WITHDRAWN = "WITHDRAWN"


class NotificationType(str, Enum):
    INVITE_RECEIVED = "INVITE_RECEIVED"
    INVITE_ACCEPTED = "INVITE_ACCEPTED"

    APPLICATION_RECEIVED = "APPLICATION_RECEIVED"
    APPLICATION_ACCEPTED = "APPLICATION_ACCEPTED"
    APPLICATION_REJECTED = "APPLICATION_REJECTED"
