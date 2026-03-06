# src/theundercut/api/v1/strategy.py
"""Strategy Score API endpoints."""

from __future__ import annotations

import json
from typing import Optional, List

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy.orm import Session

from theundercut.adapters.db import get_db
from theundercut.adapters.redis_cache import redis_client
from theundercut.models import (
    StrategyScore,
    StrategyDecision,
    Entry,
    Race,
    Season,
    Driver,
)

CACHE_TTL_SECONDS = 300


# --- Pydantic models for responses ---

class StrategyDecisionResponse(BaseModel):
    lap_number: int
    decision_type: str
    factor: str
    impact_score: float
    position_delta: Optional[int] = None
    time_delta_ms: Optional[int] = None
    explanation: str
    comparison_context: Optional[str] = None


class DriverStrategyScore(BaseModel):
    driver_code: str
    total_score: float
    pit_timing_score: float
    tire_selection_score: float
    safety_car_score: float
    weather_score: float
    calibration_profile: str
    calibration_version: str
    decisions: Optional[List[StrategyDecisionResponse]] = None


class RaceStrategyScoresResponse(BaseModel):
    season: int
    round: int
    scores: List[DriverStrategyScore]


class DriverStrategyDetailResponse(BaseModel):
    season: int
    round: int
    driver_code: str
    score: DriverStrategyScore


router = APIRouter(
    prefix="/api/v1/strategy",
    tags=["strategy"],
    responses={404: {"description": "Not found"}},
)


def _strategy_cache_key(season: int, rnd: int, driver: Optional[str] = None) -> str:
    if driver:
        return f"strategy:{season}:{rnd}:{driver.upper()}"
    return f"strategy:{season}:{rnd}"


@router.get("/{season}/{round}", response_model=RaceStrategyScoresResponse)
def get_race_strategy_scores(
    season: int,
    round: int,
    include_decisions: bool = Query(
        default=False,
        description="Include individual decision records in response",
    ),
    db: Session = Depends(get_db),
):
    """
    Get strategy scores for all drivers in a race.

    Parameters
    ----------
    season : int
        Championship year (e.g., 2024)
    round : int
        FIA round number within that season
    include_decisions : bool
        If True, include decision records for each driver

    Returns
    -------
    RaceStrategyScoresResponse
        Strategy scores for all drivers in the race
    """
    cache_key = _strategy_cache_key(season, round)
    if not include_decisions:
        cached = redis_client.get(cache_key)
        if cached:
            return json.loads(cached)

    # Get race
    race = (
        db.query(Race)
        .join(Season, Race.season_id == Season.id)
        .filter(Season.year == season, Race.round_number == round)
        .first()
    )

    if not race:
        raise HTTPException(status_code=404, detail=f"Race not found for {season} round {round}")

    # Get all entries with strategy scores
    entries_with_scores = (
        db.query(Entry, StrategyScore, Driver)
        .join(StrategyScore, Entry.id == StrategyScore.entry_id)
        .join(Driver, Entry.driver_id == Driver.id)
        .filter(Entry.race_id == race.id)
        .order_by(StrategyScore.total_score.desc())
        .all()
    )

    if not entries_with_scores:
        raise HTTPException(
            status_code=404,
            detail=f"No strategy scores found for {season} round {round}. Scores may not have been computed yet.",
        )

    scores = []
    for entry, strategy_score, driver in entries_with_scores:
        decisions = None
        if include_decisions:
            decision_records = (
                db.query(StrategyDecision)
                .filter(StrategyDecision.strategy_score_id == strategy_score.id)
                .order_by(StrategyDecision.lap_number)
                .all()
            )
            decisions = [
                StrategyDecisionResponse(
                    lap_number=d.lap_number,
                    decision_type=d.decision_type,
                    factor=d.factor,
                    impact_score=d.impact_score,
                    position_delta=d.position_delta,
                    time_delta_ms=d.time_delta_ms,
                    explanation=d.explanation,
                    comparison_context=d.comparison_context,
                )
                for d in decision_records
            ]

        scores.append(DriverStrategyScore(
            driver_code=driver.code,
            total_score=strategy_score.total_score,
            pit_timing_score=strategy_score.pit_timing_score,
            tire_selection_score=strategy_score.tire_selection_score,
            safety_car_score=strategy_score.safety_car_score,
            weather_score=strategy_score.weather_score,
            calibration_profile=strategy_score.calibration_profile,
            calibration_version=strategy_score.calibration_version,
            decisions=decisions,
        ))

    response = RaceStrategyScoresResponse(
        season=season,
        round=round,
        scores=scores,
    )

    # Cache only if decisions not included (simpler cache)
    if not include_decisions:
        redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(response.model_dump()))

    return response


@router.get("/{season}/{round}/{driver}", response_model=DriverStrategyDetailResponse)
def get_driver_strategy_score(
    season: int,
    round: int,
    driver: str,
    db: Session = Depends(get_db),
):
    """
    Get detailed strategy score for a specific driver in a race.

    Parameters
    ----------
    season : int
        Championship year (e.g., 2024)
    round : int
        FIA round number within that season
    driver : str
        Driver code (e.g., VER, HAM)

    Returns
    -------
    DriverStrategyDetailResponse
        Detailed strategy score with all decisions
    """
    driver_code = driver.upper()
    cache_key = _strategy_cache_key(season, round, driver_code)
    cached = redis_client.get(cache_key)
    if cached:
        return json.loads(cached)

    # Get race
    race = (
        db.query(Race)
        .join(Season, Race.season_id == Season.id)
        .filter(Season.year == season, Race.round_number == round)
        .first()
    )

    if not race:
        raise HTTPException(status_code=404, detail=f"Race not found for {season} round {round}")

    # Get driver
    driver_row = db.query(Driver).filter(Driver.code == driver_code).first()
    if not driver_row:
        raise HTTPException(status_code=404, detail=f"Driver {driver_code} not found")

    # Get entry with strategy score
    entry_with_score = (
        db.query(Entry, StrategyScore)
        .join(StrategyScore, Entry.id == StrategyScore.entry_id)
        .filter(Entry.race_id == race.id, Entry.driver_id == driver_row.id)
        .first()
    )

    if not entry_with_score:
        raise HTTPException(
            status_code=404,
            detail=f"No strategy score found for {driver_code} in {season} round {round}",
        )

    entry, strategy_score = entry_with_score

    # Get decisions
    decision_records = (
        db.query(StrategyDecision)
        .filter(StrategyDecision.strategy_score_id == strategy_score.id)
        .order_by(StrategyDecision.lap_number)
        .all()
    )

    decisions = [
        StrategyDecisionResponse(
            lap_number=d.lap_number,
            decision_type=d.decision_type,
            factor=d.factor,
            impact_score=d.impact_score,
            position_delta=d.position_delta,
            time_delta_ms=d.time_delta_ms,
            explanation=d.explanation,
            comparison_context=d.comparison_context,
        )
        for d in decision_records
    ]

    score = DriverStrategyScore(
        driver_code=driver_code,
        total_score=strategy_score.total_score,
        pit_timing_score=strategy_score.pit_timing_score,
        tire_selection_score=strategy_score.tire_selection_score,
        safety_car_score=strategy_score.safety_car_score,
        weather_score=strategy_score.weather_score,
        calibration_profile=strategy_score.calibration_profile,
        calibration_version=strategy_score.calibration_version,
        decisions=decisions,
    )

    response = DriverStrategyDetailResponse(
        season=season,
        round=round,
        driver_code=driver_code,
        score=score,
    )

    redis_client.setex(cache_key, CACHE_TTL_SECONDS, json.dumps(response.model_dump()))

    return response


@router.get("/{season}/{round}/comparison")
def get_strategy_comparison(
    season: int,
    round: int,
    drivers: List[str] = Query(
        description="List of driver codes to compare (e.g., VER, HAM)",
    ),
    db: Session = Depends(get_db),
):
    """
    Compare strategy scores between specific drivers.

    Parameters
    ----------
    season : int
        Championship year (e.g., 2024)
    round : int
        FIA round number within that season
    drivers : List[str]
        List of driver codes to compare

    Returns
    -------
    dict
        Comparison data including scores and key decisions
    """
    if not drivers or len(drivers) < 2:
        raise HTTPException(
            status_code=400,
            detail="At least 2 drivers required for comparison",
        )

    # Get race
    race = (
        db.query(Race)
        .join(Season, Race.season_id == Season.id)
        .filter(Season.year == season, Race.round_number == round)
        .first()
    )

    if not race:
        raise HTTPException(status_code=404, detail=f"Race not found for {season} round {round}")

    driver_codes = [d.upper() for d in drivers]
    comparison_data = []

    for driver_code in driver_codes:
        driver_row = db.query(Driver).filter(Driver.code == driver_code).first()
        if not driver_row:
            continue

        entry_with_score = (
            db.query(Entry, StrategyScore)
            .join(StrategyScore, Entry.id == StrategyScore.entry_id)
            .filter(Entry.race_id == race.id, Entry.driver_id == driver_row.id)
            .first()
        )

        if not entry_with_score:
            continue

        entry, strategy_score = entry_with_score

        # Get key decisions (those with significant impact)
        key_decisions = (
            db.query(StrategyDecision)
            .filter(
                StrategyDecision.strategy_score_id == strategy_score.id,
                StrategyDecision.impact_score.notin_([0.0]),
            )
            .order_by(StrategyDecision.impact_score.desc())
            .limit(5)
            .all()
        )

        comparison_data.append({
            "driver_code": driver_code,
            "total_score": strategy_score.total_score,
            "scores": {
                "pit_timing": strategy_score.pit_timing_score,
                "tire_selection": strategy_score.tire_selection_score,
                "safety_car": strategy_score.safety_car_score,
                "weather": strategy_score.weather_score,
            },
            "key_decisions": [
                {
                    "lap": d.lap_number,
                    "type": d.decision_type,
                    "factor": d.factor,
                    "impact": d.impact_score,
                    "explanation": d.explanation,
                }
                for d in key_decisions
            ],
        })

    if len(comparison_data) < 2:
        raise HTTPException(
            status_code=404,
            detail="Could not find strategy scores for enough drivers to compare",
        )

    return {
        "season": season,
        "round": round,
        "comparison": comparison_data,
    }
