"""Add enhanced strategy score tables

Creates tables for strategy scoring feature:
- strategy_scores: Component scores per driver per race
- strategy_decisions: Decision log for explainability
- race_control_events: SC/VSC/red flag periods
- race_weather: Per-lap weather conditions
- lap_positions: Per-lap position snapshots

Revision ID: d7a3b9c45e12
Revises: c5f8a2b91d67
Create Date: 2026-03-06

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'd7a3b9c45e12'
down_revision: Union[str, None] = 'c5f8a2b91d67'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create strategy score tables."""

    # Strategy scores - one per driver per race
    op.create_table(
        'strategy_scores',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('entry_id', sa.Integer(), nullable=False),
        # Component scores (0-100)
        sa.Column('total_score', sa.Float(), nullable=False),
        sa.Column('pit_timing_score', sa.Float(), nullable=False),
        sa.Column('tire_selection_score', sa.Float(), nullable=False),
        sa.Column('safety_car_score', sa.Float(), nullable=False),
        sa.Column('weather_score', sa.Float(), nullable=False),
        # Metadata for recomputation
        sa.Column('calibration_profile', sa.String(length=50), nullable=False),
        sa.Column('calibration_version', sa.String(length=20), nullable=False),
        sa.Column('computed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['entry_id'], ['core.entries.id']),
        sa.UniqueConstraint('entry_id', name='uq_strategy_score_entry'),
        schema='core',
    )

    # Strategy decisions - decision log for explainability
    op.create_table(
        'strategy_decisions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('strategy_score_id', sa.Integer(), nullable=False),
        # Decision context
        sa.Column('lap_number', sa.Integer(), nullable=False),
        sa.Column('decision_type', sa.String(length=50), nullable=False),
        sa.Column('factor', sa.String(length=20), nullable=False),
        # Impact assessment
        sa.Column('impact_score', sa.Float(), nullable=False),
        sa.Column('position_delta', sa.Integer(), nullable=True),
        sa.Column('time_delta_ms', sa.Integer(), nullable=True),
        # Explainability
        sa.Column('explanation', sa.String(), nullable=False),
        sa.Column('comparison_context', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(
            ['strategy_score_id'],
            ['core.strategy_scores.id'],
            ondelete='CASCADE'
        ),
        schema='core',
    )
    op.create_index(
        'ix_strategy_decision_score',
        'strategy_decisions',
        ['strategy_score_id'],
        schema='core'
    )

    # Race control events - SC/VSC/red flag periods
    op.create_table(
        'race_control_events',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('event_type', sa.String(length=20), nullable=False),
        sa.Column('start_lap', sa.Integer(), nullable=False),
        sa.Column('end_lap', sa.Integer(), nullable=True),
        sa.Column('start_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('end_time', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cause', sa.String(), nullable=True),
        sa.ForeignKeyConstraint(['race_id'], ['core.races.id']),
        sa.UniqueConstraint('race_id', 'event_type', 'start_lap', name='uq_race_control_event'),
        schema='core',
    )
    op.create_index(
        'ix_race_control_event_race',
        'race_control_events',
        ['race_id'],
        schema='core'
    )

    # Race weather - per-lap weather conditions
    op.create_table(
        'race_weather',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('lap_number', sa.Integer(), nullable=False),
        sa.Column('track_status', sa.String(length=20), nullable=False),
        sa.Column('air_temp_c', sa.Float(), nullable=True),
        sa.Column('track_temp_c', sa.Float(), nullable=True),
        sa.Column('humidity_pct', sa.Float(), nullable=True),
        sa.Column('rain_intensity', sa.String(length=20), nullable=True),
        sa.ForeignKeyConstraint(['race_id'], ['core.races.id']),
        sa.UniqueConstraint('race_id', 'lap_number', name='uq_race_weather'),
        schema='core',
    )
    op.create_index(
        'ix_race_weather_race',
        'race_weather',
        ['race_id'],
        schema='core'
    )

    # Lap positions - per-lap position snapshots
    op.create_table(
        'lap_positions',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('race_id', sa.Integer(), nullable=False),
        sa.Column('entry_id', sa.Integer(), nullable=False),
        sa.Column('lap_number', sa.Integer(), nullable=False),
        sa.Column('position', sa.Integer(), nullable=False),
        sa.Column('gap_to_leader_ms', sa.Integer(), nullable=True),
        sa.Column('gap_to_ahead_ms', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['race_id'], ['core.races.id']),
        sa.ForeignKeyConstraint(['entry_id'], ['core.entries.id']),
        sa.UniqueConstraint('race_id', 'entry_id', 'lap_number', name='uq_lap_position'),
        schema='core',
    )
    op.create_index(
        'ix_lap_position_race_lap',
        'lap_positions',
        ['race_id', 'lap_number'],
        schema='core'
    )


def downgrade() -> None:
    """Drop strategy score tables."""
    op.drop_index('ix_lap_position_race_lap', table_name='lap_positions', schema='core')
    op.drop_table('lap_positions', schema='core')

    op.drop_index('ix_race_weather_race', table_name='race_weather', schema='core')
    op.drop_table('race_weather', schema='core')

    op.drop_index('ix_race_control_event_race', table_name='race_control_events', schema='core')
    op.drop_table('race_control_events', schema='core')

    op.drop_index('ix_strategy_decision_score', table_name='strategy_decisions', schema='core')
    op.drop_table('strategy_decisions', schema='core')

    op.drop_table('strategy_scores', schema='core')
