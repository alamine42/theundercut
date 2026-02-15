from pathlib import Path

import pandas as pd
import pandas.testing as pdt

from f1_drive_grade.etl import (
    load_driver_inputs_from_json,
    build_tables,
)


def sample_json() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "examples" / "sample_weekend.json"


def sample_tables_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "examples" / "sample_weekend_tables"


def test_build_tables_matches_sample_artifacts() -> None:
    drivers = load_driver_inputs_from_json(sample_json())
    tables = build_tables(drivers)

    for name, frame in tables.items():
        expected_path = sample_tables_dir() / f"{name}.csv"
        expected = pd.read_csv(expected_path)
        frame = frame.reset_index(drop=True)
        expected = expected.reset_index(drop=True)
        frame = frame.where(pd.notna(frame), None)
        expected = expected.where(pd.notna(expected), None)
        pdt.assert_frame_equal(frame, expected, check_dtype=False)
