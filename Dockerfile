FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# install deps explicitly
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir fastapi==0.111.0 "uvicorn[standard]==0.29.0" httpx==0.27.0

COPY src/ ./src/

CMD ["uvicorn", "theundercut.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
