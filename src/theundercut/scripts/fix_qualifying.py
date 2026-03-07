#!/usr/bin/env python3
"""Fix qualifying session with OpenF1 data."""
import datetime as dt

from theundercut.adapters.openf1_loader import OpenF1Provider
from theundercut.adapters.db import SessionLocal
from theundercut.models import SessionClassification
from theundercut.services.cache import redis_client


def main():
    print("Starting qualifying fix...")

    # Delete existing
    db = SessionLocal()
    n = db.query(SessionClassification).filter_by(
        season=2026, round=1, session_type="qualifying"
    ).delete()
    db.commit()
    print(f"Deleted {n} existing records")

    # Load from OpenF1
    p = OpenF1Provider(2026, 1)
    r = p.load_results("qualifying")
    print(f"Loaded {len(r)} results from OpenF1")

    # Show what we're storing
    for _, row in r.head(3).iterrows():
        print(f"  {row['Position']}. {row.get('Abbreviation')} (Driver={row.get('Driver')})")

    # Store results
    for _, row in r.iterrows():
        driver_code = row.get("Abbreviation") or str(row.get("Driver"))
        sc = SessionClassification(
            season=2026,
            round=1,
            session_type="qualifying",
            driver_code=driver_code,
            position=int(row["Position"]),
            team=row.get("TeamName"),
            ingested_at=dt.datetime.utcnow(),
        )
        db.add(sc)
    db.commit()
    db.close()
    print(f"Stored {len(r)} qualifying results")

    # Clear cache
    keys = list(redis_client.scan_iter("*:2026:1*"))
    for k in keys:
        redis_client.delete(k)
    print(f"Cleared {len(keys)} cache keys")
    print("Done!")


if __name__ == "__main__":
    main()
