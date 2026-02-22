#!/usr/bin/env python3
"""Ingest 2026 pre-season testing data from OpenF1 - standalone script."""
import os
import sys
from datetime import datetime

def main():
    print("=== OpenF1 Testing Data Ingestion ===")

    # Get DATABASE_URL
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    # Convert postgres:// to postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    print(f"Database URL (prefix): {db_url[:50]}...")

    import httpx
    from sqlalchemy import create_engine, text
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    engine = create_engine(db_url, pool_pre_ping=True)

    # OpenF1 testing session keys for 2026
    TESTING_SESSIONS = [
        {"test": 1, "day": 1, "session_key": 11465, "date": "2026-02-11"},
        {"test": 1, "day": 2, "session_key": 11466, "date": "2026-02-12"},
        {"test": 1, "day": 3, "session_key": 11467, "date": "2026-02-13"},
        {"test": 2, "day": 1, "session_key": 11470, "date": "2026-02-18"},
        {"test": 2, "day": 2, "session_key": 11469, "date": "2026-02-19"},
        {"test": 2, "day": 3, "session_key": 11468, "date": "2026-02-20"},
    ]

    # Fetch driver info
    print("Fetching driver info...")
    drivers_resp = httpx.get(
        "https://api.openf1.org/v1/drivers",
        params={"session_key": 11465}
    )
    drivers_data = drivers_resp.json()
    driver_map = {d["driver_number"]: d for d in drivers_data}
    print(f"  Found {len(driver_map)} drivers")

    with engine.connect() as conn:
        total_laps = 0

        for test_num in [1, 2]:
            event_id = f"bahrain_pre_season_test_{test_num}"
            test_sessions = [s for s in TESTING_SESSIONS if s["test"] == test_num]

            # Check if event exists
            result = conn.execute(text(
                "SELECT id FROM testing_events WHERE season = :season AND event_id = :event_id"
            ), {"season": 2026, "event_id": event_id})
            row = result.fetchone()

            if row:
                event_db_id = row[0]
                print(f"Found existing event: {event_id} (id={event_db_id})")
            else:
                # Insert event
                result = conn.execute(text("""
                    INSERT INTO testing_events (season, event_id, event_name, circuit_id, total_days, start_date, end_date, status)
                    VALUES (:season, :event_id, :event_name, :circuit_id, :total_days, :start_date, :end_date, :status)
                    RETURNING id
                """), {
                    "season": 2026,
                    "event_id": event_id,
                    "event_name": f"Pre-Season Test {test_num}",
                    "circuit_id": "bahrain",
                    "total_days": 3,
                    "start_date": datetime.strptime(test_sessions[0]["date"], "%Y-%m-%d").date(),
                    "end_date": datetime.strptime(test_sessions[-1]["date"], "%Y-%m-%d").date(),
                    "status": "completed",
                })
                event_db_id = result.fetchone()[0]
                print(f"Created event: {event_id} (id={event_db_id})")

            # Process each day
            for sess_info in test_sessions:
                day = sess_info["day"]
                session_key = sess_info["session_key"]

                # Check if session exists
                result = conn.execute(text(
                    "SELECT id FROM testing_sessions WHERE event_id = :event_id AND day = :day"
                ), {"event_id": event_db_id, "day": day})
                row = result.fetchone()

                if row:
                    session_db_id = row[0]
                else:
                    # Insert session
                    result = conn.execute(text("""
                        INSERT INTO testing_sessions (event_id, day, status)
                        VALUES (:event_id, :day, :status)
                        RETURNING id
                    """), {"event_id": event_db_id, "day": day, "status": "completed"})
                    session_db_id = result.fetchone()[0]

                # Check if laps exist
                result = conn.execute(text(
                    "SELECT COUNT(*) FROM testing_laps WHERE session_id = :session_id"
                ), {"session_id": session_db_id})
                lap_count = result.fetchone()[0]

                if lap_count > 0:
                    print(f"  Test {test_num} Day {day}: Already has {lap_count} laps")
                    total_laps += lap_count
                    continue

                # Fetch laps from OpenF1
                print(f"  Fetching laps for Test {test_num} Day {day} (session_key={session_key})...")
                try:
                    laps_resp = httpx.get(
                        "https://api.openf1.org/v1/laps",
                        params={"session_key": session_key},
                        timeout=60
                    )
                    laps_data = laps_resp.json()
                except Exception as e:
                    print(f"    Error fetching laps: {e}")
                    continue

                if not laps_data:
                    print(f"    No lap data found")
                    continue

                # Insert laps
                for lap in laps_data:
                    driver_num = lap.get("driver_number")
                    driver_info = driver_map.get(driver_num, {})
                    driver_code = driver_info.get("name_acronym", f"D{driver_num}")
                    team = driver_info.get("team_name", "Unknown")

                    lap_duration = lap.get("lap_duration")
                    lap_time_ms = lap_duration * 1000 if lap_duration else None

                    s1 = lap.get("duration_sector_1")
                    s2 = lap.get("duration_sector_2")
                    s3 = lap.get("duration_sector_3")

                    try:
                        conn.execute(text("""
                            INSERT INTO testing_laps (session_id, driver, team, lap_number, lap_time_ms, sector_1_ms, sector_2_ms, sector_3_ms, is_valid)
                            VALUES (:session_id, :driver, :team, :lap_number, :lap_time_ms, :sector_1_ms, :sector_2_ms, :sector_3_ms, :is_valid)
                            ON CONFLICT (session_id, driver, lap_number) DO NOTHING
                        """), {
                            "session_id": session_db_id,
                            "driver": driver_code,
                            "team": team,
                            "lap_number": lap.get("lap_number", 0),
                            "lap_time_ms": lap_time_ms,
                            "sector_1_ms": s1 * 1000 if s1 else None,
                            "sector_2_ms": s2 * 1000 if s2 else None,
                            "sector_3_ms": s3 * 1000 if s3 else None,
                            "is_valid": lap.get("is_pit_out_lap") is not True,
                        })
                    except Exception as e:
                        print(f"    Error inserting lap: {e}")

                print(f"    Inserted {len(laps_data)} laps")
                total_laps += len(laps_data)

        # Commit
        print("Committing...")
        conn.commit()
        print("Committed!")

        # Verify
        result = conn.execute(text("SELECT COUNT(*) FROM testing_events"))
        event_count = result.fetchone()[0]
        result = conn.execute(text("SELECT COUNT(*) FROM testing_laps"))
        lap_count = result.fetchone()[0]

        print(f"\n=== Summary ===")
        print(f"Events: {event_count}")
        print(f"Laps: {lap_count}")

    print("=== DONE ===")

if __name__ == "__main__":
    main()
