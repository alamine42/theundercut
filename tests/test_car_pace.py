import pytest

from f1_drive_grade.car_pace import anchor_car_pace_to_team


def test_anchor_car_pace_to_team_averages_teammates() -> None:
    drivers = [
        {"driver": "A1", "team": "Team A", "car_pace": {"base_delta": -0.3, "track_adjustment": 0.0}},
        {"driver": "A2", "team": "Team A", "car_pace": {"base_delta": 0.1, "track_adjustment": 0.0}},
        {"driver": "B1", "team": "Team B", "car_pace": {"base_delta": 0.5, "track_adjustment": 0.0}},
    ]

    anchor_car_pace_to_team(drivers)

    assert drivers[0]["car_pace"]["base_delta"] == pytest.approx(-0.3)
    assert drivers[1]["car_pace"]["base_delta"] == pytest.approx(-0.3)
    assert drivers[2]["car_pace"]["base_delta"] == pytest.approx(0.3)


def test_anchor_car_pace_handles_single_team() -> None:
    drivers = [
        {"driver": "A1", "team": "Solo", "car_pace": {"base_delta": -0.5, "track_adjustment": 0.0}},
        {"driver": "A2", "team": "Solo", "car_pace": {"base_delta": -0.1, "track_adjustment": 0.0}},
    ]

    anchor_car_pace_to_team(drivers)

    assert drivers[0]["car_pace"]["base_delta"] == pytest.approx(0.0)
    assert drivers[1]["car_pace"]["base_delta"] == pytest.approx(0.0)
