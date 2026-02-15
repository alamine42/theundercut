from pathlib import Path
import shutil

import pandas as pd
import pytest

from f1_drive_grade.data_loader import WeekendTableLoader, TableValidationError
from f1_drive_grade.pipeline import DriveGradePipeline


def data_dir() -> Path:
    return Path(__file__).resolve().parents[1] / "data" / "examples"


def copy_sample_tables(tmp_path: Path) -> Path:
    dest = tmp_path / "tables"
    shutil.copytree(data_dir() / "sample_weekend_tables", dest)
    return dest


def test_weekend_table_loader_parses_all_drivers() -> None:
    loader = WeekendTableLoader(data_dir() / "sample_weekend_tables")
    driver_inputs = loader.build_driver_inputs()
    assert len(driver_inputs) == 2
    assert {driver.driver for driver in driver_inputs} == {"A. Leader", "B. Chaser"}


def test_tables_pipeline_matches_json_results() -> None:
    base = data_dir()
    loader = WeekendTableLoader(base / "sample_weekend_tables")
    inputs = loader.build_driver_inputs()

    pipeline = DriveGradePipeline()
    table_results = {driver.driver: pipeline.score_driver(driver) for driver in inputs}
    json_results = pipeline.run_from_json(base / "sample_weekend.json")

    for driver in json_results:
        assert driver in table_results
        assert abs(table_results[driver].total_grade - json_results[driver].total_grade) < 1e-9


def test_loader_errors_on_missing_columns(tmp_path: Path) -> None:
    tables_dir = copy_sample_tables(tmp_path)
    telemetry_path = tables_dir / "telemetry.csv"
    df = pd.read_csv(telemetry_path)
    df = df.drop(columns=["lap_delta"])
    df.to_csv(telemetry_path, index=False)

    loader = WeekendTableLoader(tables_dir)
    with pytest.raises(TableValidationError, match="telemetry.*missing columns"):
        loader.load_tables()


def test_loader_errors_on_mismatched_pit_lists(tmp_path: Path) -> None:
    tables_dir = copy_sample_tables(tmp_path)
    strategy_path = tables_dir / "strategy.csv"
    df = pd.read_csv(strategy_path)
    df.loc[df["driver"] == "A. Leader", "actual_pits"] = "16"
    df.to_csv(strategy_path, index=False)

    loader = WeekendTableLoader(tables_dir)
    with pytest.raises(TableValidationError, match="Strategy plan mismatch"):
        loader.build_driver_inputs()
