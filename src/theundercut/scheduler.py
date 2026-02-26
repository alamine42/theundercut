"""
RQ Scheduler main loop.

This module sets up the scheduler and runs the main loop.
Job functions are defined in scheduler_jobs.py for testability.
"""
import time

from rq_scheduler import Scheduler
from theundercut.adapters.redis_cache import redis_client
from theundercut.scheduler_jobs import (
    daily_calendar_sync,
    mark_sessions_live,
    daily_testing_sync,
    _enqueue_upcoming_impl,
    _enqueue_testing_ingestion_impl,
)

scheduler = Scheduler(queue_name="default", connection=redis_client, interval=60)


def enqueue_upcoming():
    """Wrapper that passes scheduler to implementation."""
    _enqueue_upcoming_impl(scheduler)


def enqueue_testing_ingestion():
    """Wrapper that passes scheduler to implementation."""
    _enqueue_testing_ingestion_impl(scheduler)


if __name__ == "__main__":
    # ─── start recurring jobs ─────────────────────────────────────────────
    # Daily calendar refresh at 04:00 UTC
    scheduler.cron("0 4 * * *", func=daily_calendar_sync, repeat=None)

    # Mark sessions as live every minute (detects session starts)
    scheduler.cron("* * * * *", func=mark_sessions_live, repeat=None)

    # Queue ingestion for completed sessions every 10 minutes
    scheduler.cron("*/10 * * * *", func=enqueue_upcoming, repeat=None)

    # Daily testing events sync at 05:00 UTC
    scheduler.cron("0 5 * * *", func=daily_testing_sync, repeat=None)

    # Check for testing ingestion every 30 minutes
    scheduler.cron("*/30 * * * *", func=enqueue_testing_ingestion, repeat=None)

    print("RQ Scheduler running ⏰")
    while True:
        time.sleep(60)
