"""
Server-rendered (Jinja2) pages for The Undercut.
Right now we expose only /race/<season>/<round>.
"""

from pathlib import Path
from fastapi import APIRouter, Request
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
