import datetime as dt
import json
from pathlib import Path
from typing import Dict, List, Optional

import typer

from theundercut.adapters.db import SessionLocal
from theundercut.adapters.calendar_loader import sync_year
from theundercut.models import CalendarEvent
from theundercut.services.ingestion import ingest_session
from theundercut.drive_grade.calibration import (
    load_calibration_profile,
    set_active_calibration,
)
from theundercut.drive_grade.data_loader import (
    TableValidationError,
    WeekendTableLoader,
)
from theundercut.drive_grade.pipeline import DriveGradePipeline
from theundercut.drive_grade.season import SeasonRunner

app = typer.Typer(help="The Undercut CLI")

@app.command()
def sync_calendar(
    year: int = typer.Option(dt.datetime.utcnow().year, help="Season to sync")
):
    """Load / refresh the F1 calendar for a season."""
    with SessionLocal() as db:
        sync_year(db, year)
    typer.echo(f"✅  Calendar synced for {year}")


drive_grade_app = typer.Typer(help="Driver Grade utilities (JSON or table inputs)")
app.add_typer(drive_grade_app, name="drive-grade")
calibration_cli = typer.Typer(help="Manage Drive Grade calibration profiles")
drive_grade_app.add_typer(calibration_cli, name="calibration")


def _set_calibration(profile: str | None) -> None:
    set_active_calibration(load_calibration_profile(profile))


@drive_grade_app.command("run-file")
def drive_grade_run_file(
    input_path: Path = typer.Argument(..., exists=True, readable=True),
    loader_format: str | None = typer.Option(
        None, "--format", help="Force loader format: 'json' or 'tables'."
    ),
    calibration_profile: str = typer.Option(
        "baseline",
        "--profile",
        help="Calibration profile name (configs/calibration/<name>.json).",
    ),
):
    """
    Run Drive Grade against a single race input (JSON weekend or tables directory).
    """
    _set_calibration(calibration_profile)
    if loader_format and loader_format not in {"json", "tables"}:
        raise typer.BadParameter("format must be 'json' or 'tables'")
    fmt = loader_format or ("tables" if input_path.is_dir() else "json")
    typer.echo(f"▶️  Running Drive Grade for {input_path} (format={fmt})")
    pipeline = DriveGradePipeline()
    try:
        if fmt == "json":
            results = pipeline.run_from_json(input_path)
        else:
            loader = WeekendTableLoader(input_path)
            driver_inputs = loader.build_driver_inputs()
            results = {driver.driver: pipeline.score_driver(driver) for driver in driver_inputs}
    except TableValidationError as exc:
        typer.echo(f"❌ Invalid table data: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    for driver, breakdown in results.items():
        typer.echo(
            f"{driver}: total={breakdown.total_grade:.3f} "
            f"(consistency={breakdown.consistency_score:.3f}, "
            f"strategy={breakdown.team_strategy_score:.3f}, "
            f"racecraft={breakdown.racecraft_score:.3f}, "
            f"penalties={breakdown.penalty_score:.3f}) "
            f"[on-track {breakdown.on_track_events}, pit-cycle {breakdown.pit_cycle_events}]"
        )


def _discover_races(root: Path) -> Dict[str, Path]:
    races: Dict[str, Path] = {}
    for entry in sorted(root.iterdir()):
        if entry.name.startswith("."):
            continue
        if entry.is_dir():
            races[entry.name] = entry
        elif entry.suffix.lower() == ".json":
            races[entry.stem] = entry
    return races


@drive_grade_app.command("run-season")
def drive_grade_run_season(
    season_path: Path = typer.Argument(..., exists=True, help="Directory containing race JSON files or table folders."),
    output_dir: Path = typer.Option(
        Path("outputs/season"),
        "--output",
        help="Directory where race + season CSVs will be stored.",
    ),
    manifest: Path | None = typer.Option(
        None,
        "--manifest",
        help="Optional JSON mapping of race names to explicit file paths.",
    ),
    calibration_profile: str = typer.Option(
        "baseline",
        "--profile",
        help="Calibration profile name.",
    ),
):
    """
    Run Drive Grade for every race under SEASON_PATH (or a manifest) and save outputs.
    """
    _set_calibration(calibration_profile)
    if manifest:
        race_mapping = {race: Path(path) for race, path in json.loads(manifest.read_text()).items()}
    else:
        race_mapping = _discover_races(season_path)

    if not race_mapping:
        typer.echo("❌ No race inputs found. Provide JSON files or directories.", err=True)
        raise typer.Exit(code=2)

    runner = SeasonRunner()
    try:
        results = runner.run_season(race_mapping)
    except TableValidationError as exc:
        typer.echo(f"❌ Invalid data while processing season: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    runner.save_outputs(results, output_dir)
    typer.echo(f"✅ Processed {len(results.race_results)} races. Results saved to {output_dir}")


@drive_grade_app.command("backfill")
def drive_grade_backfill(
    season: int = typer.Argument(..., help="Season year to backfill"),
    round_number: Optional[int] = typer.Option(
        None,
        "--round",
        "-r",
        help="Specific round to backfill (defaults to every race in the season).",
    ),
    session_type: str = typer.Option("Race", "--session-type", help="Session type to target (default: Race)"),
):
    """
    Re-run Drive Grade computation for races that already have lap data.
    """
    with SessionLocal() as db:
        if round_number is not None:
            rounds: List[int] = [round_number]
        else:
            rows = (
                db.query(CalendarEvent.round)
                .filter(
                    CalendarEvent.season == season,
                    CalendarEvent.session_type == session_type,
                )
                .distinct()
                .order_by(CalendarEvent.round)
                .all()
            )
            rounds = [row[0] for row in rows]
    if not rounds:
        typer.echo(f"❌ No {session_type} rounds found for {season}", err=True)
        raise typer.Exit(code=1)

    for rnd in rounds:
        typer.echo(f"▶️  Recomputing Drive Grade for {season}-{rnd} ({session_type})")
        ingest_session(season, rnd, session_type=session_type, force=True)
    typer.echo(f"✅ Backfilled {len(rounds)} round(s) for {season} {session_type}")


# =============================================================================
# Testing CLI
# =============================================================================

testing_app = typer.Typer(help="Pre-season testing data management")
app.add_typer(testing_app, name="testing")


@testing_app.command("sync")
def testing_sync(
    season: int = typer.Argument(..., help="Season year to sync testing events for"),
):
    """
    Sync testing events from FastF1 schedule to database.
    """
    from theundercut.services.testing_ingestion import sync_testing_events

    typer.echo(f"▶️  Syncing testing events for {season}...")
    try:
        results = sync_testing_events(season)
        if not results:
            typer.echo(f"⚠️  No testing events found for {season}")
            return
        for event in results:
            action = event.get("action", "unknown")
            event_id = event.get("event_id", "unknown")
            typer.echo(f"  {action}: {event_id}")
        typer.echo(f"✅ Synced {len(results)} testing event(s) for {season}")
    except Exception as exc:
        typer.echo(f"❌ Failed to sync testing events: {exc}", err=True)
        raise typer.Exit(code=2) from exc


@testing_app.command("ingest")
def testing_ingest(
    season: int = typer.Argument(..., help="Season year"),
    event_id: str = typer.Argument(..., help="Testing event ID (e.g., 'pre_season_testing')"),
    day: Optional[int] = typer.Option(
        None,
        "--day",
        "-d",
        help="Specific day to ingest (defaults to all days)",
    ),
    force: bool = typer.Option(False, "--force", "-f", help="Re-ingest even if data exists"),
):
    """
    Ingest testing data from FastF1.
    """
    from theundercut.services.testing_ingestion import (
        ingest_testing_event,
        ingest_testing_day,
    )

    if day is not None:
        typer.echo(f"▶️  Ingesting day {day} of {event_id} ({season})...")
        try:
            result = ingest_testing_day(season, event_id, day, force=force)
            status = result.get("status", "unknown")
            laps = result.get("laps_count", 0)
            stints = result.get("stints_count", 0)
            if status == "completed":
                typer.echo(f"✅ Ingested day {day}: {laps} laps, {stints} stints")
            elif status == "already_ingested":
                typer.echo(f"ℹ️  Day {day} already ingested ({laps} laps)")
            elif status == "no_data":
                typer.echo(f"⚠️  No data available for day {day}")
            else:
                typer.echo(f"⚠️  Day {day} status: {status}")
        except Exception as exc:
            typer.echo(f"❌ Failed to ingest day {day}: {exc}", err=True)
            raise typer.Exit(code=2) from exc
    else:
        typer.echo(f"▶️  Ingesting all days of {event_id} ({season})...")
        try:
            result = ingest_testing_event(season, event_id, force=force)
            days = result.get("days_ingested", 0)
            laps = result.get("total_laps", 0)
            stints = result.get("total_stints", 0)
            errors = result.get("errors", [])
            if errors:
                for error in errors:
                    typer.echo(f"  ⚠️  {error}")
            if days > 0:
                typer.echo(f"✅ Ingested {days} day(s): {laps} laps, {stints} stints")
            else:
                typer.echo(f"⚠️  No data ingested for {event_id}")
        except Exception as exc:
            typer.echo(f"❌ Failed to ingest event: {exc}", err=True)
            raise typer.Exit(code=2) from exc


@testing_app.command("backfill")
def testing_backfill(
    season: int = typer.Argument(..., help="Season year to backfill testing data for"),
    force: bool = typer.Option(False, "--force", "-f", help="Re-ingest even if data exists"),
):
    """
    Backfill all testing events for a season.
    """
    from theundercut.services.testing_ingestion import (
        sync_testing_events,
        ingest_testing_event,
    )

    typer.echo(f"▶️  Backfilling testing data for {season}...")

    # First sync events
    try:
        events = sync_testing_events(season)
        if not events:
            typer.echo(f"⚠️  No testing events found for {season}")
            return
        typer.echo(f"  Found {len(events)} testing event(s)")
    except Exception as exc:
        typer.echo(f"❌ Failed to sync testing events: {exc}", err=True)
        raise typer.Exit(code=2) from exc

    # Then ingest each event
    total_laps = 0
    total_stints = 0
    for event in events:
        event_id = event.get("event_id")
        typer.echo(f"  ▶️  Ingesting {event_id}...")
        try:
            result = ingest_testing_event(season, event_id, force=force)
            laps = result.get("total_laps", 0)
            stints = result.get("total_stints", 0)
            total_laps += laps
            total_stints += stints
            days = result.get("days_ingested", 0)
            if days > 0:
                typer.echo(f"    ✅ {days} day(s), {laps} laps, {stints} stints")
            else:
                typer.echo(f"    ⚠️  No data available")
        except Exception as exc:
            typer.echo(f"    ❌ Failed: {exc}")

    typer.echo(f"✅ Backfill complete: {total_laps} laps, {total_stints} stints")


@testing_app.command("create-tables")
def testing_create_tables():
    """
    Create testing tables directly (bypasses Alembic migrations).

    Use this if migrations are stuck and testing tables need to be created.
    """
    from theundercut.adapters.db import engine
    from sqlalchemy import text

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
        "CREATE INDEX IF NOT EXISTS ix_testing_event_lookup ON testing_events(season, event_id)",
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
        "CREATE INDEX IF NOT EXISTS ix_testing_lap_driver ON testing_laps(session_id, driver)",
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

    typer.echo("Creating testing tables...")
    typer.echo(f"  Database: {str(engine.url)[:50]}...")
    try:
        with engine.connect() as conn:
            for i, stmt in enumerate(STATEMENTS, 1):
                typer.echo(f"  Executing statement {i}/{len(STATEMENTS)}...")
                try:
                    conn.execute(text(stmt))
                    typer.echo(f"    Statement {i} executed OK")
                except Exception as e:
                    typer.echo(f"    Statement {i} FAILED: {e}", err=True)
                    raise
            typer.echo("  Committing transaction...")
            conn.commit()
            typer.echo("  Committed. Verifying tables exist...")
            result = conn.execute(text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema='public' AND table_name LIKE 'testing%'"
            ))
            tables = [row[0] for row in result]
            typer.echo(f"  Found tables: {tables}")
            if not tables:
                typer.echo("  ERROR: No tables found after creation!", err=True)
                raise typer.Exit(code=1)
    except Exception as e:
        typer.echo(f"  FATAL ERROR: {e}", err=True)
        raise typer.Exit(code=1)
    typer.echo("✅ Testing tables created successfully")


@testing_app.command("ingest-openf1")
def testing_ingest_openf1(
    season: int = typer.Argument(..., help="Season year"),
):
    """
    Ingest 2026 pre-season testing data from OpenF1 API.

    OpenF1 has testing data that FastF1 may not have yet.
    """
    import httpx
    from datetime import datetime
    from theundercut.adapters.db import SessionLocal
    from theundercut.models import TestingEvent, TestingSession, TestingLap
    from sqlalchemy.dialects.postgresql import insert as pg_insert

    if season != 2026:
        typer.echo(f"⚠️  OpenF1 ingestion currently only supports 2026 season")
        raise typer.Exit(code=1)

    typer.echo(f"▶️  Fetching 2026 pre-season testing data from OpenF1...")

    # OpenF1 testing session keys for 2026
    # Test 1: Feb 11-13 (Bahrain)
    # Test 2: Feb 18-20 (Bahrain)
    TESTING_SESSIONS = [
        {"test": 1, "day": 1, "session_key": 11465, "date": "2026-02-11"},
        {"test": 1, "day": 2, "session_key": 11466, "date": "2026-02-12"},
        {"test": 1, "day": 3, "session_key": 11467, "date": "2026-02-13"},
        {"test": 2, "day": 1, "session_key": 11470, "date": "2026-02-18"},
        {"test": 2, "day": 2, "session_key": 11469, "date": "2026-02-19"},
        {"test": 2, "day": 3, "session_key": 11468, "date": "2026-02-20"},
    ]

    # Fetch driver info first
    typer.echo("  Fetching driver info...")
    drivers_resp = httpx.get(
        "https://api.openf1.org/v1/drivers",
        params={"session_key": 11465}
    )
    drivers_data = drivers_resp.json()
    driver_map = {d["driver_number"]: d for d in drivers_data}
    typer.echo(f"    Found {len(driver_map)} drivers")

    with SessionLocal() as db:
        total_laps = 0

        for test_num in [1, 2]:
            event_id = f"bahrain_pre_season_test_{test_num}"
            test_sessions = [s for s in TESTING_SESSIONS if s["test"] == test_num]

            # Create or get the testing event
            event = (
                db.query(TestingEvent)
                .filter(TestingEvent.season == season, TestingEvent.event_id == event_id)
                .one_or_none()
            )

            if not event:
                event = TestingEvent(
                    season=season,
                    event_id=event_id,
                    event_name=f"Pre-Season Test {test_num}",
                    circuit_id="bahrain",
                    total_days=3,
                    start_date=datetime.strptime(test_sessions[0]["date"], "%Y-%m-%d").date(),
                    end_date=datetime.strptime(test_sessions[-1]["date"], "%Y-%m-%d").date(),
                    status="completed",
                )
                db.add(event)
                db.flush()
                typer.echo(f"  Created event: {event_id}")
            else:
                typer.echo(f"  Found existing event: {event_id}")

            # Process each day
            for sess_info in test_sessions:
                day = sess_info["day"]
                session_key = sess_info["session_key"]

                # Create or get the session
                session = (
                    db.query(TestingSession)
                    .filter(TestingSession.event_id == event.id, TestingSession.day == day)
                    .one_or_none()
                )

                if not session:
                    session = TestingSession(
                        event_id=event.id,
                        day=day,
                        status="completed",
                    )
                    db.add(session)
                    db.flush()

                # Check if laps already exist
                existing_laps = db.query(TestingLap).filter(TestingLap.session_id == session.id).count()
                if existing_laps > 0:
                    typer.echo(f"    Test {test_num} Day {day}: Already has {existing_laps} laps")
                    total_laps += existing_laps
                    continue

                # Fetch laps from OpenF1
                typer.echo(f"    Fetching laps for Test {test_num} Day {day} (session_key={session_key})...")
                laps_resp = httpx.get(
                    "https://api.openf1.org/v1/laps",
                    params={"session_key": session_key},
                    timeout=60
                )
                laps_data = laps_resp.json()

                if not laps_data:
                    typer.echo(f"      No lap data found")
                    continue

                # Prepare lap records
                records = []
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

                    records.append({
                        "session_id": session.id,
                        "driver": driver_code,
                        "team": team,
                        "lap_number": lap.get("lap_number", 0),
                        "lap_time_ms": lap_time_ms,
                        "compound": None,  # OpenF1 doesn't have compound in laps
                        "stint_number": None,
                        "sector_1_ms": s1 * 1000 if s1 else None,
                        "sector_2_ms": s2 * 1000 if s2 else None,
                        "sector_3_ms": s3 * 1000 if s3 else None,
                        "is_valid": lap.get("is_pit_out_lap") is not True,
                    })

                if records:
                    stmt = pg_insert(TestingLap).values(records)
                    stmt = stmt.on_conflict_do_nothing(
                        index_elements=["session_id", "driver", "lap_number"]
                    )
                    db.execute(stmt)
                    typer.echo(f"      Inserted {len(records)} laps")
                    total_laps += len(records)

        db.commit()
        typer.echo(f"✅ Ingested {total_laps} total laps for 2026 pre-season testing")


@calibration_cli.command("import")
def calibration_import_profile(
    name: str = typer.Argument(..., help="Calibration profile name to store"),
    file_path: Path = typer.Argument(..., exists=True, readable=True, help="Path to calibration JSON file"),
    activate: bool = typer.Option(False, "--activate/--no-activate", help="Mark this profile as active after import"),
):
    """
    Import a calibration JSON file into the config.calibration_profiles table.
    """
    from theundercut.drive_grade.calibration_store import upsert_profile_from_file

    try:
        profile = upsert_profile_from_file(name, file_path, activate=activate)
    except Exception as exc:  # pragma: no cover - database connectivity issues
        typer.echo(f"❌ Failed to import calibration profile: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    status = " (active)" if activate else ""
    typer.echo(f"✅ Imported calibration '{profile.name}' from {file_path}{status}")


@calibration_cli.command("set-active")
def calibration_set_active(name: str = typer.Argument(..., help="Existing profile name to activate")):
    """
    Mark a stored calibration profile as the active one.
    """
    from theundercut.drive_grade.calibration_store import set_active_profile

    ok = False
    try:
        ok = set_active_profile(name)
    except Exception as exc:  # pragma: no cover
        typer.echo(f"❌ Failed to update calibration profile: {exc}", err=True)
        raise typer.Exit(code=2) from exc
    if not ok:
        typer.echo(f"❌ Calibration profile '{name}' not found in database", err=True)
        raise typer.Exit(code=2)
    typer.echo(f"✅ '{name}' is now the active calibration profile")
