import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from theundercut.models import Base, LapTime, Stint


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
def session_factory():
    engine = _build_engine()
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        conn.execute(sa.text(
            "CREATE UNIQUE INDEX IF NOT EXISTS uq_lap_race_driver_lap ON lap_times (race_id, driver, lap)"
        ))
    SessionLocal = sessionmaker(bind=engine, future=True)

    yield SessionLocal

    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture()
def db_session(session_factory):
    session = session_factory()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


def seed_sample_race(session, season=2024, rnd=1):
    race_id = f"{season}-{rnd}"
    laps = [
        LapTime(race_id=race_id, driver="VER", lap=1, lap_ms=90000, compound="MED", stint_no=1, pit=False),
        LapTime(race_id=race_id, driver="VER", lap=2, lap_ms=90500, compound="MED", stint_no=1, pit=False),
        LapTime(race_id=race_id, driver="HAM", lap=1, lap_ms=91000, compound="MED", stint_no=1, pit=False),
        LapTime(race_id=race_id, driver="HAM", lap=2, lap_ms=92000, compound="HARD", stint_no=2, pit=True),
    ]
    stints = [
        Stint(race_id=race_id, driver="VER", stint_no=1, compound="MED", laps=18, avg_lap_ms=90250),
        Stint(race_id=race_id, driver="HAM", stint_no=1, compound="MED", laps=20, avg_lap_ms=91500),
    ]
    session.add_all(laps + stints)
    session.commit()
    return race_id


__all__ = ["seed_sample_race"]
import os
from pathlib import Path

@pytest.fixture(autouse=True)
def _fastf1_cache(tmp_path, monkeypatch):
    cache_dir = tmp_path / "fastf1_cache"
    cache_dir.mkdir(parents=True, exist_ok=True)
    monkeypatch.setenv("FASTF1_CACHE_DIR", str(cache_dir))
    yield
    monkeypatch.delenv("FASTF1_CACHE_DIR", raising=False)

@pytest.fixture()
def db_session_factory(session_factory):
    return session_factory
