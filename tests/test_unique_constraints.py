"""Tests for unique constraint functionality (UND-42).

Verifies that SQLite ATTACH and the inline unique constraint on
lap_times(race_id, driver, lap) behave correctly after database setup.
"""

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from theundercut.models import Base, LapTime


def _build_engine():
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        future=True,
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    with engine.connect() as conn:
        conn.exec_driver_sql("ATTACH DATABASE ':memory:' AS core")
        conn.exec_driver_sql("ATTACH DATABASE ':memory:' AS config")
        conn.exec_driver_sql("ATTACH DATABASE ':memory:' AS validation")
    return engine


@pytest.fixture()
def db():
    engine = _build_engine()
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_lap_race_driver_lap "
            "ON lap_times (race_id, driver, lap)"
        ))
    Session = sessionmaker(bind=engine, future=True)
    session = Session()
    yield session
    session.close()
    engine.dispose()


class TestSQLiteAttachDatabases:
    """Verify that ATTACH DATABASE works for all required schemas."""

    def test_core_schema_attached(self):
        engine = _build_engine()
        with engine.connect() as conn:
            result = conn.exec_driver_sql("PRAGMA database_list")
            db_names = [row[1] for row in result]
        assert "core" in db_names
        engine.dispose()

    def test_config_schema_attached(self):
        engine = _build_engine()
        with engine.connect() as conn:
            result = conn.exec_driver_sql("PRAGMA database_list")
            db_names = [row[1] for row in result]
        assert "config" in db_names
        engine.dispose()

    def test_validation_schema_attached(self):
        engine = _build_engine()
        with engine.connect() as conn:
            result = conn.exec_driver_sql("PRAGMA database_list")
            db_names = [row[1] for row in result]
        assert "validation" in db_names
        engine.dispose()


class TestLapTimeUniqueConstraint:
    """Verify the unique constraint on lap_times(race_id, driver, lap)."""

    def test_insert_single_lap(self, db):
        lap = LapTime(race_id="2024-1", driver="VER", lap=1, lap_ms=90000)
        db.add(lap)
        db.commit()
        assert db.query(LapTime).count() == 1

    def test_insert_different_laps_same_driver(self, db):
        db.add(LapTime(race_id="2024-1", driver="VER", lap=1, lap_ms=90000))
        db.add(LapTime(race_id="2024-1", driver="VER", lap=2, lap_ms=90500))
        db.commit()
        assert db.query(LapTime).count() == 2

    def test_insert_same_lap_different_drivers(self, db):
        db.add(LapTime(race_id="2024-1", driver="VER", lap=1, lap_ms=90000))
        db.add(LapTime(race_id="2024-1", driver="HAM", lap=1, lap_ms=91000))
        db.commit()
        assert db.query(LapTime).count() == 2

    def test_insert_same_lap_different_races(self, db):
        db.add(LapTime(race_id="2024-1", driver="VER", lap=1, lap_ms=90000))
        db.add(LapTime(race_id="2024-2", driver="VER", lap=1, lap_ms=89000))
        db.commit()
        assert db.query(LapTime).count() == 2

    def test_duplicate_lap_raises_integrity_error(self, db):
        db.add(LapTime(race_id="2024-1", driver="VER", lap=1, lap_ms=90000))
        db.commit()
        db.add(LapTime(race_id="2024-1", driver="VER", lap=1, lap_ms=91000))
        with pytest.raises(sa.exc.IntegrityError):
            db.commit()

    def test_null_lap_number_allowed(self, db):
        """Laps with NULL lap number should not conflict."""
        db.add(LapTime(race_id="2024-1", driver="VER", lap=None, lap_ms=90000))
        db.add(LapTime(race_id="2024-1", driver="VER", lap=None, lap_ms=91000))
        db.commit()
        assert db.query(LapTime).count() == 2
