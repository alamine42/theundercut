# ---------- deps layer (cached) ----------
FROM python:3.11-slim-bookworm AS deps          # 👈  switch 3.12 → 3.11
WORKDIR /app

COPY pyproject.toml ./

RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir \
      fastapi==0.111.0 uvicorn[standard]==0.29.0 httpx==0.27.0 \
      sqlalchemy psycopg2-binary redis alembic rq rq-scheduler \
      fastf1==3.1.3 pandas==2.0.3 numpy backoff pydantic

# ---------- final image ----------
FROM python:3.11-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY --from=deps /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

COPY . .
CMD ["uvicorn", "theundercut.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
