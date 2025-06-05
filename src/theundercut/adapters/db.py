"""
Single source of truth for the SQLAlchemy engine and session factory.
Other modules should *only* import SessionLocal (for ORM sessions) or
engine (for low‑level SQL).
"""

import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, scoped_session

DATABASE_URL = os.getenv("DATABASE_URL")

if not DATABASE_URL:
    raise ValueError(
        "DATABASE_URL environment variable is not set. "
        "Please set it to connect to the database."
    )

engine = create_engine(DATABASE_URL, pool_pre_ping=True, future=True)
SessionLocal = scoped_session(sessionmaker(bind=engine, autoflush=False, future=True))


# --- FastAPI-friendly dependency --------------------------------------------
def get_db():
    db = SessionLocal()
    try:
        yield db          # FastAPI receives the actual Session here
    finally:
        db.close()