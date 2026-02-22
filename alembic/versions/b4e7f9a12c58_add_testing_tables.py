"""Add pre-season testing tables

Creates tables for storing pre-season testing data:
- testing_events: Event metadata (season, circuit, dates)
- testing_sessions: Individual days within an event
- testing_laps: Lap-by-lap data with sectors
- testing_stints: Aggregated stint data

Revision ID: b4e7f9a12c58
Revises: a3f2c8e91b47
Create Date: 2026-02-22

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b4e7f9a12c58'
down_revision: Union[str, None] = 'a3f2c8e91b47'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create testing tables."""
    # testing_events - Event metadata
    op.create_table(
        'testing_events',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('season', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.String(length=50), nullable=False),
        sa.Column('event_name', sa.String(length=100), nullable=False),
        sa.Column('circuit_id', sa.String(length=50), nullable=False),
        sa.Column('total_days', sa.Integer(), nullable=True, default=3),
        sa.Column('start_date', sa.Date(), nullable=True),
        sa.Column('end_date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True, default='scheduled'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('season', 'event_id', name='uq_testing_event'),
    )
    op.create_index('ix_testing_events_season', 'testing_events', ['season'])
    op.create_index('ix_testing_event_lookup', 'testing_events', ['season', 'event_id'])

    # testing_sessions - Individual days
    op.create_table(
        'testing_sessions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('event_id', sa.Integer(), nullable=False),
        sa.Column('day', sa.Integer(), nullable=False),
        sa.Column('date', sa.Date(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=True, default='scheduled'),
        sa.ForeignKeyConstraint(['event_id'], ['testing_events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id', 'day', name='uq_testing_session'),
    )

    # testing_laps - Individual laps
    op.create_table(
        'testing_laps',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('driver', sa.String(length=3), nullable=False),
        sa.Column('team', sa.String(length=50), nullable=True),
        sa.Column('lap_number', sa.Integer(), nullable=False),
        sa.Column('lap_time_ms', sa.Float(), nullable=True),
        sa.Column('compound', sa.String(length=20), nullable=True),
        sa.Column('stint_number', sa.Integer(), nullable=True),
        sa.Column('sector_1_ms', sa.Float(), nullable=True),
        sa.Column('sector_2_ms', sa.Float(), nullable=True),
        sa.Column('sector_3_ms', sa.Float(), nullable=True),
        sa.Column('is_valid', sa.Boolean(), nullable=True, default=True),
        sa.ForeignKeyConstraint(['session_id'], ['testing_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'driver', 'lap_number', name='uq_testing_lap'),
    )
    op.create_index('ix_testing_lap_driver', 'testing_laps', ['session_id', 'driver'])

    # testing_stints - Aggregated stints
    op.create_table(
        'testing_stints',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('session_id', sa.Integer(), nullable=False),
        sa.Column('driver', sa.String(length=3), nullable=False),
        sa.Column('team', sa.String(length=50), nullable=True),
        sa.Column('stint_number', sa.Integer(), nullable=False),
        sa.Column('compound', sa.String(length=20), nullable=True),
        sa.Column('start_lap', sa.Integer(), nullable=True),
        sa.Column('end_lap', sa.Integer(), nullable=True),
        sa.Column('lap_count', sa.Integer(), nullable=True),
        sa.Column('avg_pace_ms', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['session_id'], ['testing_sessions.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('session_id', 'driver', 'stint_number', name='uq_testing_stint'),
    )


def downgrade() -> None:
    """Drop testing tables."""
    op.drop_table('testing_stints')
    op.drop_table('testing_laps')
    op.drop_table('testing_sessions')
    op.drop_table('testing_events')
