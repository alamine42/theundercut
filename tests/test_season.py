from pathlib import Path
import shutil

from f1_drive_grade.season import SeasonRunner, is_preseason_slug


def sample_race_dirs(tmp_path: Path) -> dict[str, Path]:
    base = Path(__file__).resolve().parents[1] / "data" / "examples" / "sample_weekend_tables"
    races = {}
    for idx in range(2):
        dest = tmp_path / f"race_{idx}"
        shutil.copytree(base, dest)
        races[f"round_{idx+1}"] = dest
    return races


def test_season_runner_aggregates_average(tmp_path: Path) -> None:
    races = sample_race_dirs(tmp_path)
    runner = SeasonRunner()
    results = runner.run_season(races)
    assert len(results.race_results) == 2
    summary = results.summary_rows()
    assert summary
    # same dataset repeated twice -> average grade equals single-race grade
    baseline_total = next(iter(results.race_results.values()))["A. Leader"].total_grade
    leader_row = next(row for row in summary if row["driver"] == "A. Leader")
    assert abs(leader_row["average_grade"] - baseline_total) < 1e-9
    assert leader_row["races"] == 2


def test_season_runner_skips_preseason(tmp_path: Path) -> None:
    base = Path(__file__).resolve().parents[1] / "data" / "examples" / "sample_weekend_tables"
    regular = tmp_path / "01_sample_race"
    preseason = tmp_path / "00_pre-season_testing"
    shutil.copytree(base, regular)
    shutil.copytree(base, preseason)
    races = {
        regular.name: regular,
        preseason.name: preseason,
    }
    runner = SeasonRunner()
    results = runner.run_season(races)
    assert regular.name in results.race_results
    assert preseason.name not in results.race_results
    assert all(preseason.name not in race for race in results.race_results)
    summary = results.summary_rows()
    assert summary  # still has data from non-testing race


def test_is_preseason_slug_detects_variants() -> None:
    assert is_preseason_slug("00_pre-season_testing")
    assert is_preseason_slug("pre_season_trial")
    assert not is_preseason_slug("01_bahrain_grand_prix")
