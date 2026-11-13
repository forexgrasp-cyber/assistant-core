# Assistant Core Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    ffmpeg \
    libsndfile1 \
    libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements
COPY pyproject.toml .
RUN pip install --no-cache-dir -e .[voice,desktop]

# Copy application
COPY . .

# Create data directories
RUN mkdir -p /app/data/chromadb /app/data/tenants

EXPOSE 8037

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8037"]