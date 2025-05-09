"""
RQ job: ingest an F1 session into Postgres.
"""

from __future__ import annotations
import pandas as pd
from sqlalchemy.orm import Session

from theundercut.adapters.resolver import get_provider
from theundercut.adapters.db import SessionLocal
from theundercut.models import LapTime, Stint, CalendarEvent


def _store_laps(db: Session, race_id: str, df: pd.DataFrame) -> None:
    df = (
        df.rename(
            columns={
                "Driver": "driver",
                "LapNumber": "lap",
                "Compound": "compound",
                "Stint": "stint_no",
            }
        )
        .assign(
            race_id=race_id,
            lap_ms=lambda d: d.LapTime.dt.total_seconds() * 1000,
            pit=lambda d: d.PitInTime.notna(),
        )
    )
    db.bulk_insert_mappings(
        LapTime,
        df[["race_id", "driver", "lap", "lap_ms", "compound", "stint_no", "pit"]].to_dict(
            "records"
        ),
    )


def _store_stints(db: Session, race_id: str, df: pd.DataFrame) -> None:
    df = (
        df.groupby(["Driver", "Stint", "Compound"])
        .agg(laps=("LapNumber", "count"), avg=("LapTime", "mean"))
        .reset_index()
        .rename(
            columns={
                "Driver": "driver",
                "Stint": "stint_no",
                "Compound": "compound",
            }
        )
        .assign(
            race_id=race_id,
            avg_lap_ms=lambda d: d.avg.dt.total_seconds() * 1000,
        )
    )
    db.bulk_insert_mappings(
        Stint,
        df[["race_id", "driver", "stint_no", "compound", "laps", "avg_lap_ms"]].to_dict(
            "records"
        ),
    )


def ingest_session(season: int, rnd: int, session_type: str = "Race") -> None:
    """Main RQ job entry‑point."""
    provider = get_provider(season, rnd)
    laps = provider.load_laps(session_type=session_type)
    if laps.empty:
        print(f"[ingestion] No laps for {season}-{rnd} {session_type}")
        return

    with SessionLocal() as db:
        _store_laps(db, race_id, laps)
        _store_stints(db, race_id, laps)
        # mark calendar row
        ev = (
            db.query(CalendarEvent)
            .filter_by(season=season, round=rnd, session_type=session_type)
            .one_or_none()
        )
        if ev:
            ev.status = "ingested"
        db.commit()
    print(f"[ingestion] {race_id} {session_type}: {len(laps)=}")
