"""add_jobs_table

Revision ID: f8a901234567
Revises: e7f890123456
Create Date: 2026-08-13 23:52:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f8a901234567'
down_revision = 'e7f890123456'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'jobs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('job_type', sa.String(length=30), nullable=False),
        sa.Column('meeting_id', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=30), server_default='pending', nullable=False),
        sa.Column('attempts', sa.Integer(), server_default='0', nullable=False),
        sa.Column('max_retries', sa.Integer(), server_default='3', nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['meeting_id'], ['meetings.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_jobs_meeting_id', 'jobs', ['meeting_id'], unique=False)
    op.create_index('ix_jobs_status', 'jobs', ['status'], unique=False)
    op.create_index('ix_jobs_created_at', 'jobs', ['created_at'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_jobs_created_at', table_name='jobs')
    op.drop_index('ix_jobs_status', table_name='jobs')
    op.drop_index('ix_jobs_meeting_id', table_name='jobs')
    op.drop_table('jobs')
