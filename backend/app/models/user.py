from __future__ import annotations

import uuid

from sqlalchemy import CheckConstraint, Text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(Text, nullable=False)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)

    bio: Mapped[str | None] = mapped_column(Text, nullable=True)
    availability_status: Mapped[str | None] = mapped_column(Text, nullable=True)
    avatar_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    social_links: Mapped[dict | None] = mapped_column(JSONB, nullable=True)


    owned_projects: Mapped[list["Project"]] = relationship(back_populates="owner", cascade="all, delete-orphan")
    memberships: Mapped[list["ProjectMember"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    uploaded_media: Mapped[list["MediaVersion"]] = relationship(back_populates="uploader")
    comments: Mapped[list["Comment"]] = relationship(back_populates="author")

    __table_args__ = (
        CheckConstraint(
            "availability_status IS NULL OR availability_status IN ('AVAILABLE','LIMITED','UNAVAILABLE')",
            name="ck_users_availability_status",
        ),
    )
