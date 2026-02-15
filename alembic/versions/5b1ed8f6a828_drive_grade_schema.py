"""drive grade schema

Revision ID: 5b1ed8f6a828
Revises: 8587dcdb69dd
Create Date: 2026-02-11 19:27:04.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "5b1ed8f6a828"
down_revision: Union[str, None] = "8587dcdb69dd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _create_schemas():
    op.execute("CREATE SCHEMA IF NOT EXISTS core")
    op.execute("CREATE SCHEMA IF NOT EXISTS config")
    op.execute("CREATE SCHEMA IF NOT EXISTS validation")


def upgrade() -> None:
    """Upgrade schema."""
    _create_schemas()

    op.create_table(
        "seasons",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("year", sa.Integer(), nullable=False, unique=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        schema="core",
    )

    op.create_table(
        "circuits",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False),
        sa.Column("country", sa.String(), nullable=True),
        sa.Column("latitude", sa.Float(), nullable=True),
        sa.Column("longitude", sa.Float(), nullable=True),
        schema="core",
    )

    op.create_table(
        "teams",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("power_unit", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        schema="core",
    )

    op.create_table(
        "drivers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(length=3), nullable=False, unique=True),
        sa.Column("given_name", sa.String(), nullable=True),
        sa.Column("family_name", sa.String(), nullable=True),
        sa.Column("country", sa.String(), nullable=True),
        schema="core",
    )

    op.create_table(
        "races",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("season_id", sa.Integer(), nullable=False),
        sa.Column("circuit_id", sa.Integer(), nullable=True),
        sa.Column("round_number", sa.Integer(), nullable=False),
        sa.Column("slug", sa.String(), nullable=False, unique=True),
        sa.Column("session_type", sa.String(length=2), nullable=True),
        sa.Column("start_time", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["season_id"], ["core.seasons.id"]),
        sa.ForeignKeyConstraint(["circuit_id"], ["core.circuits.id"]),
        schema="core",
    )

    op.create_table(
        "entries",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("race_id", sa.Integer(), nullable=False),
        sa.Column("driver_id", sa.Integer(), nullable=False),
        sa.Column("team_id", sa.Integer(), nullable=False),
        sa.Column("car_number", sa.Integer(), nullable=True),
        sa.Column("grid_position", sa.Integer(), nullable=True),
        sa.Column("finish_position", sa.Integer(), nullable=True),
        sa.Column("status", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["race_id"], ["core.races.id"]),
        sa.ForeignKeyConstraint(["driver_id"], ["core.drivers.id"]),
        sa.ForeignKeyConstraint(["team_id"], ["core.teams.id"]),
        schema="core",
    )

    op.create_table(
        "driver_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entry_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("calibration_profile", sa.String(), nullable=True),
        sa.Column("data_source", sa.String(), nullable=True),
        sa.Column("consistency_raw", sa.Float(), nullable=True),
        sa.Column("consistency_score", sa.Float(), nullable=True),
        sa.Column("team_strategy_raw", sa.Float(), nullable=True),
        sa.Column("team_strategy_score", sa.Float(), nullable=True),
        sa.Column("racecraft_raw", sa.Float(), nullable=True),
        sa.Column("racecraft_score", sa.Float(), nullable=True),
        sa.Column("penalties_raw", sa.Float(), nullable=True),
        sa.Column("penalty_score", sa.Float(), nullable=True),
        sa.Column("total_grade", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["entry_id"], ["core.entries.id"]),
        schema="core",
    )

    op.create_table(
        "strategy_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("planned_lap", sa.Integer(), nullable=True),
        sa.Column("executed_lap", sa.Integer(), nullable=True),
        sa.Column("compound_in", sa.String(length=10), nullable=True),
        sa.Column("compound_out", sa.String(length=10), nullable=True),
        sa.Column("stop_time", sa.Float(), nullable=True),
        sa.Column("degradation_penalty", sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(["entry_id"], ["core.entries.id"]),
        schema="core",
    )

    op.create_table(
        "penalty_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("penalty_type", sa.String(), nullable=True),
        sa.Column("time_loss_seconds", sa.Float(), nullable=True),
        sa.Column("source", sa.String(), nullable=True),
        sa.Column("lap_number", sa.Integer(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["entry_id"], ["core.entries.id"]),
        schema="core",
    )

    op.create_table(
        "overtake_events",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("entry_id", sa.Integer(), nullable=False),
        sa.Column("opponent_entry_id", sa.Integer(), nullable=True),
        sa.Column("lap_number", sa.Integer(), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=True),
        sa.Column("penalized", sa.Boolean(), nullable=True),
        sa.Column("exposure_time", sa.Float(), nullable=True),
        sa.Column("delta_cpi", sa.Float(), nullable=True),
        sa.Column("tire_delta", sa.Float(), nullable=True),
        sa.Column("tire_compound_diff", sa.String(length=10), nullable=True),
        sa.Column("ers_delta", sa.Float(), nullable=True),
        sa.Column("track_difficulty", sa.Float(), nullable=True),
        sa.Column("race_phase_pressure", sa.Float(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=True),
        sa.Column("event_source", sa.String(), nullable=True),
        sa.ForeignKeyConstraint(["entry_id"], ["core.entries.id"]),
        sa.ForeignKeyConstraint(["opponent_entry_id"], ["core.entries.id"]),
        schema="core",
    )

    op.create_table(
        "calibration_profiles",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(), nullable=False, unique=True),
        sa.Column("version", sa.String(), nullable=True, default="v1"),
        sa.Column("active", sa.Boolean(), nullable=False, server_default=sa.text("FALSE")),
        sa.Column("body", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        schema="config",
    )

    op.create_table(
        "external_rankings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("driver_code", sa.String(length=3), nullable=False),
        sa.Column("rank", sa.Integer(), nullable=False),
        sa.Column("score", sa.Float(), nullable=True),
        sa.Column("source_url", sa.String(), nullable=True),
        sa.Column("captured_at", sa.DateTime(timezone=True), nullable=True),
        schema="validation",
    )

    op.create_table(
        "validation_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("season", sa.Integer(), nullable=False),
        sa.Column("round", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("metric_name", sa.String(), nullable=False),
        sa.Column("metric_value", sa.Float(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        schema="validation",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("validation_metrics", schema="validation")
    op.drop_table("external_rankings", schema="validation")
    op.drop_table("calibration_profiles", schema="config")
    op.drop_table("overtake_events", schema="core")
    op.drop_table("penalty_events", schema="core")
    op.drop_table("strategy_events", schema="core")
    op.drop_table("driver_metrics", schema="core")
    op.drop_table("entries", schema="core")
    op.drop_table("races", schema="core")
    op.drop_table("drivers", schema="core")
    op.drop_table("teams", schema="core")
    op.drop_table("circuits", schema="core")
    op.drop_table("seasons", schema="core")
    op.execute("DROP SCHEMA IF EXISTS validation CASCADE")
    op.execute("DROP SCHEMA IF EXISTS config CASCADE")
    op.execute("DROP SCHEMA IF EXISTS core CASCADE")
