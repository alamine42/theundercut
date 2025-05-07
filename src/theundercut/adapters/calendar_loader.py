"""
calendar_loader.py
------------------
Download the Formula 1 session timetable for a given season and store it
in the `calendar_events` table.

Usage
-----
from sqlalchemy.orm import Session
from theundercut.adapters.calendar_loader import sync_year
sync_year(db_session, 2025)
"""
from __future__ import annotations

import datetime as dt
from typing import List, Dict

import httpx
import pandas as pd
import fastf1
from sqlalchemy import select
from sqlalchemy.orm import Session

from theundercut.models import CalendarEvent

_OPENF1_SESSIONS = "https://api.openf1.org/v1/sessions"


# --------------------------------------------------------------------------- #
# Helpers                                                                     #
# --------------------------------------------------------------------------- #
def _openf1_year(year: int) -> List[Dict]:
    """Return OpenF1 session dicts for a season."""
    with httpx.Client(timeout=15) as client:
        resp = client.get(_OPENF1_SESSIONS, params={"year": year})
        resp.raise_for_status()
        return resp.json()


def _normalize_openf1(rows: List[Dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df = (
        df.rename(
            columns={
                "session_name": "session_type",
                "date_start": "start_ts",
                "date_end": "end_ts",
                "meeting_key": "meeting_key",
            }
        )
        .assign(
            start_ts=lambda d: pd.to_datetime(d.start_ts, utc=True),
            end_ts=lambda d: pd.to_datetime(d.end_ts, utc=True),
            status="scheduled",
        )
    )
    # meeting_key groups a weekend (round); rank dense gives 1..23
    df["round"] = df["meeting_key"].rank(method="dense").astype(int)
    df["season"] = df["year"]
    return df[
        ["season", "round", "session_type", "start_ts", "end_ts", "meeting_key", "status"]
    ]


def _fastf1_year(year: int) -> pd.DataFrame:
    sch = fastf1.get_event_schedule(year, include_testing=False)
    # melt the wide table into rows
    melted = (
        sch.melt(
            id_vars=["RoundNumber", "EventDate", "Country"],
            value_vars=[c for c in sch.columns if c.startswith("Session")],
            var_name="session_col",
            value_name="start_ts",
        )
        .dropna(subset=["start_ts"])
    )
    melted["session_type"] = (
        melted["session_col"]
        .str.extract(r"(Session\d)")
        .fillna("Race")
        .replace(
            {
                "Session1": "FP1",
                "Session2": "FP2",
                "Session3": "FP3",
                "Session4": "Qualifying",
            }
        )
    )
    melted["start_ts"] = pd.to_datetime(melted["start_ts"], utc=True)
    melted["end_ts"] = melted["start_ts"] + pd.Timedelta(hours=2)
    melted["season"] = year
    melted["round"] = melted["RoundNumber"].astype(int)
    melted["status"] = "scheduled"
    melted["meeting_key"] = None
    return melted[
        ["season", "round", "session_type", "start_ts", "end_ts", "meeting_key", "status"]
    ]


# --------------------------------------------------------------------------- #
# Public function                                                             #
# --------------------------------------------------------------------------- #
def sync_year(db: Session, year: int) -> None:
    """
    Pull the full session timetable for `year` and upsert into Postgres.

    Rows already present (matched on season, round, session_type) are updated.
    New rows are inserted. Counts are logged to stdout.
    """
    if year >= 2022:
        raw_rows = _openf1_year(year)
        df = _normalize_openf1(raw_rows)
    else:
        df = _fastf1_year(year)

    inserted, updated = 0, 0

    for rec in df.to_dict(orient="records"):
        stmt = select(CalendarEvent).where(
            CalendarEvent.season == rec["season"],
            CalendarEvent.round == rec["round"],
            CalendarEvent.session_type == rec["session_type"],
        )
        existing: CalendarEvent | None = db.execute(stmt).scalar_one_or_none()

        if existing:
            # Update fields if they changed
            existing.start_ts = rec["start_ts"]
            existing.end_ts = rec["end_ts"]
            existing.meeting_key = rec["meeting_key"]
            existing.status = existing.status or "scheduled"
            updated += 1
        else:
            db.add(CalendarEvent(**rec))
            inserted += 1

    db.commit()
    print(f"[calendar_loader] {year}: {inserted} inserted, {updated} updated.")
