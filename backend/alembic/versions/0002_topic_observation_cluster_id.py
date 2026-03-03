"""add cluster_id to topic_observations

Revision ID: 0002_obs_cluster_id
Revises: 0001_modular_convergence
Create Date: 2026-02-27
"""

from alembic import op
import sqlalchemy as sa

revision = "0002_obs_cluster_id"
down_revision = "0001_modular_convergence"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "topic_observations",
        sa.Column("cluster_id", sa.Integer(), sa.ForeignKey("clusters.id", ondelete="SET NULL"), nullable=True),
    )
    op.create_index("ix_topic_observations_cluster_id", "topic_observations", ["cluster_id"])


def downgrade() -> None:
    op.drop_index("ix_topic_observations_cluster_id", table_name="topic_observations")
    op.drop_column("topic_observations", "cluster_id")
