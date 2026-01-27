FROM ghcr.io/astral-sh/uv:0.9.27-python3.14-alpine3.23 AS builder

ENV UV_COMPILE_BYTECODE=1
ENV UV_LINK_MODE=copy
ENV UV_NO_DEV=1
ENV UV_PYTHON_DOWNLOADS=0

WORKDIR /hyperion

# Install psutil dependencies
RUN apk add --no-cache gcc musl-dev linux-headers

RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=uv.lock,target=uv.lock \
    --mount=type=bind,source=pyproject.toml,target=pyproject.toml \
    uv sync --locked --no-install-project

# First copy only the lockfile to leverage Docker cache
COPY uv.lock .
# Install dependencies using uv with caching
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --locked --all-extras

FROM python:3.14-alpine3.23

# Create non-root user early for better security
# Choose an id that is not likely to be a default one
RUN addgroup --system --gid 10101 hyperion
RUN adduser --system --uid 10101 --ingroup hyperion hyperion

# Change ownership of the application directory to the hyperion user
COPY --from=builder --chown=hyperion:hyperion /hyperion /hyperion
ENV PATH="/hyperion/.venv/bin:$PATH"

# Set environment variables to optimize Python behavior in production
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Default number of workers; can be overridden at runtime
ENV WORKERS=2

# Install weasyprint dependencies
RUN apk add --no-cache weasyprint

WORKDIR /hyperion

# Then copy the rest of the application code
COPY alembic.ini .
COPY pyproject.toml .
COPY assets assets/
COPY migrations migrations/
COPY app app/

# Switch to non-root user
USER hyperion

# Expose port 8000
EXPOSE 8000

# Use FastAPI CLI as the entrypoint
# Use shell form to allow environment variable expansion
SHELL ["/bin/sh", "-c"]
ENTRYPOINT fastapi run --workers "$WORKERS" --host "0.0.0.0" --port 8000