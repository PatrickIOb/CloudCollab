"""add ck_comments_type

Revision ID: a6a38b2ef62e
Revises: ab4d51906fc1
Create Date: 2026-02-17 21:58:42.701877

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a6a38b2ef62e'
down_revision: Union[str, Sequence[str], None] = 'ab4d51906fc1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


revision = "XXXX"
down_revision = "ab4d51906fc1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("ALTER TABLE comments DROP CONSTRAINT IF EXISTS ck_comments_type")
    op.execute(
        "ALTER TABLE comments "
        "ADD CONSTRAINT ck_comments_type "
        "CHECK (comment_type IN ('TIMELINE','PUBLIC'))"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE comments DROP CONSTRAINT IF EXISTS ck_comments_type")
