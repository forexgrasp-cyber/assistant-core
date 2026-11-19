# AI Assistant — Production Dockerfile (multi-stage)
#
# The shared canonical services library is installed from the PRIVATE wheel
# staged in ./dist by deploy.sh (see build-wheel step). Nothing is pulled
# from a public package index.

# -----------------------------------------------------------------------------
# Stage 1: Python dependencies
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS python-builder

WORKDIR /build

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

RUN pip install --no-cache-dir --upgrade pip setuptools wheel

# Wrapper requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Private shared-canonical-services wheel (staged by deploy.sh)
COPY dist/ /tmp/dist/
RUN pip install --no-cache-dir /tmp/dist/shared_canonical_services-*.whl

# -----------------------------------------------------------------------------
# Stage 2: Runtime
# -----------------------------------------------------------------------------
FROM python:3.12-slim AS runtime

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

RUN groupadd -r appuser && useradd -r -g appuser -d /app -s /bin/bash appuser

WORKDIR /app

COPY --from=python-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Application code
COPY --chown=appuser:appuser app/ ./app/

RUN mkdir -p /app/data /app/logs && chown -R appuser:appuser /app

USER appuser

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["gunicorn", "app.main:app", \
     "--workers", "4", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--bind", "0.0.0.0:8000", \
     "--timeout", "120", \
     "--keep-alive", "5", \
     "--max-requests", "1000", \
     "--max-requests-jitter", "100", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "--log-level", "info"]
