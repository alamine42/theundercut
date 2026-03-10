"""Add circuit characteristics table

Creates table for storing track/circuit characteristics:
- Performance: full throttle %, average speed, track length
- Tire: degradation, abrasion levels
- Corners: slow/medium/fast counts
- Aero: downforce requirements
- Racing: overtaking difficulty, DRS zones, circuit type

Supports layout versioning via effective_year for circuits that change.

Revision ID: e8f4c3d56a23
Revises: d7a3b9c45e12
Create Date: 2026-03-10

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e8f4c3d56a23'
down_revision: Union[str, None] = 'd7a3b9c45e12'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create circuit_characteristics table."""

    op.create_table(
        'circuit_characteristics',
        sa.Column('id', sa.Integer(), primary_key=True),
        sa.Column('circuit_id', sa.Integer(), nullable=False),
        sa.Column('effective_year', sa.Integer(), nullable=False, server_default='2024'),

        # Performance characteristics
        sa.Column('full_throttle_pct', sa.Float(), nullable=True),
        sa.Column('full_throttle_score', sa.Integer(), nullable=True),
        sa.Column('average_speed_kph', sa.Float(), nullable=True),
        sa.Column('average_speed_score', sa.Integer(), nullable=True),
        sa.Column('track_length_km', sa.Float(), nullable=True),

        # Tire characteristics
        sa.Column('tire_degradation_score', sa.Integer(), nullable=True),
        sa.Column('tire_degradation_label', sa.String(length=20), nullable=True),
        sa.Column('track_abrasion_score', sa.Integer(), nullable=True),
        sa.Column('track_abrasion_label', sa.String(length=20), nullable=True),

        # Corner profile
        sa.Column('corners_slow', sa.Integer(), nullable=True),
        sa.Column('corners_medium', sa.Integer(), nullable=True),
        sa.Column('corners_fast', sa.Integer(), nullable=True),

        # Aerodynamic requirements
        sa.Column('downforce_score', sa.Integer(), nullable=True),
        sa.Column('downforce_label', sa.String(length=20), nullable=True),

        # Racing characteristics
        sa.Column('overtaking_difficulty_score', sa.Integer(), nullable=True),
        sa.Column('overtaking_difficulty_label', sa.String(length=20), nullable=True),
        sa.Column('drs_zones', sa.Integer(), nullable=True),
        sa.Column('circuit_type', sa.String(length=20), nullable=True),

        # Metadata
        sa.Column('data_completeness', sa.String(length=20), server_default='unknown'),
        sa.Column('last_updated', sa.DateTime(timezone=True), nullable=True),

        # Constraints
        sa.ForeignKeyConstraint(['circuit_id'], ['core.circuits.id']),
        sa.UniqueConstraint('circuit_id', 'effective_year', name='uq_circuit_characteristics'),
        sa.CheckConstraint('full_throttle_score >= 1 AND full_throttle_score <= 10', name='ck_full_throttle_score'),
        sa.CheckConstraint('average_speed_score >= 1 AND average_speed_score <= 10', name='ck_average_speed_score'),
        sa.CheckConstraint('tire_degradation_score >= 1 AND tire_degradation_score <= 10', name='ck_tire_degradation_score'),
        sa.CheckConstraint('track_abrasion_score >= 1 AND track_abrasion_score <= 10', name='ck_track_abrasion_score'),
        sa.CheckConstraint('downforce_score >= 1 AND downforce_score <= 10', name='ck_downforce_score'),
        sa.CheckConstraint('overtaking_difficulty_score >= 1 AND overtaking_difficulty_score <= 10', name='ck_overtaking_score'),
        sa.CheckConstraint(
            "circuit_type IN ('Street', 'Permanent', 'Hybrid')",
            name='ck_circuit_type'
        ),
        sa.CheckConstraint(
            "data_completeness IN ('complete', 'partial', 'unknown')",
            name='ck_data_completeness'
        ),
        schema='core',
    )

    # Index for efficient lookups
    op.create_index(
        'ix_circuit_chars_circuit_year',
        'circuit_characteristics',
        ['circuit_id', 'effective_year'],
        schema='core'
    )


def downgrade() -> None:
    """Drop circuit_characteristics table."""
    op.drop_index('ix_circuit_chars_circuit_year', table_name='circuit_characteristics', schema='core')
    op.drop_table('circuit_characteristics', schema='core')
