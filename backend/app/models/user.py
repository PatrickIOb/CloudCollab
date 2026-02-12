from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, Text, String
from sqlalchemy.dialects.postgresql import UUID as PG_UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(PG_UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    username: Mapped[str] = mapped_column(
    String(30),
    unique=True,
    index=True,
    nullable=False,
)



    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    availability_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    social_links: Mapped[dict | None] = mapped_column(JSONB, nullable=True)
    role: Mapped[str | None] = mapped_column(Text, nullable=True)
    languages: Mapped[str | None] = mapped_column(Text, nullable=True)



    owned_projects: Mapped[list["Project"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    memberships: Mapped[list["ProjectMember"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    uploaded_media: Mapped[list["MediaVersion"]] = relationship(back_populates="uploader")
    comments: Mapped[list["Comment"]] = relationship(back_populates="author")

    composer_profile: Mapped["ComposerProfile | None"] = relationship(
    back_populates="user",
    uselist=False,
    cascade="all, delete-orphan",
)

    filmmaker_profile: Mapped["FilmmakerProfile | None"] = relationship(
    back_populates="user",
    uselist=False,
    cascade="all, delete-orphan",
)


    __table_args__ = (
    CheckConstraint(
        "availability_status IS NULL OR availability_status IN ('AVAILABLE','LIMITED','BUSY')",
        name="ck_users_availability_status",
    ),
    CheckConstraint(
        "role IS NULL OR role IN ('FILMMAKER','COMPOSER','BOTH')",
        name="ck_users_role",
    ),
    CheckConstraint(
        "username ~ '^[a-z0-9._]{3,30}$'",
        name="ck_users_username_format",
    ),
)


