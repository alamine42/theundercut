from unittest.mock import MagicMock

import pandas as pd
import pytest

from theundercut.services import ingestion
from theundercut.models import DriverMetrics, Entry, StrategyEvent, PenaltyEvent, OvertakeEvent


@pytest.fixture(autouse=True)
def patch_provider(monkeypatch):
    class DummyProvider:
        def load_laps(self, session_type="Race"):
            return pd.DataFrame(
                {
                    "Driver": ["VER", "VER", "HAM", "HAM"],
                    "LapNumber": [1, 2, 1, 2],
                    "LapTime": pd.to_timedelta([90, 91, 92, 93], unit="s"),
                    "Compound": ["MED", "MED", "MED", "HARD"],
                    "Stint": [1, 1, 1, 2],
                    "PitInTime": [pd.NA, pd.NA, pd.NA, "01:32:00"],
                }
            )

    weekend = {
        "season": 2024,
        "round": 1,
        "race_name": "Test GP",
        "circuit": "Test Circuit",
        "slug": "test_gp",
        "drivers": [
            {
                "driver": "VER",
                "team": "Red Bull",
                "driver_number": 1,
                "car_pace": {"base_delta": -0.2},
                "form": {"consistency": 0.7, "error_rate": 0.05, "start_precision": 0.6},
                "lap_deltas": [0.1, 0.05],
                "strategy": {"optimal_pit_laps": [20], "actual_pit_laps": [22], "degradation_penalty": 0.02},
                "penalties": [{"type": "warning", "time_loss": 0.5}],
                "overtakes": [
                    {
                        "success": True,
                        "exposure_time": 2.0,
                        "context": {
                            "delta_cpi": -0.1,
                            "tire_delta": 1,
                            "tire_compound_diff": 0,
                            "ers_delta": 0.0,
                            "track_difficulty": 0.5,
                            "race_phase_pressure": 0.5,
                        },
                    }
                ],
                "grid_position": 2,
                "finish_position": 1,
                "classification_status": "Finished",
            },
            {
                "driver": "HAM",
                "team": "Mercedes",
                "driver_number": 44,
                "car_pace": {"base_delta": 0.3},
                "form": {"consistency": 0.6, "error_rate": 0.1, "start_precision": 0.5},
                "lap_deltas": [0.2, 0.15],
                "strategy": {"optimal_pit_laps": [22], "actual_pit_laps": [24], "degradation_penalty": 0.04},
                "penalties": [],
                "overtakes": [],
                "grid_position": 1,
                "finish_position": 2,
                "classification_status": "Finished",
            },
        ],
    }

    monkeypatch.setattr(ingestion, "get_provider", lambda season, rnd: DummyProvider())
    monkeypatch.setattr(ingestion, "_try_fetch_drivegrade_weekend", lambda season, rnd: (weekend, "test"))
    return weekend


def test_ingestion_populates_driver_metrics(db_session_factory, monkeypatch, patch_provider):
    # rebind SessionLocal to the in-memory session factory used by tests
    monkeypatch.setattr(ingestion, "SessionLocal", db_session_factory)

    with db_session_factory() as session:
        ingestion.ingest_session(2024, 1)

    session = db_session_factory()
    metrics = session.query(DriverMetrics).all()
    assert len(metrics) == 2
    totals = {m.entry_id: m.total_grade for m in metrics}
    assert all(value is not None for value in totals.values())

    entries = session.query(Entry).all()
    assert {e.grid_position for e in entries} == {1, 2}
    assert {e.finish_position for e in entries} == {1, 2}
    assert session.query(StrategyEvent).count() == 2
    assert session.query(PenaltyEvent).count() == 1
    assert session.query(OvertakeEvent).count() == 1


def test_ingestion_invalidates_cache(db_session_factory, monkeypatch, patch_provider):
    monkeypatch.setattr(ingestion, "SessionLocal", db_session_factory)
    called = {}

    def fake_invalidate(season, rnd):
        called["args"] = (season, rnd)

    monkeypatch.setattr("theundercut.services.ingestion.invalidate_analytics_cache", fake_invalidate)

    ingestion.ingest_session(2024, 1)
    assert called["args"] == (2024, 1)
