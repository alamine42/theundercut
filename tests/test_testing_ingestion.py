"""Tests for pre-season testing ingestion service."""

import datetime
import pytest
import pandas as pd
from unittest.mock import patch, MagicMock

from theundercut.models import TestingEvent, TestingSession, TestingLap, TestingStint


class TestTestingIngestionHelpers:
    """Tests for helper functions in testing ingestion."""

    def test_format_lap_time(self):
        """Test lap time formatting helper."""
        from theundercut.api.v1.testing import _format_lap_time

        # Standard lap time
        assert _format_lap_time(90123.456) == "1:30.123"

        # None returns None
        assert _format_lap_time(None) is None


class TestStoreLaps:
    """Tests for _store_testing_laps function."""

    def test_stores_laps_from_dataframe(self, session_factory):
        """Test that laps are correctly stored from a DataFrame."""
        from theundercut.services.testing_ingestion import _store_testing_laps

        with session_factory() as db:
            # Create a testing event and session
            event = TestingEvent(
                season=2024,
                event_id="test_event",
                event_name="Test Event",
                circuit_id="bahrain",
                total_days=1,
                status="running",
            )
            db.add(event)
            db.flush()

            session = TestingSession(
                event_id=event.id,
                day=1,
                status="running",
            )
            db.add(session)
            db.flush()

            # Create mock lap data
            laps_df = pd.DataFrame({
                "Driver": ["VER", "VER", "HAM"],
                "Team": ["Red Bull", "Red Bull", "Mercedes"],
                "LapNumber": [1, 2, 1],
                "LapTime": [
                    pd.Timedelta(seconds=90.123),
                    pd.Timedelta(seconds=89.456),
                    pd.Timedelta(seconds=91.000),
                ],
                "Compound": ["SOFT", "SOFT", "MEDIUM"],
                "Stint": [1, 1, 1],
                "IsAccurate": [True, True, False],
                "Sector1Time": [pd.Timedelta(seconds=25.0), pd.Timedelta(seconds=24.8), pd.Timedelta(seconds=26.0)],
                "Sector2Time": [pd.Timedelta(seconds=35.0), pd.Timedelta(seconds=34.5), pd.Timedelta(seconds=35.5)],
                "Sector3Time": [pd.Timedelta(seconds=30.0), pd.Timedelta(seconds=30.1), pd.Timedelta(seconds=29.5)],
            })

            # Store the laps
            count = _store_testing_laps(db, session.id, laps_df)
            db.commit()

            assert count == 3

            # Verify laps were stored
            stored_laps = db.query(TestingLap).filter(
                TestingLap.session_id == session.id
            ).all()

            assert len(stored_laps) == 3

            # Check VER lap 1
            ver_lap1 = next(l for l in stored_laps if l.driver == "VER" and l.lap_number == 1)
            assert ver_lap1.team == "Red Bull"
            assert ver_lap1.lap_time_ms == pytest.approx(90123.0, abs=1.0)
            assert ver_lap1.compound == "SOFT"
            assert ver_lap1.is_valid == True

    def test_handles_empty_dataframe(self, session_factory):
        """Test that empty DataFrame returns 0 laps."""
        from theundercut.services.testing_ingestion import _store_testing_laps

        with session_factory() as db:
            empty_df = pd.DataFrame()
            count = _store_testing_laps(db, 999, empty_df)
            assert count == 0

    def test_handles_missing_driver(self, session_factory):
        """Test that rows with missing drivers are skipped."""
        from theundercut.services.testing_ingestion import _store_testing_laps

        with session_factory() as db:
            # Create event and session
            event = TestingEvent(
                season=2024,
                event_id="test_event",
                event_name="Test Event",
                circuit_id="bahrain",
                total_days=1,
                status="running",
            )
            db.add(event)
            db.flush()

            session = TestingSession(
                event_id=event.id,
                day=1,
                status="running",
            )
            db.add(session)
            db.flush()

            # DataFrame with missing driver
            laps_df = pd.DataFrame({
                "Driver": ["VER", None, ""],
                "Team": ["Red Bull", "Unknown", "Unknown"],
                "LapNumber": [1, 1, 1],
                "LapTime": [
                    pd.Timedelta(seconds=90.0),
                    pd.Timedelta(seconds=91.0),
                    pd.Timedelta(seconds=92.0),
                ],
                "Compound": ["SOFT", "SOFT", "SOFT"],
                "Stint": [1, 1, 1],
                "IsAccurate": [True, True, True],
            })

            count = _store_testing_laps(db, session.id, laps_df)
            db.commit()

            # Only VER lap should be stored
            stored = db.query(TestingLap).filter(TestingLap.session_id == session.id).all()
            assert len(stored) == 1
            assert stored[0].driver == "VER"


class TestComputeStints:
    """Tests for _compute_and_store_stints function."""

    def test_computes_stint_aggregates(self, session_factory):
        """Test that stints are correctly computed from lap data."""
        from theundercut.services.testing_ingestion import _compute_and_store_stints

        with session_factory() as db:
            # Create event and session
            event = TestingEvent(
                season=2024,
                event_id="test_event",
                event_name="Test Event",
                circuit_id="bahrain",
                total_days=1,
                status="running",
            )
            db.add(event)
            db.flush()

            session = TestingSession(
                event_id=event.id,
                day=1,
                status="running",
            )
            db.add(session)
            db.flush()

            # Create lap data with multiple stints
            laps_df = pd.DataFrame({
                "Driver": ["VER", "VER", "VER", "VER"],
                "Team": ["Red Bull", "Red Bull", "Red Bull", "Red Bull"],
                "LapNumber": [1, 2, 3, 4],
                "LapTime": [
                    pd.Timedelta(seconds=90.0),
                    pd.Timedelta(seconds=89.0),
                    pd.Timedelta(seconds=88.0),  # Stint 2 starts
                    pd.Timedelta(seconds=87.0),
                ],
                "Compound": ["SOFT", "SOFT", "MEDIUM", "MEDIUM"],
                "Stint": [1, 1, 2, 2],
            })

            count = _compute_and_store_stints(db, session.id, laps_df)
            db.commit()

            assert count == 2

            # Verify stints
            stints = db.query(TestingStint).filter(
                TestingStint.session_id == session.id
            ).order_by(TestingStint.stint_number).all()

            assert len(stints) == 2

            # Stint 1: SOFT, 2 laps
            assert stints[0].compound == "SOFT"
            assert stints[0].lap_count == 2
            assert stints[0].stint_number == 1

            # Stint 2: MEDIUM, 2 laps
            assert stints[1].compound == "MEDIUM"
            assert stints[1].lap_count == 2
            assert stints[1].stint_number == 2


class TestIngestTestingDay:
    """Tests for ingest_testing_day function."""

    def test_ingests_day_successfully(self, session_factory, monkeypatch):
        """Test successful ingestion of a testing day."""
        from theundercut.services.testing_ingestion import ingest_testing_day

        # Mock SessionLocal to use our test session
        monkeypatch.setattr(
            "theundercut.services.testing_ingestion.SessionLocal",
            session_factory
        )

        with session_factory() as db:
            # Create event
            event = TestingEvent(
                season=2024,
                event_id="test_event",
                event_name="Test Event",
                circuit_id="bahrain",
                total_days=3,
                status="running",
            )
            db.add(event)
            db.commit()

        # Mock FastF1 to return test data
        mock_laps = pd.DataFrame({
            "Driver": ["VER", "HAM"],
            "Team": ["Red Bull", "Mercedes"],
            "LapNumber": [1, 1],
            "LapTime": [
                pd.Timedelta(seconds=90.0),
                pd.Timedelta(seconds=91.0),
            ],
            "Compound": ["SOFT", "MEDIUM"],
            "Stint": [1, 1],
            "IsAccurate": [True, True],
            "Sector1Time": [None, None],
            "Sector2Time": [None, None],
            "Sector3Time": [None, None],
        })

        with patch(
            "theundercut.services.testing_ingestion._load_testing_laps_for_day",
            return_value=mock_laps
        ):
            result = ingest_testing_day(2024, "test_event", 1)

        assert result["status"] == "completed"
        assert result["laps_count"] == 2
        assert result["stints_count"] == 2

        # Verify data was stored
        with session_factory() as db:
            session = db.query(TestingSession).filter(
                TestingSession.day == 1
            ).first()
            assert session is not None
            assert session.status == "completed"

    def test_handles_no_data(self, session_factory, monkeypatch):
        """Test handling when no lap data is available."""
        from theundercut.services.testing_ingestion import ingest_testing_day

        monkeypatch.setattr(
            "theundercut.services.testing_ingestion.SessionLocal",
            session_factory
        )

        with session_factory() as db:
            event = TestingEvent(
                season=2024,
                event_id="test_event",
                event_name="Test Event",
                circuit_id="bahrain",
                total_days=3,
                status="running",
            )
            db.add(event)
            db.commit()

        with patch(
            "theundercut.services.testing_ingestion._load_testing_laps_for_day",
            return_value=pd.DataFrame()
        ):
            result = ingest_testing_day(2024, "test_event", 1)

        assert result["status"] == "no_data"
        assert result["laps_count"] == 0

    def test_handles_missing_event(self, session_factory, monkeypatch):
        """Test handling when event doesn't exist."""
        from theundercut.services.testing_ingestion import ingest_testing_day

        monkeypatch.setattr(
            "theundercut.services.testing_ingestion.SessionLocal",
            session_factory
        )

        result = ingest_testing_day(2024, "nonexistent_event", 1)

        assert result["status"] == "event_not_found"


class TestSyncTestingEvents:
    """Tests for sync_testing_events function."""

    def test_syncs_new_events(self, session_factory, monkeypatch):
        """Test syncing new testing events from schedule."""
        from theundercut.services.testing_ingestion import sync_testing_events

        monkeypatch.setattr(
            "theundercut.services.testing_ingestion.SessionLocal",
            session_factory
        )

        mock_schedule = [
            {
                "event_id": "pre_season_test",
                "event_name": "Pre-Season Test",
                "circuit_id": "bahrain",
                "total_days": 3,
                "start_date": datetime.date(2024, 2, 21),
                "end_date": datetime.date(2024, 2, 23),
            }
        ]

        with patch(
            "theundercut.services.testing_ingestion._get_testing_schedule",
            return_value=mock_schedule
        ):
            result = sync_testing_events(2024)

        assert len(result) == 1
        assert result[0]["event_id"] == "pre_season_test"
        assert result[0]["action"] == "created"

        # Verify event was created
        with session_factory() as db:
            event = db.query(TestingEvent).filter(
                TestingEvent.event_id == "pre_season_test"
            ).first()
            assert event is not None
            assert event.event_name == "Pre-Season Test"

    def test_updates_existing_events(self, session_factory, monkeypatch):
        """Test updating existing testing events."""
        from theundercut.services.testing_ingestion import sync_testing_events

        monkeypatch.setattr(
            "theundercut.services.testing_ingestion.SessionLocal",
            session_factory
        )

        # Create existing event
        with session_factory() as db:
            event = TestingEvent(
                season=2024,
                event_id="pre_season_test",
                event_name="Old Name",
                circuit_id="bahrain",
                total_days=3,
                status="scheduled",
            )
            db.add(event)
            db.commit()

        mock_schedule = [
            {
                "event_id": "pre_season_test",
                "event_name": "Pre-Season Test",
                "circuit_id": "bahrain",
                "total_days": 3,
                "start_date": datetime.date(2024, 2, 21),
                "end_date": datetime.date(2024, 2, 23),
            }
        ]

        with patch(
            "theundercut.services.testing_ingestion._get_testing_schedule",
            return_value=mock_schedule
        ):
            result = sync_testing_events(2024)

        assert len(result) == 1
        assert result[0]["action"] == "updated"

        # Verify dates were updated
        with session_factory() as db:
            event = db.query(TestingEvent).filter(
                TestingEvent.event_id == "pre_season_test"
            ).first()
            assert event.start_date == datetime.date(2024, 2, 21)
