############################
# choose the version ONCE  #
############################
ARG PY_VER=3.11                    

# ---------- deps layer ----------
FROM python:${PY_VER}-slim-bookworm AS deps
ARG PY_VER                           
WORKDIR /app

COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip \
 && pip install --no-cache-dir \
      fastapi==0.111.0 uvicorn[standard]==0.29.0 httpx==0.27.0 \
      sqlalchemy psycopg2-binary redis alembic rq rq-scheduler \
      fastf1==3.1.3 pandas==2.0.3 numpy backoff pydantic

# ---------- final image ----------
FROM python:${PY_VER}-slim-bookworm
ARG PY_VER
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
WORKDIR /app

COPY --from=deps /usr/local/lib/python${PY_VER}/site-packages /usr/local/lib/python${PY_VER}/site-packages
COPY --from=deps /usr/local/bin /usr/local/bin

COPY . .
RUN pip install --no-cache-dir -e .

# Create a non-root user and set appropriate permissions
RUN useradd -m appuser && \
    chown -R appuser:appuser /app
USER appuser

CMD ["uvicorn", "theundercut.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
