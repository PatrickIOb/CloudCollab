# app/schemas/user.py
from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field, field_validator, AnyUrl, ConfigDict
import re

from app.models.enums import AvailabilityStatus, UserRole, PrimaryFocus
from app.schemas.project import ProjectOut


ALLOWED_SOCIAL_KEYS = {
    "website",
    "instagram",
    "youtube",
    "vimeo",
    "spotify",
    "soundcloud",
    "tiktok",
    "x",
    "linkedin",
}


USERNAME_RE = re.compile(r"^[a-z0-9._]{3,30}$")

class UserCreate(BaseModel):
    email: EmailStr
    password: str
    display_name: str
    username: str = Field(min_length=3, max_length=30)

    @field_validator("username")
    @classmethod
    def validate_username(cls, v: str) -> str:
        v = v.strip().lower()
        if not USERNAME_RE.match(v):
            raise ValueError("username must be 3-30 chars, lowercase, only a-z 0-9 . _")
        return v


class UserOut(BaseModel):
    """Existing minimal output used by /auth endpoints."""
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    display_name: str
    username: str


class ComposerProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    primary_focus: PrimaryFocus | None = None
    genres: str | None = None
    instruments: str | None = None


class FilmmakerProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    disciplines: str | None = None
    genres: str | None = None


class UserPublicProfileOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    display_name: str
    username: str

    role: UserRole | None = None
    avatar_url: str | None = None
    bio: str | None = None
    availability_status: AvailabilityStatus | None = None
    languages: str | None = None
    social_links: dict[str, Any] | None = None

    composer_profile: ComposerProfileOut | None = None
    filmmaker_profile: FilmmakerProfileOut | None = None

    public_projects: list[ProjectOut] = Field(default_factory=list)


class UserMeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: UUID
    email: EmailStr
    display_name: str
    username: str

    role: UserRole | None = None
    avatar_url: str | None = None
    bio: str | None = None
    availability_status: AvailabilityStatus | None = None
    languages: str | None = None
    social_links: dict[str, Any] | None = None

    composer_profile: ComposerProfileOut | None = None
    filmmaker_profile: FilmmakerProfileOut | None = None

    projects: list[ProjectOut] = Field(default_factory=list)


class ComposerProfileUpdate(BaseModel):
    primary_focus: PrimaryFocus | None = None
    genres: str | None = None
    instruments: str | None = None


class FilmmakerProfileUpdate(BaseModel):
    disciplines: str | None = None
    genres: str | None = None


class UserMeUpdate(BaseModel):
    display_name: str | None = Field(default=None, min_length=2, max_length=80)

    role: UserRole | None = None
    avatar_url: str | None = Field(default=None, max_length=500)
    bio: str | None = Field(default=None, max_length=2000)
    availability_status: AvailabilityStatus | None = None
    languages: str | None = Field(default=None, max_length=200)

    social_links: dict[str, Any] | None = None

    composer_profile: ComposerProfileUpdate | None = None
    filmmaker_profile: FilmmakerProfileUpdate | None = None

    @field_validator("social_links")
    @classmethod
    def validate_social_links(cls, v: dict[str, Any] | None):
        if v is None:
            return v

        # only allow known keys
        for k in v.keys():
            if k not in ALLOWED_SOCIAL_KEYS:
                raise ValueError(f"Unsupported social link key: {k}")

        # validate URLs (only for string values)
        for k, val in v.items():
            if val is None:
                continue
            if not isinstance(val, str):
                raise ValueError(f"Social link '{k}' must be a string URL")
            # Pydantic AnyUrl validation
            AnyUrl(val)

        return v
