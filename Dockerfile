# Dockerfile - production-friendly for python:3.11-slim
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1
WORKDIR /app

# Install system deps required to compile wheels (psycopg2, Pillow)
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    gcc \
    libpq-dev \
    libjpeg-dev \
    zlib1g-dev \
    libssl-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy only requirements first for caching
COPY requirements.txt .

# Upgrade pip (optional) then install python deps
RUN pip install --upgrade pip setuptools wheel \
    && pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create a non-root user and fix permissions
RUN adduser --disabled-password --gecos "" appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 5000

# Healthcheck (optional)
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s CMD curl -f http://localhost:5000/_health || exit 1

# Run via gunicorn
CMD ["gunicorn", "--workers", "3", "--bind", "0.0.0.0:5000", "wsgi:app"]
