# src/theundercut/api/v1/race.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from theundercut.adapters.db import get_db
from theundercut.models import LapTime

router = APIRouter(
    prefix="/api/v1/race",
    tags=["race"],
    responses={404: {"description": "Race not found"}},
)

@router.get("/{season}/{round}/laps")
def get_laps(
    season: int,
    round: int,
    drivers: list[str] = Query(
        default=None,
        description="Optional list of driver codes (e.g. VER, HAM) to filter laps",
    ),
    db: Session = Depends(get_db),
):
    """
    Return lap-time records for a given race.

    Parameters
    ----------
    season : int
        Championship year (e.g., 2024)
    round : int
        FIA round number within that season
    drivers : list[str], optional
        One or more driver codes to filter; if omitted, returns all drivers

    Returns
    -------
    list[dict]
        Each item: {driver, lap, lap_ms}
    """
    q = (
        db.query(LapTime.driver, LapTime.lap, LapTime.lap_ms)
        .filter(LapTime.race_id == f"{season}-{round}")
    )
    if drivers:
        q = q.filter(LapTime.driver.in_(drivers))

    rows = (
        q.order_by(LapTime.driver, LapTime.lap)
        .all()
    )

    return [
        {"driver": d, "lap": int(l), "lap_ms": float(ms)}
        for d, l, ms in rows
    ]
