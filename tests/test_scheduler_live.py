"""Tests for live session detection in scheduler."""
import datetime as dt
from unittest.mock import patch, MagicMock

import pytest

from theundercut.models import CalendarEvent


class TestMarkSessionsLive:
    """Tests for mark_sessions_live() function."""

    def test_marks_started_session_as_live(self, db_session):
        """Session that has started should be marked as 'live'."""
        # Create a session that started 30 minutes ago
        now = dt.datetime.utcnow()
        session = CalendarEvent(
            season=2026,
            round=1,
            session_type="race",
            start_ts=now - dt.timedelta(minutes=30),
            end_ts=now + dt.timedelta(hours=2),
            status="scheduled",
        )
        db_session.add(session)
        db_session.commit()

        # Import and call the function with mocked SessionLocal
        with patch("theundercut.scheduler_jobs.SessionLocal") as mock_session_local, \
             patch("theundercut.scheduler_jobs.invalidate_race_weekend_cache") as mock_invalidate:
            mock_session_local.return_value.__enter__.return_value = db_session
            mock_session_local.return_value.__exit__ = MagicMock()

            from theundercut.scheduler_jobs import mark_sessions_live
            mark_sessions_live()

        # Verify session is now live
        db_session.refresh(session)
        assert session.status == "live"
        mock_invalidate.assert_called_once_with(2026, 1)

    def test_ignores_future_sessions(self, db_session):
        """Sessions that haven't started yet should remain 'scheduled'."""
        now = dt.datetime.utcnow()
        session = CalendarEvent(
            season=2026,
            round=1,
            session_type="fp1",
            start_ts=now + dt.timedelta(hours=2),
            end_ts=now + dt.timedelta(hours=3),
            status="scheduled",
        )
        db_session.add(session)
        db_session.commit()

        with patch("theundercut.scheduler_jobs.SessionLocal") as mock_session_local, \
             patch("theundercut.scheduler_jobs.invalidate_race_weekend_cache") as mock_invalidate:
            mock_session_local.return_value.__enter__.return_value = db_session
            mock_session_local.return_value.__exit__ = MagicMock()

            from theundercut.scheduler_jobs import mark_sessions_live
            mark_sessions_live()

        db_session.refresh(session)
        assert session.status == "scheduled"
        mock_invalidate.assert_not_called()

    def test_ignores_already_live_sessions(self, db_session):
        """Sessions already marked as 'live' should not be processed again."""
        now = dt.datetime.utcnow()
        session = CalendarEvent(
            season=2026,
            round=1,
            session_type="race",
            start_ts=now - dt.timedelta(minutes=30),
            end_ts=now + dt.timedelta(hours=2),
            status="live",  # Already live
        )
        db_session.add(session)
        db_session.commit()

        with patch("theundercut.scheduler_jobs.SessionLocal") as mock_session_local, \
             patch("theundercut.scheduler_jobs.invalidate_race_weekend_cache") as mock_invalidate:
            mock_session_local.return_value.__enter__.return_value = db_session
            mock_session_local.return_value.__exit__ = MagicMock()

            from theundercut.scheduler_jobs import mark_sessions_live
            mark_sessions_live()

        db_session.refresh(session)
        assert session.status == "live"
        # Should not invalidate cache for already-live session
        mock_invalidate.assert_not_called()

    def test_ignores_ingested_sessions(self, db_session):
        """Sessions already ingested should not be marked as 'live'."""
        now = dt.datetime.utcnow()
        session = CalendarEvent(
            season=2026,
            round=1,
            session_type="race",
            start_ts=now - dt.timedelta(hours=3),
            end_ts=now - dt.timedelta(hours=1),
            status="ingested",
        )
        db_session.add(session)
        db_session.commit()

        with patch("theundercut.scheduler_jobs.SessionLocal") as mock_session_local, \
             patch("theundercut.scheduler_jobs.invalidate_race_weekend_cache") as mock_invalidate:
            mock_session_local.return_value.__enter__.return_value = db_session
            mock_session_local.return_value.__exit__ = MagicMock()

            from theundercut.scheduler_jobs import mark_sessions_live
            mark_sessions_live()

        db_session.refresh(session)
        assert session.status == "ingested"
        mock_invalidate.assert_not_called()

    def test_marks_multiple_sessions_as_live(self, db_session):
        """Multiple sessions that have started should all be marked as 'live'."""
        now = dt.datetime.utcnow()
        # FP1 started 2 hours ago
        fp1 = CalendarEvent(
            season=2026,
            round=1,
            session_type="fp1",
            start_ts=now - dt.timedelta(hours=2),
            end_ts=now - dt.timedelta(hours=1),
            status="scheduled",
        )
        # FP2 started 30 minutes ago
        fp2 = CalendarEvent(
            season=2026,
            round=1,
            session_type="fp2",
            start_ts=now - dt.timedelta(minutes=30),
            end_ts=now + dt.timedelta(minutes=30),
            status="scheduled",
        )
        db_session.add_all([fp1, fp2])
        db_session.commit()

        with patch("theundercut.scheduler_jobs.SessionLocal") as mock_session_local, \
             patch("theundercut.scheduler_jobs.invalidate_race_weekend_cache") as mock_invalidate:
            mock_session_local.return_value.__enter__.return_value = db_session
            mock_session_local.return_value.__exit__ = MagicMock()

            from theundercut.scheduler_jobs import mark_sessions_live
            mark_sessions_live()

        db_session.refresh(fp1)
        db_session.refresh(fp2)
        assert fp1.status == "live"
        assert fp2.status == "live"
        # Cache should be invalidated for each session (same round, so could be 1 or 2 calls)
        assert mock_invalidate.call_count == 2


class TestEnqueueUpcoming:
    """Tests for _enqueue_upcoming_impl() function."""

    def test_queues_ingestion_for_ended_live_sessions(self, db_session):
        """Live sessions that have ended should be queued for ingestion."""
        now = dt.datetime.utcnow()
        session = CalendarEvent(
            season=2026,
            round=1,
            session_type="race",
            start_ts=now - dt.timedelta(hours=3),
            end_ts=now - dt.timedelta(minutes=10),  # Ended 10 minutes ago
            status="live",
        )
        db_session.add(session)
        db_session.commit()

        mock_scheduler = MagicMock()
        mock_scheduler.job_exists.return_value = False

        with patch("theundercut.scheduler_jobs.SessionLocal") as mock_session_local:
            mock_session_local.return_value.__enter__.return_value = db_session
            mock_session_local.return_value.__exit__ = MagicMock()

            from theundercut.scheduler_jobs import _enqueue_upcoming_impl
            _enqueue_upcoming_impl(mock_scheduler)

        mock_scheduler.enqueue_at.assert_called_once()

    def test_ignores_scheduled_sessions(self, db_session):
        """Scheduled sessions should not be queued (they need to be live first)."""
        now = dt.datetime.utcnow()
        session = CalendarEvent(
            season=2026,
            round=1,
            session_type="race",
            start_ts=now - dt.timedelta(hours=3),
            end_ts=now - dt.timedelta(minutes=10),
            status="scheduled",  # Not live
        )
        db_session.add(session)
        db_session.commit()

        mock_scheduler = MagicMock()

        with patch("theundercut.scheduler_jobs.SessionLocal") as mock_session_local:
            mock_session_local.return_value.__enter__.return_value = db_session
            mock_session_local.return_value.__exit__ = MagicMock()

            from theundercut.scheduler_jobs import _enqueue_upcoming_impl
            _enqueue_upcoming_impl(mock_scheduler)

        mock_scheduler.enqueue_at.assert_not_called()

    def test_ignores_still_running_live_sessions(self, db_session):
        """Live sessions that haven't ended yet should not be queued."""
        now = dt.datetime.utcnow()
        session = CalendarEvent(
            season=2026,
            round=1,
            session_type="race",
            start_ts=now - dt.timedelta(hours=1),
            end_ts=now + dt.timedelta(hours=1),  # Still running
            status="live",
        )
        db_session.add(session)
        db_session.commit()

        mock_scheduler = MagicMock()

        with patch("theundercut.scheduler_jobs.SessionLocal") as mock_session_local:
            mock_session_local.return_value.__enter__.return_value = db_session
            mock_session_local.return_value.__exit__ = MagicMock()

            from theundercut.scheduler_jobs import _enqueue_upcoming_impl
            _enqueue_upcoming_impl(mock_scheduler)

        mock_scheduler.enqueue_at.assert_not_called()

    def test_skips_existing_jobs(self, db_session):
        """Sessions with already-scheduled jobs should be skipped."""
        now = dt.datetime.utcnow()
        session = CalendarEvent(
            season=2026,
            round=1,
            session_type="race",
            start_ts=now - dt.timedelta(hours=3),
            end_ts=now - dt.timedelta(minutes=10),
            status="live",
        )
        db_session.add(session)
        db_session.commit()

        mock_scheduler = MagicMock()
        mock_scheduler.job_exists.return_value = True  # Job already exists

        with patch("theundercut.scheduler_jobs.SessionLocal") as mock_session_local:
            mock_session_local.return_value.__enter__.return_value = db_session
            mock_session_local.return_value.__exit__ = MagicMock()

            from theundercut.scheduler_jobs import _enqueue_upcoming_impl
            _enqueue_upcoming_impl(mock_scheduler)

        mock_scheduler.enqueue_at.assert_not_called()
