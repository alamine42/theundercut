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
