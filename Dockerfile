FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1

WORKDIR /app
COPY pyproject.toml ./
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r <(python -m pip install --dry-run -r /dev/null \
        | grep -E "fastapi|uvicorn|httpx" | cut -d' ' -f1)

COPY src/ ./src/
CMD ["uvicorn", "theundercut.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
