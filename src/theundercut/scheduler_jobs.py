"""
Scheduler job functions.

These functions are called by the RQ Scheduler. They are extracted into
a separate module to allow testing without importing the scheduler infrastructure.
"""
import datetime as dt

from theundercut.adapters.db import SessionLocal
from theundercut.models import CalendarEvent, TestingEvent, TestingSession
from theundercut.adapters.calendar_loader import sync_year
from theundercut.services.cache import invalidate_race_weekend_cache
from theundercut.services.testing_ingestion import sync_testing_events


def _utc_now() -> dt.datetime:
    """Return current UTC time as timezone-aware datetime."""
    return dt.datetime.now(dt.timezone.utc)


def daily_calendar_sync():
    """Sync the F1 calendar for the current year."""
    year = _utc_now().year
    with SessionLocal() as db:
        sync_year(db, year)


def mark_sessions_live():
    """
    Mark sessions as 'live' when they start.
    Runs every minute to detect session start times.
    """
    now = _utc_now()
    with SessionLocal() as db:
        # Find scheduled sessions that have started
        rows = (
            db.query(CalendarEvent)
            .filter(
                CalendarEvent.start_ts <= now,
                CalendarEvent.status == "scheduled",
            )
            .all()
        )
        for ev in rows:
            ev.status = "live"
            print(f"[scheduler] session live: {ev.season}-{ev.round}-{ev.session_type}")
            # Invalidate cache so frontend sees updated status
            try:
                invalidate_race_weekend_cache(ev.season, ev.round)
            except Exception as exc:
                print(f"[scheduler] cache invalidation failed: {exc}")
        db.commit()


def _enqueue_upcoming_impl(scheduler):
    """
    Queue ingestion jobs for sessions that have ended.
    Looks for sessions where end_ts + 5 min has passed and status is 'live' or 'scheduled'.

    The 'scheduled' check catches sessions that were missed by mark_sessions_live
    (e.g., if the scheduler was down when the session started).

    Takes scheduler as parameter for testability.
    """
    from theundercut.services.ingestion import ingest_session

    now = _utc_now()
    with SessionLocal() as db:
        # Find sessions that have ended but not yet ingested
        # Include both 'live' (normal flow) and 'scheduled' (missed sessions)
        rows = (
            db.query(CalendarEvent)
            .filter(
                CalendarEvent.end_ts + dt.timedelta(minutes=5) <= now,
                CalendarEvent.status.in_(["live", "scheduled"]),
            )
            .all()
        )
        for ev in rows:
            job_id = f"{ev.season}-{ev.round}-{ev.session_type}"
            if scheduler.job_exists(job_id):
                continue

            # If session was 'scheduled' but has ended, mark it as 'live' first for consistency
            if ev.status == "scheduled":
                ev.status = "live"
                print(f"[scheduler] session missed start, marking live: {ev.season}-{ev.round}-{ev.session_type}")
                try:
                    invalidate_race_weekend_cache(ev.season, ev.round)
                except Exception as exc:
                    print(f"[scheduler] cache invalidation failed: {exc}")

            scheduler.enqueue_at(
                ev.end_ts + dt.timedelta(minutes=5),
                ingest_session,
                ev.season,
                ev.round,
                ev.session_type,
                job_id=job_id,
            )
            print(f"[scheduler] queued {job_id}")
            # Status stays 'live' - ingestion job will set to 'ingested'
        db.commit()


def daily_testing_sync():
    """Sync testing events for the current year."""
    year = _utc_now().year
    try:
        sync_testing_events(year)
        print(f"[scheduler] synced testing events for {year}")
    except Exception as exc:
        print(f"[scheduler] failed to sync testing events: {exc}")


def _enqueue_testing_ingestion_impl(scheduler):
    """
    Check for testing sessions that need data ingestion.

    Triggers ingestion for:
    - Testing events marked as 'running' or 'completed'
    - Sessions where the date has passed but no laps exist
    """
    from theundercut.services.testing_ingestion import ingest_testing_day

    now = _utc_now()
    today = now.date()

    with SessionLocal() as db:
        # Find testing events that are active or recently completed
        events = (
            db.query(TestingEvent)
            .filter(
                TestingEvent.status.in_(["running", "scheduled"]),
                TestingEvent.start_date <= today,
            )
            .all()
        )

        for event in events:
            # Check each day of the event
            for day in range(1, event.total_days + 1):
                # Calculate the date for this day
                if event.start_date:
                    day_date = event.start_date + dt.timedelta(days=day - 1)
                    # Only process if the day has passed
                    if day_date > today:
                        continue

                # Check if session exists and has data
                session = (
                    db.query(TestingSession)
                    .filter(
                        TestingSession.event_id == event.id,
                        TestingSession.day == day,
                    )
                    .one_or_none()
                )

                # Skip if session is already completed with data
                if session and session.status == "completed":
                    continue

                # Create job for this day
                job_id = f"testing-{event.season}-{event.event_id}-day{day}"
                if scheduler.job_exists(job_id):
                    continue

                # Schedule ingestion 30 minutes after midnight (to allow data to be available)
                scheduler.enqueue_in(
                    dt.timedelta(minutes=1),  # Run soon
                    ingest_testing_day,
                    event.season,
                    event.event_id,
                    day,
                    job_id=job_id,
                )
                print(f"[scheduler] queued {job_id}")

        # Update event status if all days are done
        for event in events:
            if event.end_date and event.end_date < today:
                completed_sessions = (
                    db.query(TestingSession)
                    .filter(
                        TestingSession.event_id == event.id,
                        TestingSession.status == "completed",
                    )
                    .count()
                )
                if completed_sessions >= event.total_days:
                    event.status = "completed"

        db.commit()
