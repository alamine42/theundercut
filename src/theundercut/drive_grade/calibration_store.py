"""
Helpers for storing and retrieving calibration profiles from the database.
"""
from __future__ import annotations

import json
import datetime as dt
from pathlib import Path
from typing import Any, Dict

from sqlalchemy import select, update
from sqlalchemy.exc import SQLAlchemyError

from theundercut.adapters.db import SessionLocal
from theundercut.models import CalibrationProfile as CalibrationProfileRow
from .calibration import CalibrationProfile


def fetch_profile_from_db(name: str) -> CalibrationProfile | None:
    """
    Return a calibration profile stored in config.calibration_profiles.
    """
    try:
        with SessionLocal() as session:
            row = (
                session.execute(
                    select(CalibrationProfileRow).where(CalibrationProfileRow.name == name)
                )
                .scalar_one_or_none()
            )
            if not row:
                return None
            payload: Dict[str, Any] = dict(row.body or {})
            payload.setdefault("name", row.name)
            profile = CalibrationProfile.from_dict(payload)
            profile.name = row.name
            return profile
    except SQLAlchemyError:
        return None


def upsert_profile_from_file(
    name: str,
    file_path: Path,
    *,
    activate: bool = False,
) -> CalibrationProfile:
    """
    Import a calibration JSON file into config.calibration_profiles.
    """
    data = json.loads(file_path.read_text())
    profile = CalibrationProfile.from_dict({**data, "name": name})
    now = dt.datetime.utcnow()

    with SessionLocal() as session:
        existing = (
            session.execute(
                select(CalibrationProfileRow).where(CalibrationProfileRow.name == name)
            )
            .scalar_one_or_none()
        )
        if activate:
            session.execute(
                update(CalibrationProfileRow).values(active=False)
            )
        if existing:
            existing.body = data
            existing.version = data.get("version") or existing.version
            existing.updated_at = now
            if activate:
                existing.active = True
        else:
            session.add(
                CalibrationProfileRow(
                    name=name,
                    version=data.get("version") or "v1",
                    active=activate,
                    body=data,
                    created_at=now,
                    updated_at=now,
                )
            )
        session.commit()
    return profile


def set_active_profile(name: str) -> bool:
    """
    Mark a calibration profile as active; returns True if the profile exists.
    """
    with SessionLocal() as session:
        row = (
            session.execute(
                select(CalibrationProfileRow).where(CalibrationProfileRow.name == name)
            )
            .scalar_one_or_none()
        )
        if not row:
            return False
        session.execute(update(CalibrationProfileRow).values(active=False))
        row.active = True
        row.updated_at = dt.datetime.utcnow()
        session.commit()
    return True


__all__ = ["fetch_profile_from_db", "upsert_profile_from_file", "set_active_profile"]
