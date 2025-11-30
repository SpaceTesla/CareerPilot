FROM python:3.12-slim

# Environment
ENV PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

# System packages for psycopg2 and builds
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    ca-certificates \
  && rm -rf /var/lib/apt/lists/*

# Upgrade pip
RUN python -m pip install --upgrade pip

WORKDIR /app

# Copy requirements and install dependencies
COPY pyproject.toml ./

# Install all dependencies from pyproject.toml
RUN pip install \
    "fastapi>=0.118.0" \
    "google-generativeai>=0.8.5" \
    "httpx>=0.28.1" \
    "langchain>=0.3.27" \
    "langchain-google-genai>=2.0.10" \
    "langgraph>=0.6.8" \
    "pydantic[email]>=2.11.10" \
    "pydantic-settings>=2.11.0" \
    "python-dotenv>=1.1.1" \
    "uvicorn[standard]>=0.37.0" \
    "sse-starlette>=2.2.1" \
    "pymupdf>=1.26.5" \
    "pymupdf4llm>=0.0.27" \
    "python-multipart>=0.0.20" \
    "sqlalchemy>=2.0.43" \
    "psycopg2-binary>=2.9.11" \
    "pgvector>=0.4.1" \
    "alembic>=1.17.0" \
    "tavily-python>=0.3.0" \
    "langchain-community>=0.3.31"

# Copy application source
COPY src ./src

# Create and use non-root user
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# App env
ENV PYTHONPATH=/app/src

# Default command
CMD ["python", "-m", "uvicorn", "app.main:app", "--app-dir", "src", "--host", "0.0.0.0", "--port", "8000", "--reload"]