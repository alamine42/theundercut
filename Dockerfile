# ---------- base & deps layer (cached unless pyproject changes) ----------
FROM python:3.12-slim-bookworm AS deps
WORKDIR /app
COPY pyproject.toml poetry.lock* ./          # only dependency files
RUN apt-get update && apt-get install -y build-essential git && \
    pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-interaction --only main

# ---------- final image ----------
FROM python:3.12-slim-bookworm
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app
COPY --from=deps /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

COPY . .                       # now copy the source (fast)
CMD ["uvicorn", "theundercut.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
