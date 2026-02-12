from __future__ import annotations
import uuid
from sqlalchemy import CheckConstraint, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, TimestampMixin

class ComposerProfile(TimestampMixin, Base):
    __tablename__ = "composer_profiles"

    user_id: Mapped[uuid.UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
    )

    primary_focus: Mapped[str | None] = mapped_column(Text, nullable=True)
    genres: Mapped[str | None] = mapped_column(Text, nullable=True)
    instruments: Mapped[str | None] = mapped_column(Text, nullable=True)

    user: Mapped["User"] = relationship(back_populates="composer_profile")

    __table_args__ = (
        CheckConstraint(
            "primary_focus IS NULL OR primary_focus IN ('INSTRUMENTAL','ELECTRONIC','HYBRID')",
            name="ck_composer_profiles_primary_focus",
        ),
    )
