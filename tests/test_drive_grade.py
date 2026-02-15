from f1_drive_grade.drive_grade import (
    DriveGradeCalculator,
    DriveGradeBreakdown,
    OvertakeContext,
    OvertakeEvent,
)


def make_event(success: bool = True) -> OvertakeEvent:
    ctx = OvertakeContext(
        delta_cpi=0.0,
        tire_delta=0,
        tire_compound_diff=0,
        ers_delta=0.0,
        track_difficulty=0.5,
        race_phase_pressure=0.5,
    )
    return OvertakeEvent(context=ctx, success=success, exposure_time=10)


def test_breakdown_total_grade_runs() -> None:
    calc = DriveGradeCalculator()
    breakdown = calc.build_breakdown(
        consistency=0.55,
        strategy=0.52,
        penalties=0.1,
        events=[make_event(), make_event(success=False)],
        on_track_events=2,
        pit_cycle_events=0,
    )
    assert isinstance(breakdown, DriveGradeBreakdown)
    assert 0 <= breakdown.total_grade <= 1
