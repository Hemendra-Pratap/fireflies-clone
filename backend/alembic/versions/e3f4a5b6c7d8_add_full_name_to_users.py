"""add_full_name_to_users

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-08-14 01:45:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e3f4a5b6c7d8'
down_revision = 'd2e3f4a5b6c7'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('users', sa.Column('full_name', sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column('users', 'full_name')
