FROM python:3.13-slim

# Environment
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_SYSTEM_PYTHON=1

# System packages for psycopg2 and builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Install uv via pip (simple and reliable)
RUN python -m pip install --upgrade pip uv

WORKDIR /app

# Copy project manifests first for better layer caching
COPY pyproject.toml uv.lock ./

# Install dependencies into system Python using uv and lockfile
RUN uv sync --frozen --no-dev

# Copy application source
COPY src ./src

# Create and use non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# App env
ENV PYTHONPATH=/app/src

# Default command (dev: reload; override in prod compose)
CMD ["uv", "run", "uvicorn", "app.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000", "--reload"]