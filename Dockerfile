ARG REQUIREMENTS_MD5
ARG DOCKER_REGISTRY_IDENTIFER
FROM ${DOCKER_REGISTRY_IDENTIFER}/hyperion-base:${REQUIREMENTS_MD5}

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1
EXPOSE 8000

WORKDIR /hyperion

COPY pyproject.toml .
COPY init.py .
COPY alembic.ini .
COPY migrations migrations/
COPY assets assets/
COPY app app/

ENTRYPOINT ["fastapi", "run", "app/main.py", "--workers", "${NB_WORKERS:-1}"]
