"""
Server-rendered (Jinja2) pages for The Undercut.
Exposes homepage, standings, race analytics, and legal pages.
"""

from pathlib import Path
from typing import Optional, List
from fastapi import APIRouter, Request, Query
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates

BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

router = APIRouter()


@router.get("/", response_class=RedirectResponse)
async def homepage():
    """Redirect homepage to current season standings."""
    return RedirectResponse(url="/standings/2024", status_code=302)


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


@router.get("/standings/{season}", response_class=HTMLResponse)
async def standings_page(request: Request, season: int):
    """
    Season championship standings with driver and constructor tables.
    """
    return templates.TemplateResponse(
        "standings/index.html",
        {"request": request, "season": season},
    )


@router.get("/privacy", response_class=HTMLResponse)
async def privacy_policy(request: Request):
    """Privacy policy page."""
    return templates.TemplateResponse("legal/privacy.html", {"request": request})


@router.get("/terms", response_class=HTMLResponse)
async def terms_of_service(request: Request):
    """Terms of service page."""
    return templates.TemplateResponse("legal/terms.html", {"request": request})
