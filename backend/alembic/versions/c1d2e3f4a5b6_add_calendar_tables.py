"""add_calendar_tables

Revision ID: c1d2e3f4a5b6
Revises: f8a901234567
Create Date: 2026-08-14 01:25:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'c1d2e3f4a5b6'
down_revision = 'f8a901234567'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create calendar_connections table
    op.create_table(
        'calendar_connections',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('provider', sa.String(length=50), server_default='google', nullable=False),
        sa.Column('account_email', sa.String(length=255), nullable=True),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('refresh_token', sa.Text(), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='active', nullable=False),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'provider', 'account_email', name='uq_calendar_conn_workspace_provider_email')
    )
    op.create_index('ix_calendar_connections_user_id', 'calendar_connections', ['user_id'], unique=False)
    op.create_index('ix_calendar_connections_workspace_id', 'calendar_connections', ['workspace_id'], unique=False)

    # Create calendar_events table
    op.create_table(
        'calendar_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('calendar_connection_id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('external_event_id', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('timezone', sa.String(length=100), server_default='UTC', nullable=True),
        sa.Column('organizer_email', sa.String(length=255), nullable=True),
        sa.Column('attendees_json', sa.Text(), nullable=True),
        sa.Column('meeting_url', sa.String(length=1024), nullable=True),
        sa.Column('status', sa.String(length=50), server_default='confirmed', nullable=False),
        sa.Column('meeting_id', sa.Integer(), nullable=True),
        sa.Column('synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['calendar_connection_id'], ['calendar_connections.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['meeting_id'], ['meetings.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('calendar_connection_id', 'external_event_id', name='uq_calendar_event_connection_external_id')
    )
    op.create_index('ix_calendar_events_calendar_connection_id', 'calendar_events', ['calendar_connection_id'], unique=False)
    op.create_index('ix_calendar_events_workspace_id', 'calendar_events', ['workspace_id'], unique=False)
    op.create_index('ix_calendar_events_user_id', 'calendar_events', ['user_id'], unique=False)
    op.create_index('ix_calendar_events_external_event_id', 'calendar_events', ['external_event_id'], unique=False)
    op.create_index('ix_calendar_events_start_time', 'calendar_events', ['start_time'], unique=False)
    op.create_index('ix_calendar_events_end_time', 'calendar_events', ['end_time'], unique=False)
    op.create_index('ix_calendar_events_meeting_id', 'calendar_events', ['meeting_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_calendar_events_meeting_id', table_name='calendar_events')
    op.drop_index('ix_calendar_events_end_time', table_name='calendar_events')
    op.drop_index('ix_calendar_events_start_time', table_name='calendar_events')
    op.drop_index('ix_calendar_events_external_event_id', table_name='calendar_events')
    op.drop_index('ix_calendar_events_user_id', table_name='calendar_events')
    op.drop_index('ix_calendar_events_workspace_id', table_name='calendar_events')
    op.drop_index('ix_calendar_events_calendar_connection_id', table_name='calendar_events')
    op.drop_table('calendar_events')

    op.drop_index('ix_calendar_connections_workspace_id', table_name='calendar_connections')
    op.drop_index('ix_calendar_connections_user_id', table_name='calendar_connections')
    op.drop_table('calendar_connections')
