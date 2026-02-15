"""
Single source of truth for the SQLAlchemy engine and session factory.
Other modules should *only* import SessionLocal (for ORM sessions) or
engine (for low‑level SQL).
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

from theundercut.config import get_settings

settings = get_settings()
engine = create_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, future=True))


# --- FastAPI-friendly dependency --------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db          # FastAPI receives the actual Session here
    finally:
        db.close()
