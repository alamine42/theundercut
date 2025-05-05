# ---------- deps layer (cached) ----------
FROM python:3.12-slim-bookworm AS deps
WORKDIR /app

# copy only dependency file(s) to leverage cache
COPY pyproject.toml ./

# install runtime deps directly with pip (no compiler needed)
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir \
      fastapi==0.111.0 uvicorn[standard]==0.29.0 httpx==0.27.0 \
      sqlalchemy psycopg2-binary redis alembic rq rq-scheduler \
      fastf1==3.1.3 pandas==2.0.3 numpy backoff pydantic

# ---------- final image ----------
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

# copy installed site‑packages and binaries from deps layer
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

# copy your actual source code (this is the only layer that changes often)
COPY . .

CMD ["uvicorn", "theundercut.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
