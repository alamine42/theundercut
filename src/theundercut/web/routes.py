"""
Server-rendered (Jinja2) pages for The Undercut.
Exposes /race/<season>/<round> and /analytics/<season>/<round>.
"""

from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()


@router.get("/race/{season}/{round}", response_class=HTMLResponse)
async def race_page(request: Request, season: int, round: int):
    """
    Minimal page that fetches laps via HTMX.
    """
    return templates.TemplateResponse(
        "race/detail.html",
        {"request": request, "season": season, "round": round},
    )


@router.get("/analytics/{season}/{round}", response_class=HTMLResponse)
async def analytics_page(
    request: Request,
    season: int,
    round: int,
    drivers: Optional[List[str]] = Query(default=None),
):
    """
    Analytics page with interactive Chart.js visualizations.
    """
    return templates.TemplateResponse(
        "analytics/index.html",
        {
            "request": request,
            "season": season,
            "round": round,
            "selected_drivers": drivers or [],
        },
    )


@router.get("/analytics/{season}/{round}/charts", response_class=HTMLResponse)
async def analytics_charts_partial(
    request: Request,
    season: int,
    round: int,
    drivers: Optional[List[str]] = Query(default=None),
):
    """
    HTMX partial that returns updated chart containers and scripts.
    Used when driver filters change.
    """
    return templates.TemplateResponse(
        "analytics/_charts.html",
        {
            "request": request,
            "season": season,
            "round": round,
            "selected_drivers": drivers or [],
        },
    )
