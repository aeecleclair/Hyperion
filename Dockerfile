FROM python:3.11-slim-bookworm

# Default number of workers; can be overridden at runtime
ENV WORKERS=1

# Update package list and install weasyprint dependencies
RUN apt-get update && apt-get install -y \
    weasyprint \
    && rm -rf /var/lib/apt/lists/*

# Set environment variables to optimize Python behavior in production
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1

WORKDIR /hyperion

# First copy only the requirements to leverage Docker cache
COPY requirements-common.txt .
COPY requirements-prod.txt .
# Install dependencies, using
# --no-cache-dir to reduce image size and
# --upgrade to get benefits of the caching layer in Docker
RUN pip install --no-cache-dir --upgrade -r requirements-prod.txt

# Then copy the rest of the application code
COPY pyproject.toml .
COPY alembic.ini .
COPY migrations migrations/
COPY assets assets/
COPY app app/

# Expose port 8000
EXPOSE 8000

# Use uvicorn instead of fastapi for better performance and flexibility
ENTRYPOINT ["sh", "-c", "uvicorn app.main:app --workers $WORKERS --host 0.0.0.0 --port 8000"]