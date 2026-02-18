"""notifications add comment types

Revision ID: e5e44a545816
Revises: XXXX
Create Date: 2026-02-18 16:25:35.723482

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e5e44a545816'
down_revision: Union[str, Sequence[str], None] = 'XXXX'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE notifications DROP CONSTRAINT IF EXISTS ck_notifications_type")
    op.execute(
        "ALTER TABLE notifications "
        "ADD CONSTRAINT ck_notifications_type "
        "CHECK (type IN ("
        "'INVITE_RECEIVED','INVITE_ACCEPTED',"
        "'APPLICATION_RECEIVED','APPLICATION_ACCEPTED','APPLICATION_REJECTED',"
        "'COMMENT_TIMELINE_CREATED','COMMENT_PUBLIC_CREATED','COMMENT_REPLY_CREATED'"
        "))"
    )

def downgrade() -> None:
    op.execute("ALTER TABLE notifications DROP CONSTRAINT IF EXISTS ck_notifications_type")

