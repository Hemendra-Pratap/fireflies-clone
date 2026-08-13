"""add_observability_fields_to_jobs

Revision ID: f4a5b6c7d8e9
Revises: e3f4a5b6c7d8
Create Date: 2026-08-14 02:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f4a5b6c7d8e9'
down_revision = 'e3f4a5b6c7d8'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column('jobs', sa.Column('started_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('jobs', sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('jobs', sa.Column('last_heartbeat_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('jobs', sa.Column('worker_id', sa.String(length=100), nullable=True))
    op.add_column('jobs', sa.Column('correlation_id', sa.String(length=100), nullable=True))
    op.create_index('ix_jobs_last_heartbeat', 'jobs', ['last_heartbeat_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_jobs_last_heartbeat', table_name='jobs')
    op.drop_column('jobs', 'correlation_id')
    op.drop_column('jobs', 'worker_id')
    op.drop_column('jobs', 'last_heartbeat_at')
    op.drop_column('jobs', 'completed_at')
    op.drop_column('jobs', 'started_at')
