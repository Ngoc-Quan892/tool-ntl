"""Initial migration with all tables

Revision ID: 001_initial
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '001_initial'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Create game_results table
    op.create_table(
        'game_results',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('result', sa.String(length=1), nullable=False),
        sa.Column('prediction', sa.JSON(), nullable=True),
        sa.Column('shoe_number', sa.Integer(), nullable=True, server_default='1'),
        sa.Column('hand_number', sa.Integer(), nullable=True),
        sa.Column('timestamp', sa.DateTime(), nullable=False),
        sa.Column('true_count', sa.Float(), nullable=True),
        sa.Column('edge', sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_game_results_id', 'game_results', ['id'], unique=False)
    op.create_index('ix_game_results_result', 'game_results', ['result'], unique=False)
    op.create_index('ix_game_results_shoe_number', 'game_results', ['shoe_number'], unique=False)
    op.create_index('ix_game_results_timestamp', 'game_results', ['timestamp'], unique=False)
    op.create_index('idx_game_results_shoe_hand', 'game_results', ['shoe_number', 'hand_number'], unique=False)
    op.create_index('idx_game_results_result_timestamp', 'game_results', ['result', 'timestamp'], unique=False)
    op.create_index('idx_game_results_shoe_timestamp', 'game_results', ['shoe_number', 'timestamp'], unique=False)

    # Create simulation_runs table
    op.create_table(
        'simulation_runs',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('task_id', sa.String(length=50), nullable=False),
        sa.Column('total_shoes', sa.Integer(), nullable=False),
        sa.Column('completed_shoes', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('results', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('started_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('task_id')
    )
    op.create_index('ix_simulation_runs_id', 'simulation_runs', ['id'], unique=False)
    op.create_index('ix_simulation_runs_task_id', 'simulation_runs', ['task_id'], unique=True)
    op.create_index('ix_simulation_runs_status', 'simulation_runs', ['status'], unique=False)
    op.create_index('idx_simulation_runs_task_id', 'simulation_runs', ['task_id'], unique=False)


def downgrade() -> None:
    # Drop indexes first
    op.drop_index('idx_simulation_runs_task_id', table_name='simulation_runs')
    op.drop_index('ix_simulation_runs_status', table_name='simulation_runs')
    op.drop_index('ix_simulation_runs_task_id', table_name='simulation_runs')
    op.drop_index('ix_simulation_runs_id', table_name='simulation_runs')
    
    op.drop_index('idx_game_results_shoe_hand', table_name='game_results')
    op.drop_index('ix_game_results_timestamp', table_name='game_results')
    op.drop_index('ix_game_results_shoe_number', table_name='game_results')
    op.drop_index('ix_game_results_result', table_name='game_results')
    op.drop_index('ix_game_results_id', table_name='game_results')
    
    # Drop tables
    op.drop_table('simulation_runs')
    op.drop_table('game_results')

