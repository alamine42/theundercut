from sqlalchemy import (
    Column,
    Integer,
    String,
    Boolean,
    DateTime,
    Interval,
    ForeignKey,
    Float,
    JSON,
)
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class CalendarEvent(Base):
    __tablename__ = "calendar_events"
    id           = Column(Integer, primary_key=True)
    season       = Column(Integer, nullable=False)
    round        = Column(Integer, nullable=False)
    session_type = Column(String, nullable=False)        # FP1, Qualifying, Race…
    start_ts     = Column(DateTime(timezone=True))
    end_ts       = Column(DateTime(timezone=True))
    meeting_key  = Column(Integer)                       # OpenF1 join‑key
    status       = Column(String, default="scheduled")   # scheduled | running | ingested

class LapTime(Base):
    __tablename__ = "lap_times"
    id         = Column(Integer, primary_key=True)
    race_id    = Column(String, nullable=False)          # season‑round "2024-5"
    driver     = Column(String(3), nullable=False)
    lap        = Column(Integer)
    lap_ms     = Column(Integer)
    compound   = Column(String(10))
    stint_no   = Column(Integer)
    pit        = Column(Boolean)

class Stint(Base):
    __tablename__ = "stints"
    id        = Column(Integer, primary_key=True)
    race_id   = Column(String, nullable=False)
    driver    = Column(String(3), nullable=False)
    stint_no  = Column(Integer)
    compound  = Column(String(10))
    laps      = Column(Integer)
    avg_lap_ms = Column(Integer)


# --- Drive Grade reference tables -------------------------------------------------

class Season(Base):
    __tablename__ = "seasons"
    __table_args__ = {"schema": "core"}

    id       = Column(Integer, primary_key=True)
    year     = Column(Integer, unique=True, nullable=False)
    status   = Column(String, default="planned")
    created_at = Column(DateTime(timezone=True))


class Circuit(Base):
    __tablename__ = "circuits"
    __table_args__ = {"schema": "core"}

    id       = Column(Integer, primary_key=True)
    name     = Column(String, nullable=False)
    country  = Column(String)
    latitude = Column(Float)
    longitude = Column(Float)


class Team(Base):
    __tablename__ = "teams"
    __table_args__ = {"schema": "core"}

    id        = Column(Integer, primary_key=True)
    name      = Column(String, nullable=False, unique=True)
    power_unit = Column(String)
    country   = Column(String)


class Driver(Base):
    __tablename__ = "drivers"
    __table_args__ = {"schema": "core"}

    id          = Column(Integer, primary_key=True)
    code        = Column(String(3), unique=True, nullable=False)
    given_name  = Column(String)
    family_name = Column(String)
    country     = Column(String)


class Race(Base):
    __tablename__ = "races"
    __table_args__ = {"schema": "core"}

    id          = Column(Integer, primary_key=True)
    season_id   = Column(Integer, ForeignKey("core.seasons.id"), nullable=False)
    circuit_id  = Column(Integer, ForeignKey("core.circuits.id"))
    round_number = Column(Integer, nullable=False)
    slug        = Column(String, unique=True, nullable=False)
    session_type = Column(String(2), default="R")
    start_time  = Column(DateTime(timezone=True))


class Entry(Base):
    __tablename__ = "entries"
    __table_args__ = {"schema": "core"}

    id           = Column(Integer, primary_key=True)
    race_id      = Column(Integer, ForeignKey("core.races.id"), nullable=False)
    driver_id    = Column(Integer, ForeignKey("core.drivers.id"), nullable=False)
    team_id      = Column(Integer, ForeignKey("core.teams.id"), nullable=False)
    car_number   = Column(Integer)
    grid_position = Column(Integer)
    finish_position = Column(Integer)
    status       = Column(String)


class DriverMetrics(Base):
    __tablename__ = "driver_metrics"
    __table_args__ = {"schema": "core"}

    id              = Column(Integer, primary_key=True)
    entry_id        = Column(Integer, ForeignKey("core.entries.id"), unique=True, nullable=False)
    calibration_profile = Column(String)
    data_source     = Column(String)
    consistency_raw = Column(Float)
    consistency_score = Column(Float)
    team_strategy_raw = Column(Float)
    team_strategy_score = Column(Float)
    racecraft_raw   = Column(Float)
    racecraft_score = Column(Float)
    penalties_raw   = Column(Float)
    penalty_score   = Column(Float)
    total_grade     = Column(Float)
    created_at      = Column(DateTime(timezone=True))


class StrategyEvent(Base):
    __tablename__ = "strategy_events"
    __table_args__ = {"schema": "core"}

    id          = Column(Integer, primary_key=True)
    entry_id    = Column(Integer, ForeignKey("core.entries.id"), nullable=False)
    planned_lap = Column(Integer)
    executed_lap = Column(Integer)
    compound_in  = Column(String(10))
    compound_out = Column(String(10))
    stop_time    = Column(Float)
    degradation_penalty = Column(Float)


class PenaltyEvent(Base):
    __tablename__ = "penalty_events"
    __table_args__ = {"schema": "core"}

    id              = Column(Integer, primary_key=True)
    entry_id        = Column(Integer, ForeignKey("core.entries.id"), nullable=False)
    penalty_type    = Column(String)
    time_loss_seconds = Column(Float)
    source          = Column(String)
    lap_number      = Column(Integer)
    notes           = Column(String)


class OvertakeEvent(Base):
    __tablename__ = "overtake_events"
    __table_args__ = {"schema": "core"}

    id               = Column(Integer, primary_key=True)
    entry_id         = Column(Integer, ForeignKey("core.entries.id"), nullable=False)
    opponent_entry_id = Column(Integer, ForeignKey("core.entries.id"))
    lap_number       = Column(Integer)
    success          = Column(Boolean)
    penalized        = Column(Boolean)
    exposure_time    = Column(Float)
    delta_cpi        = Column(Float)
    tire_delta       = Column(Float)
    tire_compound_diff = Column(String(10))
    ers_delta        = Column(Float)
    track_difficulty = Column(Float)
    race_phase_pressure = Column(Float)
    event_type       = Column(String)
    event_source     = Column(String)


class CalibrationProfile(Base):
    __tablename__ = "calibration_profiles"
    __table_args__ = {"schema": "config"}

    id          = Column(Integer, primary_key=True)
    name        = Column(String, nullable=False, unique=True)
    version     = Column(String, default="v1")
    active      = Column(Boolean, default=False)
    body        = Column(JSON, nullable=False)
    created_at  = Column(DateTime(timezone=True))
    updated_at  = Column(DateTime(timezone=True))


class ExternalRanking(Base):
    __tablename__ = "external_rankings"
    __table_args__ = {"schema": "validation"}

    id          = Column(Integer, primary_key=True)
    season      = Column(Integer, nullable=False)
    round       = Column(Integer, nullable=False)
    source      = Column(String, nullable=False)
    driver_code = Column(String(3), nullable=False)
    rank        = Column(Integer, nullable=False)
    score       = Column(Float)
    source_url  = Column(String)
    captured_at = Column(DateTime(timezone=True))


class ValidationMetric(Base):
    __tablename__ = "validation_metrics"
    __table_args__ = {"schema": "validation"}

    id          = Column(Integer, primary_key=True)
    season      = Column(Integer, nullable=False)
    round       = Column(Integer, nullable=False)
    source      = Column(String, nullable=False)
    metric_name = Column(String, nullable=False)
    metric_value = Column(Float)
    created_at  = Column(DateTime(timezone=True))
