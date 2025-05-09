import time, datetime as dt
from rq_scheduler import Scheduler
from theundercut.adapters.redis_cache import redis_client
from theundercut.adapters.db import SessionLocal
from theundercut.models import CalendarEvent
from theundercut.adapters.calendar_loader import sync_year
from theundercut.services.ingestion import ingest_session

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


# ─── start recurring jobs ─────────────────────────────────────────────
# Daily calendar refresh at 04:00 UTC
scheduler.cron("0 4 * * *", func=daily_calendar_sync, repeat=None)

# Queue upcoming sessions every 10 minutes
scheduler.cron("*/10 * * * *", func=enqueue_upcoming, repeat=None)

print("RQ Scheduler running ⏰")
while True:
    time.sleep(60)
