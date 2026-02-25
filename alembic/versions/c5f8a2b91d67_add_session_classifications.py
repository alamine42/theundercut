"""Add session_classifications table for Race Weekend Widget

Creates a table to store condensed session results (FP1-3, Qualifying, Sprint, Race)
as a single source of truth for the Race Weekend Widget, avoiding dual data sources.

Revision ID: c5f8a2b91d67
Revises: b4e7f9a12c58
Create Date: 2026-02-24

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c5f8a2b91d67'
down_revision: Union[str, None] = 'b4e7f9a12c58'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create session_classifications table."""
    op.create_table(
        'session_classifications',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('season', sa.Integer(), nullable=False),
        sa.Column('round', sa.Integer(), nullable=False),
        sa.Column('session_type', sa.String(length=20), nullable=False),
        sa.Column('driver_code', sa.String(length=3), nullable=False),
        sa.Column('driver_name', sa.String(length=100), nullable=True),
        sa.Column('team', sa.String(length=50), nullable=True),
        sa.Column('position', sa.Integer(), nullable=True),
        sa.Column('time_ms', sa.Float(), nullable=True),
        sa.Column('gap_ms', sa.Float(), nullable=True),
        sa.Column('laps', sa.Integer(), nullable=True),
        sa.Column('points', sa.Integer(), nullable=True),
        # Qualifying-specific fields
        sa.Column('q1_time_ms', sa.Float(), nullable=True),
        sa.Column('q2_time_ms', sa.Float(), nullable=True),
        sa.Column('q3_time_ms', sa.Float(), nullable=True),
        sa.Column('eliminated_in', sa.String(length=5), nullable=True),
        # Metadata
        sa.Column('ingested_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('amended', sa.Boolean(), nullable=True, default=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('season', 'round', 'session_type', 'driver_code', name='uq_session_classification'),
    )
    op.create_index('ix_session_classification_lookup', 'session_classifications', ['season', 'round', 'session_type'])


def downgrade() -> None:
    """Drop session_classifications table."""
    op.drop_index('ix_session_classification_lookup', table_name='session_classifications')
    op.drop_table('session_classifications')
