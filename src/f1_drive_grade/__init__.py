"""
Compatibility package for legacy `f1_drive_grade` imports.

Drive Grade code now lives under `theundercut.drive_grade.*`, but existing
scripts/tests still import `f1_drive_grade`. This shim proxies those modules
so we can migrate gradually without rewriting every consumer.
"""

from __future__ import annotations

import importlib
import sys
from types import ModuleType

_MODULES = {
    "calibration": "theundercut.drive_grade.calibration",
    "car_pace": "theundercut.drive_grade.car_pace",
    "data_loader": "theundercut.drive_grade.data_loader",
    "drive_grade": "theundercut.drive_grade.drive_grade",
    "etl": "theundercut.drive_grade.etl",
    "pipeline": "theundercut.drive_grade.pipeline",
    "season": "theundercut.drive_grade.season",
    "data_sources": "theundercut.drive_grade.data_sources",
}


def _proxy_module(name: str, target_path: str) -> ModuleType:
    target = importlib.import_module(target_path)
    sys.modules[f"f1_drive_grade.{name}"] = target
    return target


for _mod, path in _MODULES.items():
    globals()[_mod] = _proxy_module(_mod, path)

__all__ = list(_MODULES.keys())
