"""Optimize database indexes for performance

Revision ID: 002_optimize_indexes
Revises: 001_initial_migration
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '002_optimize_indexes'
down_revision = '001_initial_migration'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add composite index for common query patterns
    # Query: Get results by shoe and result type
    op.create_index(
        'idx_game_results_shoe_result',
        'game_results',
        ['shoe_number', 'result'],
        unique=False
    )
    
    # Query: Get recent results ordered by timestamp
    op.create_index(
        'idx_game_results_timestamp_desc',
        'game_results',
        [sa.text('timestamp DESC')],
        unique=False
    )
    
    # Query: Get results by shoe and timestamp range
    op.create_index(
        'idx_game_results_shoe_timestamp',
        'game_results',
        ['shoe_number', 'timestamp'],
        unique=False
    )
    
    # Query: Filter by result and timestamp
    op.create_index(
        'idx_game_results_result_timestamp',
        'game_results',
        ['result', 'timestamp'],
        unique=False
    )
    
    # Query: Get results with true_count (for edge calculations)
    op.create_index(
        'idx_game_results_true_count',
        'game_results',
        ['true_count'],
        unique=False,
        postgresql_where=sa.text('true_count IS NOT NULL')
    )
    
    # Query: Get results with edge (for analysis)
    op.create_index(
        'idx_game_results_edge',
        'game_results',
        ['edge'],
        unique=False,
        postgresql_where=sa.text('edge IS NOT NULL')
    )


def downgrade() -> None:
    # Drop indexes in reverse order
    op.drop_index('idx_game_results_edge', table_name='game_results')
    op.drop_index('idx_game_results_true_count', table_name='game_results')
    op.drop_index('idx_game_results_result_timestamp', table_name='game_results')
    op.drop_index('idx_game_results_shoe_timestamp', table_name='game_results')
    op.drop_index('idx_game_results_timestamp_desc', table_name='game_results')
    op.drop_index('idx_game_results_shoe_result', table_name='game_results')

