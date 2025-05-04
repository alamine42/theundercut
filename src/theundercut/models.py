from sqlalchemy import Column, Integer, String, Boolean, DateTime, Interval, ForeignKey
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
