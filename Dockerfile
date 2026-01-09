FROM ghcr.io/astral-sh/uv:python3.14-trixie-slim

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

# Create non-root user early for better security
# Choose an id that is not likely to be a default one
RUN groupadd --gid 10101 hyperion && \
    useradd --uid 10101 --gid hyperion --shell /bin/bash --create-home hyperion

WORKDIR /hyperion

# First copy only the requirements to leverage Docker cache
COPY requirements-prod.txt .

# Install dependencies using uv (way faster than pip)
RUN uv pip install --system --no-cache -r requirements-prod.txt

# Then copy the rest of the application code
COPY alembic.ini .
COPY pyproject.toml .
COPY assets assets/
COPY migrations migrations/
COPY app app/

# Change ownership of the application directory to the hyperion user
RUN chown -R hyperion:hyperion /hyperion

# Switch to non-root user
USER hyperion

# Expose port 8000
EXPOSE 8000

# Use fastapi cli as the entrypoint
# Use sh -c to allow environment variable expansion
ENTRYPOINT ["sh", "-c", "fastapi run --workers $WORKERS --host 0.0.0.0 --port 8000"]

