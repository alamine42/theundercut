from pathlib import Path

from f1_drive_grade.pipeline import (
    DriveGradePipeline,
    compute_consistency_score,
    compute_penalty_score,
    compute_strategy_score,
    load_weekend_file,
    StrategyPlan,
    PenaltyEvent,
)


def repo_path() -> Path:
    return Path(__file__).resolve().parents[1]


def test_consistency_score_rewards_alignment() -> None:
    score = compute_consistency_score(
        lap_deltas=[-0.31, -0.3, -0.33, -0.29],
        expected_delta=-0.3,
        actual_pit_laps=[15],
    )
    assert score > 0.8


def test_strategy_score_penalizes_large_deviation() -> None:
    tight_plan = StrategyPlan(optimal_pit_laps=[15, 40], actual_pit_laps=[15, 41], degradation_penalty=0.1)
    loose_plan = StrategyPlan(optimal_pit_laps=[15, 40], actual_pit_laps=[20, 48], degradation_penalty=0.1)
    assert compute_strategy_score(tight_plan) > compute_strategy_score(loose_plan)


def test_penalty_score_accumulates_time_loss() -> None:
    low = compute_penalty_score([PenaltyEvent(type="lockup", time_loss=2.0)])
    high = compute_penalty_score([PenaltyEvent(type="lockup", time_loss=10.0)])
    assert low < high <= 1.0


def test_pipeline_runs_on_sample_weekend() -> None:
    sample_path = repo_path() / "data" / "examples" / "sample_weekend.json"
    drivers = load_weekend_file(sample_path)
    assert len(drivers) == 2

    pipeline = DriveGradePipeline()
    results = pipeline.run_from_json(sample_path)
    assert set(results.keys()) == {"A. Leader", "B. Chaser"}
    assert results["B. Chaser"].total_grade > results["A. Leader"].total_grade
