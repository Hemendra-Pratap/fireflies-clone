"""add_workspaces_and_workspace_members_tables

Revision ID: e7f890123456
Revises: ddd38f8a6fb0
Create Date: 2026-08-13 23:48:00.000000
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'e7f890123456'
down_revision = 'ddd38f8a6fb0'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # 1. Create workspaces table
    op.create_table(
        'workspaces',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('owner_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['owner_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_workspaces_owner_id', 'workspaces', ['owner_id'], unique=False)
    op.create_index('ix_workspaces_created_at', 'workspaces', ['created_at'], unique=False)

    # 2. Create workspace_members table
    op.create_table(
        'workspace_members',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('workspace_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('role', sa.String(length=20), server_default='MEMBER', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('CURRENT_TIMESTAMP'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['workspace_id'], ['workspaces.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('workspace_id', 'user_id', name='uq_workspace_user')
    )
    op.create_index('ix_workspace_members_workspace_id', 'workspace_members', ['workspace_id'], unique=False)
    op.create_index('ix_workspace_members_user_id', 'workspace_members', ['user_id'], unique=False)

    # 3. Add workspace_id column to meetings table
    op.add_column('meetings', sa.Column('workspace_id', sa.Integer(), nullable=True))
    op.create_index('ix_meetings_workspace_id', 'meetings', ['workspace_id'], unique=False)

    # 4. Data Migration for existing users & meetings
    bind = op.get_bind()
    users = bind.execute(sa.text("SELECT id, email FROM users")).fetchall()
    for u_id, email in users:
        w_name = f"{email}'s Workspace" if email else "Personal Workspace"
        bind.execute(
            sa.text("INSERT INTO workspaces (name, owner_id) VALUES (:name, :owner_id)"),
            {"name": w_name, "owner_id": u_id}
        )
        w_id = bind.execute(
            sa.text("SELECT id FROM workspaces WHERE owner_id = :owner_id ORDER BY id DESC LIMIT 1"),
            {"owner_id": u_id}
        ).scalar()
        if w_id:
            bind.execute(
                sa.text("INSERT INTO workspace_members (workspace_id, user_id, role) VALUES (:w_id, :u_id, 'OWNER')"),
                {"w_id": w_id, "u_id": u_id}
            )
            bind.execute(
                sa.text("UPDATE meetings SET workspace_id = :w_id WHERE user_id = :u_id AND workspace_id IS NULL"),
                {"w_id": w_id, "u_id": u_id}
            )


def downgrade() -> None:
    op.drop_index('ix_meetings_workspace_id', table_name='meetings')
    op.drop_column('meetings', 'workspace_id')
    op.drop_index('ix_workspace_members_user_id', table_name='workspace_members')
    op.drop_index('ix_workspace_members_workspace_id', table_name='workspace_members')
    op.drop_table('workspace_members')
    op.drop_index('ix_workspaces_created_at', table_name='workspaces')
    op.drop_index('ix_workspaces_owner_id', table_name='workspaces')
    op.drop_table('workspaces')
