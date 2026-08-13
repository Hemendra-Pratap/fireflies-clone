"""add_user_id_to_meetings

Revision ID: bb5ff6dd5e76
Revises: 67c6b0b54ca5
Create Date: 2026-08-13 19:05:19.009204
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'bb5ff6dd5e76'
down_revision = '67c6b0b54ca5'
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.add_column(sa.Column('user_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_meetings_user_id'), ['user_id'], unique=False)
        batch_op.create_foreign_key('fk_meetings_user_id_users', 'users', ['user_id'], ['id'], ondelete='SET NULL')


def downgrade() -> None:
    with op.batch_alter_table('meetings', schema=None) as batch_op:
        batch_op.drop_constraint('fk_meetings_user_id_users', type_='foreignkey')
        batch_op.drop_index(batch_op.f('ix_meetings_user_id'))
        batch_op.drop_column('user_id')
