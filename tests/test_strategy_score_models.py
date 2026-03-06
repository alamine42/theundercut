"""Unit tests for Strategy Score models."""
import pytest
from datetime import datetime, timezone

from theundercut.models import (
    StrategyScore,
    StrategyDecision,
    RaceControlEvent,
    RaceWeather,
    LapPosition,
)


class TestStrategyScoreModel:
    """Test StrategyScore model structure."""

    def test_strategy_score_has_required_fields(self):
        """Verify StrategyScore model has all required fields."""
        score = StrategyScore(
            entry_id=1,
            total_score=75.5,
            pit_timing_score=80.0,
            tire_selection_score=70.0,
            safety_car_score=75.0,
            weather_score=50.0,
            calibration_profile="baseline",
            calibration_version="v1.0",
            computed_at=datetime.now(timezone.utc),
        )
        assert score.entry_id == 1
        assert score.total_score == 75.5
        assert score.pit_timing_score == 80.0
        assert score.tire_selection_score == 70.0
        assert score.safety_car_score == 75.0
        assert score.weather_score == 50.0
        assert score.calibration_profile == "baseline"
        assert score.calibration_version == "v1.0"

    def test_strategy_score_table_name(self):
        """Verify table name and schema."""
        assert StrategyScore.__tablename__ == "strategy_scores"
        assert StrategyScore.__table_args__["schema"] == "core"


class TestStrategyDecisionModel:
    """Test StrategyDecision model structure."""

    def test_strategy_decision_has_required_fields(self):
        """Verify StrategyDecision model has all required fields."""
        decision = StrategyDecision(
            strategy_score_id=1,
            lap_number=18,
            decision_type="pit_stop",
            factor="pit_timing",
            impact_score=12.5,
            position_delta=2,
            time_delta_ms=-3500,
            explanation="Undercut on Norris successful",
            comparison_context="Pitted 3 laps before peer average",
        )
        assert decision.lap_number == 18
        assert decision.decision_type == "pit_stop"
        assert decision.factor == "pit_timing"
        assert decision.impact_score == 12.5
        assert decision.position_delta == 2
        assert decision.explanation == "Undercut on Norris successful"


class TestRaceControlEventModel:
    """Test RaceControlEvent model structure."""

    def test_race_control_event_safety_car(self):
        """Verify RaceControlEvent for safety car period."""
        event = RaceControlEvent(
            race_id=1,
            event_type="safety_car",
            start_lap=15,
            end_lap=20,
            cause="Debris on track",
        )
        assert event.event_type == "safety_car"
        assert event.start_lap == 15
        assert event.end_lap == 20
        assert event.cause == "Debris on track"

    def test_race_control_event_vsc(self):
        """Verify RaceControlEvent for VSC period."""
        event = RaceControlEvent(
            race_id=1,
            event_type="vsc",
            start_lap=30,
            end_lap=32,
        )
        assert event.event_type == "vsc"

    def test_race_control_event_table_schema(self):
        """Verify table is in core schema."""
        assert RaceControlEvent.__table_args__[2]["schema"] == "core"


class TestRaceWeatherModel:
    """Test RaceWeather model structure."""

    def test_race_weather_dry_conditions(self):
        """Verify RaceWeather for dry conditions."""
        weather = RaceWeather(
            race_id=1,
            lap_number=1,
            track_status="dry",
            air_temp_c=28.5,
            track_temp_c=45.2,
            humidity_pct=45.0,
            rain_intensity="none",
        )
        assert weather.track_status == "dry"
        assert weather.air_temp_c == 28.5
        assert weather.rain_intensity == "none"

    def test_race_weather_wet_conditions(self):
        """Verify RaceWeather for wet conditions."""
        weather = RaceWeather(
            race_id=1,
            lap_number=25,
            track_status="wet",
            air_temp_c=18.0,
            track_temp_c=22.0,
            humidity_pct=95.0,
            rain_intensity="heavy",
        )
        assert weather.track_status == "wet"
        assert weather.rain_intensity == "heavy"


class TestLapPositionModel:
    """Test LapPosition model structure."""

    def test_lap_position_has_required_fields(self):
        """Verify LapPosition model has all required fields."""
        position = LapPosition(
            race_id=1,
            entry_id=5,
            lap_number=20,
            position=3,
            gap_to_leader_ms=15000,
            gap_to_ahead_ms=2500,
        )
        assert position.lap_number == 20
        assert position.position == 3
        assert position.gap_to_leader_ms == 15000
        assert position.gap_to_ahead_ms == 2500

    def test_lap_position_table_schema(self):
        """Verify table is in core schema."""
        assert LapPosition.__table_args__[2]["schema"] == "core"
