#!/usr/bin/env python3
"""Diagnose testing data in the database."""
import os
import sys

def main():
    print("=== Testing Data Diagnostics ===")

    # Get DATABASE_URL
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    # Convert postgres:// to postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    print(f"Database URL (prefix): {db_url[:50]}...")

    from sqlalchemy import create_engine, text

    engine = create_engine(db_url, pool_pre_ping=True)

    with engine.connect() as conn:
        # Check if tables exist
        print("\n--- Tables ---")
        result = conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name LIKE 'testing%'"
        ))
        tables = [row[0] for row in result]
        print(f"Testing tables: {tables}")

        if not tables:
            print("ERROR: No testing tables found!")
            sys.exit(1)

        # Check testing_events
        print("\n--- testing_events ---")
        result = conn.execute(text("SELECT COUNT(*) FROM testing_events"))
        count = result.fetchone()[0]
        print(f"Total rows: {count}")

        if count > 0:
            result = conn.execute(text(
                "SELECT id, season, event_id, event_name, status FROM testing_events ORDER BY id"
            ))
            for row in result:
                print(f"  id={row[0]}, season={row[1]}, event_id={row[2]}, name={row[3]}, status={row[4]}")

        # Check testing_sessions
        print("\n--- testing_sessions ---")
        result = conn.execute(text("SELECT COUNT(*) FROM testing_sessions"))
        count = result.fetchone()[0]
        print(f"Total rows: {count}")

        if count > 0:
            result = conn.execute(text(
                "SELECT id, event_id, day, status FROM testing_sessions ORDER BY id"
            ))
            for row in result:
                print(f"  id={row[0]}, event_id={row[1]}, day={row[2]}, status={row[3]}")

        # Check testing_laps
        print("\n--- testing_laps ---")
        result = conn.execute(text("SELECT COUNT(*) FROM testing_laps"))
        count = result.fetchone()[0]
        print(f"Total rows: {count}")

        if count > 0:
            result = conn.execute(text(
                "SELECT driver, COUNT(*) as lap_count FROM testing_laps GROUP BY driver ORDER BY lap_count DESC LIMIT 10"
            ))
            print("Top 10 drivers by lap count:")
            for row in result:
                print(f"  {row[0]}: {row[1]} laps")

    print("\n=== DONE ===")

if __name__ == "__main__":
    main()
