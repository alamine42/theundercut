#!/usr/bin/env python3
"""Create testing tables - standalone script with full diagnostics."""
import os
import sys

def main():
    print("=== Testing Tables Creation Script ===")

    # Get DATABASE_URL
    db_url = os.environ.get("DATABASE_URL", "")
    if not db_url:
        print("ERROR: DATABASE_URL not set")
        sys.exit(1)

    # Convert postgres:// to postgresql://
    if db_url.startswith("postgres://"):
        db_url = db_url.replace("postgres://", "postgresql://", 1)

    print(f"Database URL (prefix): {db_url[:50]}...")

    # Import SQLAlchemy and create engine
    from sqlalchemy import create_engine, text, inspect

    engine = create_engine(db_url, pool_pre_ping=True)
    print(f"Engine created: {engine}")

    # SQL statements
    STATEMENTS = [
        """CREATE TABLE IF NOT EXISTS testing_events (
            id SERIAL PRIMARY KEY,
            season INTEGER NOT NULL,
            event_id VARCHAR(50) NOT NULL,
            event_name VARCHAR(100) NOT NULL,
            circuit_id VARCHAR(50) NOT NULL,
            total_days INTEGER DEFAULT 3,
            start_date DATE,
            end_date DATE,
            status VARCHAR(20) DEFAULT 'scheduled',
            UNIQUE(season, event_id)
        )""",
        "CREATE INDEX IF NOT EXISTS ix_testing_events_season ON testing_events(season)",
        """CREATE TABLE IF NOT EXISTS testing_sessions (
            id SERIAL PRIMARY KEY,
            event_id INTEGER NOT NULL REFERENCES testing_events(id) ON DELETE CASCADE,
            day INTEGER NOT NULL,
            date DATE,
            status VARCHAR(20) DEFAULT 'scheduled',
            UNIQUE(event_id, day)
        )""",
        """CREATE TABLE IF NOT EXISTS testing_laps (
            id SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL REFERENCES testing_sessions(id) ON DELETE CASCADE,
            driver VARCHAR(3) NOT NULL,
            team VARCHAR(50),
            lap_number INTEGER NOT NULL,
            lap_time_ms FLOAT,
            compound VARCHAR(20),
            stint_number INTEGER,
            sector_1_ms FLOAT,
            sector_2_ms FLOAT,
            sector_3_ms FLOAT,
            is_valid BOOLEAN DEFAULT TRUE,
            UNIQUE(session_id, driver, lap_number)
        )""",
        """CREATE TABLE IF NOT EXISTS testing_stints (
            id SERIAL PRIMARY KEY,
            session_id INTEGER NOT NULL REFERENCES testing_sessions(id) ON DELETE CASCADE,
            driver VARCHAR(3) NOT NULL,
            team VARCHAR(50),
            stint_number INTEGER NOT NULL,
            compound VARCHAR(20),
            start_lap INTEGER,
            end_lap INTEGER,
            lap_count INTEGER,
            avg_pace_ms FLOAT,
            UNIQUE(session_id, driver, stint_number)
        )""",
    ]

    # Create tables
    print("\n--- Creating tables ---")
    with engine.connect() as conn:
        for i, stmt in enumerate(STATEMENTS, 1):
            print(f"Executing statement {i}...")
            conn.execute(text(stmt))
        print("Committing...")
        conn.commit()
        print("Committed!")

        # Verify in same connection
        print("\n--- Verifying (same connection) ---")
        result = conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name LIKE 'testing%'"
        ))
        tables = [row[0] for row in result]
        print(f"Tables found: {tables}")

    # Verify with fresh connection
    print("\n--- Verifying (new connection) ---")
    engine2 = create_engine(db_url, pool_pre_ping=True)
    with engine2.connect() as conn2:
        result = conn2.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema='public' AND table_name LIKE 'testing%'"
        ))
        tables2 = [row[0] for row in result]
        print(f"Tables found: {tables2}")

    if len(tables2) >= 4:
        print("\n=== SUCCESS ===")
        sys.exit(0)
    else:
        print("\n=== FAILURE: Tables not persisted ===")
        sys.exit(1)

if __name__ == "__main__":
    main()
