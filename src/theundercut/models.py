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
    Date,
    UniqueConstraint,
    Index,
)
from sqlalchemy.orm import declarative_base, relationship

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


# --- Pre-Season Testing tables ---------------------------------------------------

class TestingEvent(Base):
    """Pre-season or in-season testing event (e.g., Bahrain 2025 testing)."""
    __tablename__ = "testing_events"
    __table_args__ = (
        UniqueConstraint("season", "event_id", name="uq_testing_event"),
        Index("ix_testing_event_lookup", "season", "event_id"),
    )

    id         = Column(Integer, primary_key=True)
    season     = Column(Integer, nullable=False, index=True)
    event_id   = Column(String(50), nullable=False)  # e.g., "pre_season_2025"
    event_name = Column(String(100), nullable=False)  # e.g., "Pre-Season Testing"
    circuit_id = Column(String(50), nullable=False)  # e.g., "bahrain"
    total_days = Column(Integer, default=3)
    start_date = Column(Date)
    end_date   = Column(Date)
    status     = Column(String(20), default="scheduled")  # scheduled | running | completed

    sessions = relationship("TestingSession", back_populates="event", cascade="all, delete-orphan")


class TestingSession(Base):
    """Single day of a testing event."""
    __tablename__ = "testing_sessions"
    __table_args__ = (
        UniqueConstraint("event_id", "day", name="uq_testing_session"),
    )

    id       = Column(Integer, primary_key=True)
    event_id = Column(Integer, ForeignKey("testing_events.id"), nullable=False)
    day      = Column(Integer, nullable=False)  # 1, 2, or 3
    date     = Column(Date)
    status   = Column(String(20), default="scheduled")  # scheduled | running | completed

    event  = relationship("TestingEvent", back_populates="sessions")
    laps   = relationship("TestingLap", back_populates="session", cascade="all, delete-orphan")
    stints = relationship("TestingStint", back_populates="session", cascade="all, delete-orphan")


class TestingLap(Base):
    """Individual lap from a testing session."""
    __tablename__ = "testing_laps"
    __table_args__ = (
        UniqueConstraint("session_id", "driver", "lap_number", name="uq_testing_lap"),
        Index("ix_testing_lap_driver", "session_id", "driver"),
    )

    id          = Column(Integer, primary_key=True)
    session_id  = Column(Integer, ForeignKey("testing_sessions.id"), nullable=False)
    driver      = Column(String(3), nullable=False)  # Driver code (e.g., "VER")
    team        = Column(String(50))  # Team name
    lap_number  = Column(Integer, nullable=False)
    lap_time_ms = Column(Float)  # Lap time in milliseconds
    compound    = Column(String(20))  # Tire compound (SOFT, MEDIUM, HARD, etc.)
    stint_number = Column(Integer)
    sector_1_ms = Column(Float)
    sector_2_ms = Column(Float)
    sector_3_ms = Column(Float)
    is_valid    = Column(Boolean, default=True)  # Valid lap (no track limits, etc.)

    session = relationship("TestingSession", back_populates="laps")


class TestingStint(Base):
    """Aggregated stint from a testing session."""
    __tablename__ = "testing_stints"
    __table_args__ = (
        UniqueConstraint("session_id", "driver", "stint_number", name="uq_testing_stint"),
    )

    id           = Column(Integer, primary_key=True)
    session_id   = Column(Integer, ForeignKey("testing_sessions.id"), nullable=False)
    driver       = Column(String(3), nullable=False)
    team         = Column(String(50))
    stint_number = Column(Integer, nullable=False)
    compound     = Column(String(20))
    start_lap    = Column(Integer)
    end_lap      = Column(Integer)
    lap_count    = Column(Integer)
    avg_pace_ms  = Column(Float)  # Average lap time in milliseconds

    session = relationship("TestingSession", back_populates="stints")


# --- Race Weekend Widget tables --------------------------------------------------

class SessionClassification(Base):
    """Condensed session results for all session types (FP1-3, Quali, Sprint, Race).

    Used by the Race Weekend Widget to display session results from a single source
    of truth (Postgres) rather than fetching from external APIs on each request.
    """
    __tablename__ = "session_classifications"
    __table_args__ = (
        UniqueConstraint("season", "round", "session_type", "driver_code", name="uq_session_classification"),
        Index("ix_session_classification_lookup", "season", "round", "session_type"),
    )

    id            = Column(Integer, primary_key=True)
    season        = Column(Integer, nullable=False)
    round         = Column(Integer, nullable=False)
    session_type  = Column(String(20), nullable=False)  # fp1, fp2, fp3, qualifying, sprint_qualifying, sprint_race, race
    driver_code   = Column(String(3), nullable=False)
    driver_name   = Column(String(100))
    team          = Column(String(50))
    position      = Column(Integer)
    time_ms       = Column(Float)   # Best lap time (practice) or classified time (race)
    gap_ms        = Column(Float)   # Gap to leader
    laps          = Column(Integer)
    points        = Column(Integer) # For race/sprint sessions
    # Qualifying-specific fields
    q1_time_ms    = Column(Float)
    q2_time_ms    = Column(Float)
    q3_time_ms    = Column(Float)
    eliminated_in = Column(String(5))  # Q1, Q2, or null
    # Metadata
    ingested_at   = Column(DateTime(timezone=True))
    amended       = Column(Boolean, default=False)  # True if post-race penalty changed classification


# --- Enhanced Strategy Score tables -----------------------------------------------

class StrategyScore(Base):
    """Enhanced strategy score per driver per race.

    Stores comprehensive strategy evaluation with component sub-scores
    for pit timing, tire selection, safety car response, and weather calls.
    Linked to Entry for referential integrity.
    """
    __tablename__ = "strategy_scores"
    __table_args__ = {"schema": "core"}

    id                   = Column(Integer, primary_key=True)
    entry_id             = Column(Integer, ForeignKey("core.entries.id"), unique=True, nullable=False)

    # Component scores (0-100)
    total_score          = Column(Float, nullable=False)
    pit_timing_score     = Column(Float, nullable=False)
    tire_selection_score = Column(Float, nullable=False)
    safety_car_score     = Column(Float, nullable=False)
    weather_score        = Column(Float, nullable=False)

    # Metadata for recomputation
    calibration_profile  = Column(String(50), nullable=False)
    calibration_version  = Column(String(20), nullable=False)
    computed_at          = Column(DateTime(timezone=True))

    # Relationships
    decisions = relationship("StrategyDecision", back_populates="strategy_score", cascade="all, delete-orphan")


class StrategyDecision(Base):
    """Individual strategic decision with impact assessment and explanation.

    Provides explainability for strategy scores by logging each decision
    with its impact on race outcome.
    """
    __tablename__ = "strategy_decisions"
    __table_args__ = (
        Index("ix_strategy_decision_score", "strategy_score_id"),
        {"schema": "core"},
    )

    id                 = Column(Integer, primary_key=True)
    strategy_score_id  = Column(Integer, ForeignKey("core.strategy_scores.id", ondelete="CASCADE"), nullable=False)

    # Decision context
    lap_number         = Column(Integer, nullable=False)
    decision_type      = Column(String(50), nullable=False)  # pit_stop, stay_out, tire_change, compound_choice, etc.
    factor             = Column(String(20), nullable=False)  # pit_timing, tire_selection, safety_car, weather

    # Impact assessment
    impact_score       = Column(Float, nullable=False)       # Positive = good, negative = bad
    position_delta     = Column(Integer)                     # Positions gained/lost
    time_delta_ms      = Column(Integer)                     # Time gained/lost in milliseconds

    # Explainability
    explanation        = Column(String, nullable=False)      # Human-readable explanation
    comparison_context = Column(String)                      # What peers did, simulation alternative

    created_at         = Column(DateTime(timezone=True))

    # Relationships
    strategy_score = relationship("StrategyScore", back_populates="decisions")


class RaceControlEvent(Base):
    """Safety Car, VSC, and Red Flag periods during a race.

    Required for SafetyCar scorer to evaluate strategic decisions
    during neutralization periods.
    """
    __tablename__ = "race_control_events"
    __table_args__ = (
        UniqueConstraint("race_id", "event_type", "start_lap", name="uq_race_control_event"),
        Index("ix_race_control_event_race", "race_id"),
        {"schema": "core"},
    )

    id         = Column(Integer, primary_key=True)
    race_id    = Column(Integer, ForeignKey("core.races.id"), nullable=False)

    event_type = Column(String(20), nullable=False)   # safety_car, vsc, red_flag
    start_lap  = Column(Integer, nullable=False)
    end_lap    = Column(Integer)                       # NULL if race ends under SC
    start_time = Column(DateTime(timezone=True))
    end_time   = Column(DateTime(timezone=True))
    cause      = Column(String)                        # Incident description if available


class RaceWeather(Base):
    """Per-lap weather conditions during a race.

    Required for Weather scorer to evaluate tire compound decisions
    relative to track conditions.
    """
    __tablename__ = "race_weather"
    __table_args__ = (
        UniqueConstraint("race_id", "lap_number", name="uq_race_weather"),
        Index("ix_race_weather_race", "race_id"),
        {"schema": "core"},
    )

    id             = Column(Integer, primary_key=True)
    race_id        = Column(Integer, ForeignKey("core.races.id"), nullable=False)
    lap_number     = Column(Integer, nullable=False)

    track_status   = Column(String(20), nullable=False)  # dry, damp, wet
    air_temp_c     = Column(Float)
    track_temp_c   = Column(Float)
    humidity_pct   = Column(Float)
    rain_intensity = Column(String(20))                   # none, light, moderate, heavy


class LapPosition(Base):
    """Per-lap position snapshots for position delta analysis.

    Required for Position Delta Analyzer and Pit Timing Scorer
    to track positions gained/lost around strategic decisions.
    """
    __tablename__ = "lap_positions"
    __table_args__ = (
        UniqueConstraint("race_id", "entry_id", "lap_number", name="uq_lap_position"),
        Index("ix_lap_position_race_lap", "race_id", "lap_number"),
        {"schema": "core"},
    )

    id              = Column(Integer, primary_key=True)
    race_id         = Column(Integer, ForeignKey("core.races.id"), nullable=False)
    entry_id        = Column(Integer, ForeignKey("core.entries.id"), nullable=False)
    lap_number      = Column(Integer, nullable=False)

    position        = Column(Integer, nullable=False)    # Race position at end of lap
    gap_to_leader_ms = Column(Integer)                   # Gap to P1 in milliseconds
    gap_to_ahead_ms  = Column(Integer)                   # Gap to car ahead
