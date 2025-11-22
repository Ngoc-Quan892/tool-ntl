"""Add performance indexes

Revision ID: add_indexes_v1
Revises: 002_optimize_indexes
Create Date: 2024-01-01 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "add_indexes_v1"
down_revision = "002_optimize_indexes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "idx_game_results_result_hand",
        "game_results",
        ["result", "hand_number"],
        unique=False,
    )
    op.create_index(
        "idx_game_results_timestamp_edge",
        "game_results",
        ["timestamp", "edge"],
        unique=False,
    )
    op.create_index(
        "idx_simulation_runs_status_started_at",
        "simulation_runs",
        ["status", sa.text("started_at DESC")],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_simulation_runs_status_started_at", table_name="simulation_runs")
    op.drop_index("idx_game_results_timestamp_edge", table_name="game_results")
    op.drop_index("idx_game_results_result_hand", table_name="game_results")

