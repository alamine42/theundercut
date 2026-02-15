from fastapi import FastAPI
from theundercut.api.v1 import analytics as analytics_api
from theundercut.api.v1 import race as race_api          # JSON API
from theundercut.web.routes import router as web_router  # Jinja pages

app = FastAPI(title="The Undercut")

# JSON endpoints
app.include_router(race_api.router)
app.include_router(analytics_api.router)

# Server-rendered pages
app.include_router(web_router)
