"""Helpers for running Drive Grade across multiple races in a season."""
from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Mapping

from .drive_grade import DriveGradeBreakdown
from .pipeline import DriveGradePipeline
from .data_loader import WeekendTableLoader


def is_preseason_slug(value: str) -> bool:
    """Return True if the provided slug/name refers to pre-season testing."""

    slug = value.lower()
    return "pre-season" in slug or "pre_season" in slug


@dataclass(slots=True)
class DriverSeasonRow:
    driver: str
    races: int
    total_grade: float
    average_grade: float
    average_consistency: float
    average_team_strategy: float
    average_racecraft: float
    average_penalties: float
    average_on_track_events: float
    average_pit_cycle_events: float


@dataclass(slots=True)
class SeasonResults:
    race_results: Dict[str, Dict[str, DriveGradeBreakdown]]
    season_rows: List[DriverSeasonRow]

    def race_rows(self) -> List[Dict[str, float | str]]:
        rows: List[Dict[str, float | str]] = []
        for race, drivers in self.race_results.items():
            for driver, breakdown in drivers.items():
                rows.append(
                    {
                        "race": race,
                        "driver": driver,
                        "consistency": breakdown.consistency_score,
                        "team_strategy": breakdown.team_strategy_score,
                        "racecraft": breakdown.racecraft_score,
                        "penalties": breakdown.penalty_score,
                        "on_track_overtakes": breakdown.on_track_events,
                        "pit_cycle_overtakes": breakdown.pit_cycle_events,
                        "total_grade": breakdown.total_grade,
                    }
                )
        return rows

    def summary_rows(self) -> List[Dict[str, float | str]]:
        return [
            {
                "driver": row.driver,
                "races": row.races,
                "total_grade": row.total_grade,
                "average_grade": row.average_grade,
                "average_consistency": row.average_consistency,
                "average_team_strategy": row.average_team_strategy,
                "average_racecraft": row.average_racecraft,
                "average_penalties": row.average_penalties,
                "average_on_track_events": row.average_on_track_events,
                "average_pit_cycle_events": row.average_pit_cycle_events,
            }
            for row in self.season_rows
        ]


class SeasonRunner:
    """Runs Drive Grade for multiple races and aggregates season-long results."""

    def __init__(self, pipeline: DriveGradePipeline | None = None) -> None:
        self.pipeline = pipeline or DriveGradePipeline()

    def run_race(self, path: Path | str, input_format: str | None = None) -> Dict[str, DriveGradeBreakdown]:
        race_path = Path(path)
        fmt = input_format or ("tables" if race_path.is_dir() else "json")
        if fmt == "json":
            return self.pipeline.run_from_json(race_path)
        loader = WeekendTableLoader(race_path)
        driver_inputs = loader.build_driver_inputs()
        return {driver.driver: self.pipeline.score_driver(driver) for driver in driver_inputs}

    def run_season(self, race_inputs: Mapping[str, Path | str]) -> SeasonResults:
        race_results: Dict[str, Dict[str, DriveGradeBreakdown]] = {}
        for race, location in race_inputs.items():
            slug_hint = race or ""
            path_name = Path(str(location)).stem if Path(str(location)).is_file() else Path(str(location)).name
            if is_preseason_slug(slug_hint) or is_preseason_slug(path_name):
                continue
            race_results[race] = self.run_race(location)
        if not race_results:
            raise RuntimeError("No non-testing races provided to SeasonRunner")
        season_rows = aggregate_season(race_results)
        return SeasonResults(race_results=race_results, season_rows=season_rows)

    def save_outputs(self, results: SeasonResults, output_dir: Path | str) -> None:
        dest = Path(output_dir)
        dest.mkdir(parents=True, exist_ok=True)
        race_rows = results.race_rows()
        season_rows = results.summary_rows()
        if race_rows:
            _write_csv(
                dest / "race_results.csv",
                [
                    "race",
                    "driver",
                    "consistency",
                    "team_strategy",
                    "racecraft",
                    "penalties",
                    "on_track_overtakes",
                    "pit_cycle_overtakes",
                    "total_grade",
                ],
                race_rows,
            )
        if season_rows:
            _write_csv(
                dest / "season_summary.csv",
                [
                    "driver",
                    "races",
                    "total_grade",
                    "average_grade",
                    "average_consistency",
                    "average_team_strategy",
                    "average_racecraft",
                    "average_penalties",
                    "average_on_track_events",
                    "average_pit_cycle_events",
                ],
                season_rows,
            )


def aggregate_season(
    race_results: Mapping[str, Mapping[str, DriveGradeBreakdown]]
) -> List[DriverSeasonRow]:
    aggregates: Dict[str, Dict[str, float]] = {}
    counts: Dict[str, int] = {}

    for drivers in race_results.values():
        for driver, breakdown in drivers.items():
            agg = aggregates.setdefault(
                driver,
                {
                    "total_grade": 0.0,
                    "consistency": 0.0,
                    "team_strategy": 0.0,
                    "racecraft": 0.0,
                    "penalties": 0.0,
                    "on_track": 0.0,
                    "pit_cycle": 0.0,
                },
            )
            counts[driver] = counts.get(driver, 0) + 1
            agg["total_grade"] += breakdown.total_grade
            agg["consistency"] += breakdown.consistency_score
            agg["team_strategy"] += breakdown.team_strategy_score
            agg["racecraft"] += breakdown.racecraft_score
            agg["penalties"] += breakdown.penalty_score
            agg["on_track"] += breakdown.on_track_events
            agg["pit_cycle"] += breakdown.pit_cycle_events

    rows: List[DriverSeasonRow] = []
    for driver, sums in aggregates.items():
        race_count = counts[driver]
        rows.append(
            DriverSeasonRow(
                driver=driver,
                races=race_count,
                total_grade=sums["total_grade"],
                average_grade=sums["total_grade"] / race_count,
                average_consistency=sums["consistency"] / race_count,
                average_team_strategy=sums["team_strategy"] / race_count,
                average_racecraft=sums["racecraft"] / race_count,
                average_penalties=sums["penalties"] / race_count,
                average_on_track_events=sums["on_track"] / race_count,
                average_pit_cycle_events=sums["pit_cycle"] / race_count,
            )
        )
    rows.sort(key=lambda row: row.average_grade, reverse=True)
    return rows


def _write_csv(path: Path, headers: Iterable[str], rows: Iterable[Mapping[str, float | str]]) -> None:
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(headers))
        writer.writeheader()
        writer.writerows(rows)


__all__ = ["SeasonRunner", "SeasonResults", "DriverSeasonRow", "is_preseason_slug"]
