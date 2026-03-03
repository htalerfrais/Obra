"""initial modular convergence schema

Revision ID: 0001_modular_convergence
Revises:
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa
from pgvector.sqlalchemy import Vector

# revision identifiers, used by Alembic.
revision = "0001_modular_convergence"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("google_user_id", sa.String(), nullable=False),
        sa.Column("token", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_users_google_user_id", "users", ["google_user_id"], unique=True)

    op.create_table(
        "sessions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_identifier", sa.String(), nullable=False),
        sa.Column("start_time", sa.DateTime(), nullable=False),
        sa.Column("end_time", sa.DateTime(), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_sessions_user_id", "sessions", ["user_id"], unique=False)
    op.create_index("ix_sessions_session_identifier", "sessions", ["session_identifier"], unique=True)

    op.create_table(
        "clusters",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_clusters_session_id", "clusters", ["session_id"], unique=False)

    op.create_table(
        "history_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("cluster_id", sa.Integer(), sa.ForeignKey("clusters.id", ondelete="CASCADE"), nullable=False),
        sa.Column("url", sa.String(), nullable=False),
        sa.Column("title", sa.String(), nullable=True),
        sa.Column("domain", sa.String(), nullable=True),
        sa.Column("visit_time", sa.DateTime(), nullable=False),
        sa.Column("raw_semantics", sa.JSON(), nullable=True),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_history_items_cluster_id", "history_items", ["cluster_id"], unique=False)

    op.create_table(
        "topics",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("embedding", Vector(768), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_topics_user_id", "topics", ["user_id"], unique=False)
    op.create_index("ix_topics_name", "topics", ["name"], unique=False)

    op.create_table(
        "topic_observations",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("session_id", sa.Integer(), sa.ForeignKey("sessions.id", ondelete="CASCADE"), nullable=False),
        sa.Column("observed_at", sa.DateTime(), nullable=False),
        sa.Column("importance_score", sa.Float(), server_default=sa.text("0.5"), nullable=False),
        sa.Column("source", sa.String(), server_default=sa.text("'clustering'"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_topic_observations_topic_id", "topic_observations", ["topic_id"], unique=False)
    op.create_index("ix_topic_observations_session_id", "topic_observations", ["session_id"], unique=False)

    op.create_table(
        "topic_recall_state",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("strength", sa.Float(), server_default=sa.text("0.5"), nullable=False),
        sa.Column("forgetting_score", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("interval_days", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("repetitions", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("next_review_at", sa.DateTime(), nullable=True),
        sa.Column("last_reviewed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_topic_recall_state_topic_id", "topic_recall_state", ["topic_id"], unique=True)
    op.create_index("ix_topic_recall_state_next_review_at", "topic_recall_state", ["next_review_at"], unique=False)

    op.create_table(
        "recall_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id", ondelete="CASCADE"), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("event_time", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_recall_events_topic_id", "recall_events", ["topic_id"], unique=False)

    op.create_table(
        "quiz_sets",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("topic_id", sa.Integer(), sa.ForeignKey("topics.id", ondelete="SET NULL"), nullable=True),
        sa.Column("title", sa.String(), nullable=False),
        sa.Column("status", sa.String(), server_default=sa.text("'ready'"), nullable=False),
        sa.Column("metadata_json", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_quiz_sets_user_id", "quiz_sets", ["user_id"], unique=False)
    op.create_index("ix_quiz_sets_topic_id", "quiz_sets", ["topic_id"], unique=False)

    op.create_table(
        "quiz_items",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("quiz_set_id", sa.Integer(), sa.ForeignKey("quiz_sets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("question", sa.Text(), nullable=False),
        sa.Column("answer", sa.Text(), nullable=False),
        sa.Column("distractors", sa.JSON(), nullable=True),
        sa.Column("difficulty", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_quiz_items_quiz_set_id", "quiz_items", ["quiz_set_id"], unique=False)

    op.create_table(
        "quiz_attempts",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("quiz_set_id", sa.Integer(), sa.ForeignKey("quiz_sets.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("score", sa.Float(), server_default=sa.text("0.0"), nullable=False),
        sa.Column("total_items", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("submitted_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_quiz_attempts_quiz_set_id", "quiz_attempts", ["quiz_set_id"], unique=False)
    op.create_index("ix_quiz_attempts_user_id", "quiz_attempts", ["user_id"], unique=False)

    op.create_table(
        "quiz_item_results",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("quiz_attempt_id", sa.Integer(), sa.ForeignKey("quiz_attempts.id", ondelete="CASCADE"), nullable=False),
        sa.Column("quiz_item_id", sa.Integer(), sa.ForeignKey("quiz_items.id", ondelete="CASCADE"), nullable=False),
        sa.Column("user_answer", sa.Text(), nullable=True),
        sa.Column("is_correct", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_quiz_item_results_quiz_attempt_id", "quiz_item_results", ["quiz_attempt_id"], unique=False)
    op.create_index("ix_quiz_item_results_quiz_item_id", "quiz_item_results", ["quiz_item_id"], unique=False)

    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("aggregate_type", sa.String(), nullable=False),
        sa.Column("aggregate_id", sa.String(), nullable=False),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("event_version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column("idempotency_key", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(), server_default=sa.text("'pending'"), nullable=False),
        sa.Column("retries", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("published_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_outbox_events_aggregate_type", "outbox_events", ["aggregate_type"], unique=False)
    op.create_index("ix_outbox_events_aggregate_id", "outbox_events", ["aggregate_id"], unique=False)
    op.create_index("ix_outbox_events_event_type", "outbox_events", ["event_type"], unique=False)
    op.create_index("ix_outbox_events_status", "outbox_events", ["status"], unique=False)
    op.create_index("ix_outbox_events_created_at", "outbox_events", ["created_at"], unique=False)
    op.create_index("ix_outbox_events_idempotency_key", "outbox_events", ["idempotency_key"], unique=True)

    # pgvector HNSW indexes aligned with previous schema performance profile
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_clusters_embedding ON clusters USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_history_items_embedding ON history_items USING hnsw (embedding vector_cosine_ops) WITH (m = 16, ef_construction = 64)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_history_items_embedding")
    op.execute("DROP INDEX IF EXISTS idx_clusters_embedding")

    op.drop_index("ix_outbox_events_idempotency_key", table_name="outbox_events")
    op.drop_index("ix_outbox_events_created_at", table_name="outbox_events")
    op.drop_index("ix_outbox_events_status", table_name="outbox_events")
    op.drop_index("ix_outbox_events_event_type", table_name="outbox_events")
    op.drop_index("ix_outbox_events_aggregate_id", table_name="outbox_events")
    op.drop_index("ix_outbox_events_aggregate_type", table_name="outbox_events")
    op.drop_table("outbox_events")

    op.drop_index("ix_quiz_item_results_quiz_item_id", table_name="quiz_item_results")
    op.drop_index("ix_quiz_item_results_quiz_attempt_id", table_name="quiz_item_results")
    op.drop_table("quiz_item_results")

    op.drop_index("ix_quiz_attempts_user_id", table_name="quiz_attempts")
    op.drop_index("ix_quiz_attempts_quiz_set_id", table_name="quiz_attempts")
    op.drop_table("quiz_attempts")

    op.drop_index("ix_quiz_items_quiz_set_id", table_name="quiz_items")
    op.drop_table("quiz_items")

    op.drop_index("ix_quiz_sets_topic_id", table_name="quiz_sets")
    op.drop_index("ix_quiz_sets_user_id", table_name="quiz_sets")
    op.drop_table("quiz_sets")

    op.drop_index("ix_recall_events_topic_id", table_name="recall_events")
    op.drop_table("recall_events")

    op.drop_index("ix_topic_recall_state_next_review_at", table_name="topic_recall_state")
    op.drop_index("ix_topic_recall_state_topic_id", table_name="topic_recall_state")
    op.drop_table("topic_recall_state")

    op.drop_index("ix_topic_observations_session_id", table_name="topic_observations")
    op.drop_index("ix_topic_observations_topic_id", table_name="topic_observations")
    op.drop_table("topic_observations")

    op.drop_index("ix_topics_name", table_name="topics")
    op.drop_index("ix_topics_user_id", table_name="topics")
    op.drop_table("topics")

    op.drop_index("ix_history_items_cluster_id", table_name="history_items")
    op.drop_table("history_items")

    op.drop_index("ix_clusters_session_id", table_name="clusters")
    op.drop_table("clusters")

    op.drop_index("ix_sessions_session_identifier", table_name="sessions")
    op.drop_index("ix_sessions_user_id", table_name="sessions")
    op.drop_table("sessions")

    op.drop_index("ix_users_google_user_id", table_name="users")
    op.drop_table("users")
