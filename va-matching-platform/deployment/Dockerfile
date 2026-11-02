# VA Matching Platform — production Docker image
# Build context must include shared-canonical-services as sibling
# docker build -t va-matching-platform --build-arg SHARED_SERVICES_PATH=../shared-canonical-services deployment/

FROM python:3.12-slim AS base

# System deps for asyncpg, stripe, etc.
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc libpq-dev curl && \
    rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN groupadd -r app && useradd -r -g app app
WORKDIR /app

# Install Python deps (shared services first, then project)
ARG SHARED_SERVICES_PATH
COPY ${SHARED_SERVICES_PATH}/shared /tmp/shared-canonical-services
RUN pip install --no-cache-dir -e /tmp/shared-canonical-services

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY marketplace/ marketplace/
COPY main.py .
COPY frontend/ frontend/

# Switch to non-root
USER app

EXPOSE 8000

# Lifespan runs init_db -> task manager -> app
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=15s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1