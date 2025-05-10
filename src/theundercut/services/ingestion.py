"""
RQ job: ingest an F1 session into Postgres.
"""

from __future__ import annotations
import pandas as pd
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert as pg_insert

from theundercut.adapters.resolver import get_provider
from theundercut.adapters.db import SessionLocal
from theundercut.models import LapTime, Stint, CalendarEvent


def _store_laps(db: Session, race_id: str, df: pd.DataFrame) -> None:
    """
    Clean, normalise and bulk-insert lap records.
    If the unique index (race_id, driver, lap) already has a row,
    ON CONFLICT DO NOTHING prevents duplicates.
    """
    cleaned = (
        df.rename(
            columns={
                "Driver": "driver",
                "LapNumber": "lap",
                "Compound": "compound",
                "Stint": "stint_no",
            }
        )
        .assign(
            lap_ms=lambda d: (
                d.LapTime.dt.total_seconds() * 1000
            ).round().astype("Int64"),
            lap=lambda d: d.lap.astype("Int64"),
            stint_no=lambda d: d.stint_no.astype("Int64"),
            pit=lambda d: d.PitInTime.notna(),
            race_id=race_id,
        )
        .fillna({"lap_ms": -1, "lap": -1, "stint_no": -1})
    )

    stmt = pg_insert(LapTime).values(
        cleaned[
            ["race_id", "driver", "lap", "lap_ms", "compound", "stint_no", "pit"]
        ].to_dict("records")
    )

    # If a row with same (race_id, driver, lap) exists, skip it.
    stmt = stmt.on_conflict_do_nothing(
        index_elements=["race_id", "driver", "lap"]
    )

    db.execute(stmt)



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

    race_id = f"{season}-{rnd}"

    with SessionLocal() as db:
        already = db.scalar(
            sa.text("SELECT 1 FROM lap_times WHERE race_id = :rid LIMIT 1"),
            {"rid": f"{season}-{rnd}"},
        )
    if already:
        print(f"[ingestion] {season}-{rnd} already ingested, skipping.")
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
