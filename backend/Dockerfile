# Multi-stage production Dockerfile for FastAPI backend
FROM python:3.12-slim AS builder

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt


# Final Runtime Stage
FROM python:3.12-slim AS runner

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/root/.local/bin:$PATH"

# Install runtime PostgreSQL client library
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -g 1000 appgroup && \
    useradd -u 1000 -g appgroup -s /bin/bash -m appuser

# Copy installed Python packages from builder
COPY --from=builder /root/.local /home/appuser/.local
ENV PATH="/home/appuser/.local/bin:$PATH"

# Copy application source code
COPY --chown=appuser:appgroup alembic.ini .
COPY --chown=appuser:appgroup alembic ./alembic
COPY --chown=appuser:appgroup app ./app
COPY --chown=appuser:appgroup scripts ./scripts

# Create uploads directory with non-root ownership
RUN mkdir -p /app/uploads/menu && chown -R appuser:appgroup /app/uploads

USER appuser

EXPOSE 8000

# Healthcheck using FastAPI readiness probe
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://127.0.0.1:8000/api/v1/health/live || exit 1

# Single Uvicorn async worker process (maintains in-memory WebSocket state without Redis)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1", "--ws-ping-interval", "25", "--ws-ping-timeout", "20", "--ws-max-size", "4096", "--proxy-headers"]
