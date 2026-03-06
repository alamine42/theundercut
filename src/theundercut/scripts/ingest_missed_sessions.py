#!/usr/bin/env python3
"""
Manually ingest missed sessions.

Usage:
    python -m theundercut.scripts.ingest_missed_sessions [--season SEASON] [--round ROUND] [--session SESSION] [--all]

Examples:
    # Ingest a specific session
    python -m theundercut.scripts.ingest_missed_sessions --season 2026 --round 1 --session fp2

    # Ingest all missed sessions for current year
    python -m theundercut.scripts.ingest_missed_sessions --all
"""
import argparse
import datetime as dt

from theundercut.adapters.db import SessionLocal
from theundercut.models import CalendarEvent
from theundercut.services.ingestion import ingest_session


def _utc_now() -> dt.datetime:
    """Return current UTC time as timezone-aware datetime."""
    return dt.datetime.now(dt.timezone.utc)


def ingest_single_session(season: int, rnd: int, session_type: str, force: bool = False):
    """Ingest a specific session."""
    print(f"Ingesting {season}-{rnd} {session_type}...")
    try:
        ingest_session(season, rnd, session_type, force=force)
        print(f"  ✓ Successfully ingested {season}-{rnd} {session_type}")
    except Exception as exc:
        print(f"  ✗ Failed to ingest {season}-{rnd} {session_type}: {exc}")


def ingest_all_missed(year: int = None, force: bool = False):
    """Find and ingest all sessions that have ended but aren't ingested."""
    now = _utc_now()
    year = year or now.year

    with SessionLocal() as db:
        # Find sessions that have ended but not ingested
        rows = (
            db.query(CalendarEvent)
            .filter(
                CalendarEvent.season == year,
                CalendarEvent.end_ts + dt.timedelta(minutes=5) <= now,
                CalendarEvent.status.in_(["scheduled", "live"]),
            )
            .order_by(CalendarEvent.start_ts)
            .all()
        )

        if not rows:
            print(f"No missed sessions found for {year}")
            return

        print(f"Found {len(rows)} missed sessions for {year}:")
        for ev in rows:
            print(f"  - {ev.season}-{ev.round} {ev.session_type} (status: {ev.status}, ended: {ev.end_ts})")

        print()
        for ev in rows:
            ingest_single_session(ev.season, ev.round, ev.session_type, force=force)


def main():
    parser = argparse.ArgumentParser(description="Ingest missed F1 sessions")
    parser.add_argument("--season", type=int, help="Season year (e.g., 2026)")
    parser.add_argument("--round", type=int, help="Round number")
    parser.add_argument("--session", type=str, help="Session type (e.g., fp1, fp2, qualifying, race)")
    parser.add_argument("--all", action="store_true", help="Ingest all missed sessions for current year")
    parser.add_argument("--force", action="store_true", help="Force re-ingestion even if already ingested")
    args = parser.parse_args()

    if args.all:
        ingest_all_missed(year=args.season, force=args.force)
    elif args.season and args.round and args.session:
        ingest_single_session(args.season, args.round, args.session, force=args.force)
    else:
        parser.print_help()
        print("\nError: Either use --all or specify --season, --round, and --session")
        exit(1)


if __name__ == "__main__":
    main()
