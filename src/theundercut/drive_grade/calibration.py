"""Loading and managing Drive Grade calibration profiles."""
from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


DEFAULT_PROFILE_NAME = "baseline"
DEFAULT_CONFIG_DIR = Path(__file__).resolve().parents[2] / "configs" / "calibration"


@dataclass(slots=True)
class CalibrationProfile:
    """Tunables controlling component tolerances."""

    name: str = DEFAULT_PROFILE_NAME
    consistency_tolerance: float = 4.1
    pace_advantage_scale: float = 3.0
    pace_boost_cap: float = 0.25
    pace_min_advantage: float = 0.2
    stint_target_laps: float = 15.0
    stint_boost_cap: float = 0.35
    strategy_lap_tolerance: float = 6.0
    penalty_normalizer: float = 12.0

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "CalibrationProfile":
        defaults = cls()
        payload = {field: data.get(field, getattr(defaults, field)) for field in cls.__dataclass_fields__}
        return cls(**payload)


_ACTIVE_PROFILE: CalibrationProfile | None = None


def _profile_path(profile: str) -> Path:
    config_dir = Path(os.getenv("DRIVE_GRADE_CALIBRATION_DIR", DEFAULT_CONFIG_DIR))
    candidate = Path(profile)
    if candidate.exists():
        return candidate
    return config_dir / f"{profile}.json"


def _load_from_db(profile_name: str) -> Optional[CalibrationProfile]:
    try:
        from .calibration_store import fetch_profile_from_db
    except Exception:
        return None
    return fetch_profile_from_db(profile_name)


def load_calibration_profile(profile: str | None = None) -> CalibrationProfile:
    profile_name = profile or os.getenv("DRIVE_GRADE_CALIBRATION_PROFILE", DEFAULT_PROFILE_NAME)
    from_db = _load_from_db(profile_name)
    if from_db is not None:
        return from_db
    path = _profile_path(profile_name)
    if not path.exists():
        return CalibrationProfile(name=profile_name)
    data = json.loads(path.read_text())
    if "name" not in data:
        data["name"] = profile_name
    return CalibrationProfile.from_dict(data)


def get_active_calibration() -> CalibrationProfile:
    global _ACTIVE_PROFILE
    if _ACTIVE_PROFILE is None:
        _ACTIVE_PROFILE = load_calibration_profile()
    return _ACTIVE_PROFILE


def set_active_calibration(profile: CalibrationProfile) -> None:
    global _ACTIVE_PROFILE
    _ACTIVE_PROFILE = profile


__all__ = [
    "CalibrationProfile",
    "get_active_calibration",
    "load_calibration_profile",
    "set_active_calibration",
]
