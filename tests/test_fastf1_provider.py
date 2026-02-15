from datetime import timedelta

import pandas as pd

from f1_drive_grade.data_sources.fastf1_provider import (
    compute_lap_deltas,
    derive_form_metrics,
    slugify,
)


def make_laps() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "LapTime": pd.Series([
                timedelta(seconds=90),
                timedelta(seconds=91),
                timedelta(seconds=92),
            ])
        }
    )


def test_compute_lap_deltas_centers_on_median() -> None:
    laps = make_laps()
    deltas = compute_lap_deltas(laps)
    assert len(deltas) == 3
    assert abs(sum(deltas)) < 1e-9  # centered around zero
    assert min(deltas) < 0 < max(deltas)


def test_derive_form_metrics_bounds_scores() -> None:
    metrics = derive_form_metrics([-0.5, 0.1, 0.2], grid=6, position=2)
    assert 0 <= metrics["consistency"] <= 1
    assert metrics["start_precision"] > 0.5


def test_slugify_removes_special_chars() -> None:
    assert slugify("Las Vegas GP (Night)") == "las_vegas_gp_night"
