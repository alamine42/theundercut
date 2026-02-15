from typer.testing import CliRunner

from theundercut.cli import app
from theundercut.models import CalendarEvent


def test_drive_grade_backfill_invokes_ingest(monkeypatch, session_factory):
    runner = CliRunner()
    session = session_factory()
    session.add(CalendarEvent(season=2024, round=1, session_type="Race"))
    session.commit()

    # Use the in-memory session factory inside the CLI
    monkeypatch.setattr("theundercut.cli.SessionLocal", session_factory)

    called = []

    def fake_ingest(season, rnd, session_type="Race", force=False):
        called.append((season, rnd, session_type, force))

    monkeypatch.setattr("theundercut.cli.ingest_session", fake_ingest)

    result = runner.invoke(app, ["drive-grade", "backfill", "2024"])
    assert result.exit_code == 0, result.stdout
    assert called == [(2024, 1, "Race", True)]
