"""initial_schema

Revision ID: 0540508442f9
Revises: 
Create Date: 2026-08-13 03:19:32.093276
"""

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '0540508442f9'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "meetings",
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("source_name", sa.String(length=100), nullable=True),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(length=30), server_default="completed", nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_meetings_created_at", "meetings", ["created_at"], unique=False)
    op.create_index("ix_meetings_recorded_at", "meetings", ["recorded_at"], unique=False)
    op.create_index("ix_meetings_status", "meetings", ["status"], unique=False)
    op.create_index("ix_meetings_title", "meetings", ["title"], unique=False)

    op.create_table(
        "chapters",
        sa.Column("meeting_id", sa.Integer(), nullable=False),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("start_time_ms", sa.Integer(), nullable=False),
        sa.Column("end_time_ms", sa.Integer(), nullable=True),
        sa.Column("summary", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("end_time_ms IS NULL OR end_time_ms >= start_time_ms", name="ck_chapters_end_after_start"),
        sa.CheckConstraint("start_time_ms >= 0", name="ck_chapters_start_nonnegative"),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("meeting_id", "sequence_number", name="uq_chapters_meeting_sequence"),
    )
    op.create_index("ix_chapters_meeting_id", "chapters", ["meeting_id"], unique=False)
    op.create_index("ix_chapters_meeting_id_sequence_number", "chapters", ["meeting_id", "sequence_number"], unique=False)
    op.create_index("ix_chapters_meeting_id_start_time_ms", "chapters", ["meeting_id", "start_time_ms"], unique=False)

    op.create_table(
        "participants",
        sa.Column("meeting_id", sa.Integer(), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=False),
        sa.Column("speaker_label", sa.String(length=100), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("is_host", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_participants_meeting_id", "participants", ["meeting_id"], unique=False)
    op.create_index("ix_participants_meeting_id_display_name", "participants", ["meeting_id", "display_name"], unique=False)

    op.create_table(
        "summaries",
        sa.Column("meeting_id", sa.Integer(), nullable=False),
        sa.Column("overview", sa.Text(), nullable=False),
        sa.Column("key_points", sa.Text(), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("meeting_id"),
    )
    op.create_index("ix_summaries_meeting_id", "summaries", ["meeting_id"], unique=True)

    op.create_table(
        "action_items",
        sa.Column("meeting_id", sa.Integer(), nullable=False),
        sa.Column("participant_id", sa.Integer(), nullable=True),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("is_completed", sa.Boolean(), server_default="0", nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("due_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_action_items_due_at", "action_items", ["due_at"], unique=False)
    op.create_index("ix_action_items_meeting_id", "action_items", ["meeting_id"], unique=False)
    op.create_index("ix_action_items_meeting_id_is_completed", "action_items", ["meeting_id", "is_completed"], unique=False)
    op.create_index("ix_action_items_participant_id", "action_items", ["participant_id"], unique=False)

    op.create_table(
        "transcript_segments",
        sa.Column("meeting_id", sa.Integer(), nullable=False),
        sa.Column("participant_id", sa.Integer(), nullable=True),
        sa.Column("sequence_number", sa.Integer(), nullable=False),
        sa.Column("start_time_ms", sa.Integer(), nullable=False),
        sa.Column("end_time_ms", sa.Integer(), nullable=False),
        sa.Column("text", sa.Text(), nullable=False),
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("(CURRENT_TIMESTAMP)"), nullable=False),
        sa.CheckConstraint("end_time_ms >= start_time_ms", name="ck_transcript_segments_end_after_start"),
        sa.CheckConstraint("sequence_number >= 1", name="ck_transcript_segments_sequence_positive"),
        sa.CheckConstraint("start_time_ms >= 0", name="ck_transcript_segments_start_nonnegative"),
        sa.ForeignKeyConstraint(["meeting_id"], ["meetings.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["participant_id"], ["participants.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("meeting_id", "sequence_number", name="uq_transcript_segments_meeting_sequence"),
    )
    op.create_index("ix_transcript_segments_meeting_id", "transcript_segments", ["meeting_id"], unique=False)
    op.create_index("ix_transcript_segments_meeting_id_sequence_number", "transcript_segments", ["meeting_id", "sequence_number"], unique=False)
    op.create_index("ix_transcript_segments_meeting_id_start_time_ms", "transcript_segments", ["meeting_id", "start_time_ms"], unique=False)
    op.create_index("ix_transcript_segments_participant_id", "transcript_segments", ["participant_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_transcript_segments_participant_id", table_name="transcript_segments")
    op.drop_index("ix_transcript_segments_meeting_id_start_time_ms", table_name="transcript_segments")
    op.drop_index("ix_transcript_segments_meeting_id_sequence_number", table_name="transcript_segments")
    op.drop_index("ix_transcript_segments_meeting_id", table_name="transcript_segments")
    op.drop_table("transcript_segments")

    op.drop_index("ix_action_items_participant_id", table_name="action_items")
    op.drop_index("ix_action_items_meeting_id_is_completed", table_name="action_items")
    op.drop_index("ix_action_items_meeting_id", table_name="action_items")
    op.drop_index("ix_action_items_due_at", table_name="action_items")
    op.drop_table("action_items")

    op.drop_index("ix_summaries_meeting_id", table_name="summaries")
    op.drop_table("summaries")

    op.drop_index("ix_participants_meeting_id_display_name", table_name="participants")
    op.drop_index("ix_participants_meeting_id", table_name="participants")
    op.drop_table("participants")

    op.drop_index("ix_chapters_meeting_id_start_time_ms", table_name="chapters")
    op.drop_index("ix_chapters_meeting_id_sequence_number", table_name="chapters")
    op.drop_index("ix_chapters_meeting_id", table_name="chapters")
    op.drop_table("chapters")

    op.drop_index("ix_meetings_title", table_name="meetings")
    op.drop_index("ix_meetings_status", table_name="meetings")
    op.drop_index("ix_meetings_recorded_at", table_name="meetings")
    op.drop_index("ix_meetings_created_at", table_name="meetings")
    op.drop_table("meetings")
