"""Backfill comments.media_version_id from projects.active_media_version_id

Revision ID: b1c9d9f0c3a1
Revises: ee7ae269db17
Create Date: 2026-02-19

This migration backfills NULL media_version_id for old TIMELINE/PUBLIC comments
(created before media_versions existed) to the project's active_media_version_id.

"""

from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = "b1c9d9f0c3a1"
down_revision: Union[str, Sequence[str], None] = "ee7ae269db17"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Backfill NULL media_version_id for TIMELINE and PUBLIC comments.

    Conditions:
    - comments.media_version_id IS NULL
    - projects.active_media_version_id IS NOT NULL
    - comment_type IN ('TIMELINE', 'PUBLIC')
    """
    op.execute(
        """
        UPDATE comments c
        SET media_version_id = p.active_media_version_id
        FROM projects p
        WHERE c.project_id = p.id
          AND c.media_version_id IS NULL
          AND p.active_media_version_id IS NOT NULL
          AND c.comment_type IN ('TIMELINE', 'PUBLIC');
        """
    )


def downgrade() -> None:
    """
    No-op downgrade.

    We intentionally do not revert the backfill because the application relies on
    version-scoped comments going forward.
    """
    pass
