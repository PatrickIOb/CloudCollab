"""fix project_members role constraint

Revision ID: 4909d4925499
Revises: 80dbd787a8d8
Create Date: 2026-02-17 16:23:36.444311

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '4909d4925499'
down_revision: Union[str, Sequence[str], None] = '80dbd787a8d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    op.drop_constraint("ck_project_members_role", "project_members", type_="check")
    op.create_check_constraint(
        "ck_project_members_role",
        "project_members",
        "role IN ('COMPOSER','FILMMAKER','CONTRIBUTOR')",
    )

def downgrade() -> None:
    op.drop_constraint("ck_project_members_role", "project_members", type_="check")
    op.create_check_constraint(
        "ck_project_members_role",
        "project_members",
        "role IN ('OWNER','CONTRIBUTOR')",
    )
