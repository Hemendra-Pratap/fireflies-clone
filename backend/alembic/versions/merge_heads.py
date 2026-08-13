"""Merge Alembic migration heads

Revision ID: merge_heads_001
Revises: bb5ff6dd5e76, f4a5b6c7d8e9
Create Date: 2026-08-14

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'merge_heads_001'
down_revision = ('bb5ff6dd5e76', 'f4a5b6c7d8e9')
branch_labels = None
depends_on = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
