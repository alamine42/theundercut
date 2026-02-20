from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from theundercut.api.v1 import analytics as analytics_api
from theundercut.api.v1 import circuits as circuits_api
from theundercut.api.v1 import race as race_api          # JSON API
from theundercut.api.v1 import standings as standings_api
from theundercut.web.routes import router as web_router  # Jinja pages

app = FastAPI(title="The Undercut")

# Static files (logo, etc.)
STATIC_DIR = Path(__file__).resolve().parent.parent / "web" / "static"
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# JSON endpoints
app.include_router(race_api.router)
app.include_router(analytics_api.router)
app.include_router(standings_api.router)
app.include_router(circuits_api.router)

# Server-rendered pages
app.include_router(web_router)
