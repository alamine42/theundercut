import time, datetime as dt
from rq_scheduler import Scheduler
from theundercut.adapters.redis_cache import redis_client
from theundercut.adapters.db import SessionLocal
from theundercut.models import CalendarEvent, TestingEvent, TestingSession
from theundercut.adapters.calendar_loader import sync_year
from theundercut.services.ingestion import ingest_session
from theundercut.services.testing_ingestion import (
    sync_testing_events,
    ingest_testing_day,
)

scheduler = Scheduler(queue_name="default", connection=redis_client, interval=60)


def daily_calendar_sync():
    year = dt.datetime.utcnow().year
    with SessionLocal() as db:
        sync_year(db, year)


def enqueue_upcoming():
    now = dt.datetime.utcnow()
    window = now + dt.timedelta(hours=2)
    with SessionLocal() as db:
        rows = (
            db.query(CalendarEvent)
            .filter(
                CalendarEvent.start_ts <= window,
                CalendarEvent.end_ts + dt.timedelta(minutes=5) <= now,
                CalendarEvent.status == "scheduled",
            )
            .all()
        )
        for ev in rows:
            job_id = f"{ev.season}-{ev.round}-{ev.session_type}"
            if scheduler.job_exists(job_id):
                continue
            scheduler.enqueue_at(
                ev.end_ts + dt.timedelta(minutes=5),
                ingest_session,
                ev.season,
                ev.round,
                ev.session_type,
                job_id=job_id,
            )
            print(f"[scheduler] queued {job_id}")
            ev.status = "running"
        db.commit()


# ─── Testing ingestion jobs ───────────────────────────────────────────


def daily_testing_sync():
    """Sync testing events for the current year."""
    year = dt.datetime.utcnow().year
    try:
        sync_testing_events(year)
        print(f"[scheduler] synced testing events for {year}")
    except Exception as exc:
        print(f"[scheduler] failed to sync testing events: {exc}")


def enqueue_testing_ingestion():
    """
    Check for testing sessions that need data ingestion.

    Triggers ingestion for:
    - Testing events marked as 'running' or 'completed'
    - Sessions where the date has passed but no laps exist
    """
    now = dt.datetime.utcnow()
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


# ─── start recurring jobs ─────────────────────────────────────────────
# Daily calendar refresh at 04:00 UTC
scheduler.cron("0 4 * * *", func=daily_calendar_sync, repeat=None)

# Queue upcoming sessions every 10 minutes
scheduler.cron("*/10 * * * *", func=enqueue_upcoming, repeat=None)

# Daily testing events sync at 05:00 UTC
scheduler.cron("0 5 * * *", func=daily_testing_sync, repeat=None)

# Check for testing ingestion every 30 minutes
scheduler.cron("*/30 * * * *", func=enqueue_testing_ingestion, repeat=None)

print("RQ Scheduler running ⏰")
while True:
    time.sleep(60)
