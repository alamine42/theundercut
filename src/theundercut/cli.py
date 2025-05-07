import datetime as dt
import typer

from theundercut.adapters.db import SessionLocal
from theundercut.adapters.calendar_loader import sync_year

app = typer.Typer(help="The Undercut CLI")

@app.command()
def sync_calendar(
    year: int = typer.Option(dt.datetime.utcnow().year, help="Season to sync")
):
    """Load / refresh the F1 calendar for a season."""
    with SessionLocal() as db:
        sync_year(db, year)
    typer.echo(f"✅  Calendar synced for {year}")
