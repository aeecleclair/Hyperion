ARG REQUIREMENTS_MD5
ARG DOCKER_REGISTRY_IDENTIFER
FROM ${DOCKER_REGISTRY_IDENTIFER}/hyperion-base:${REQUIREMENTS_MD5}

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV UV_COMPILE_BYTECODE=1

WORKDIR /hyperion

COPY init.py .
COPY alembic.ini .
COPY migrations migrations/
COPY assets assets/
COPY app app/

COPY start.sh .
RUN chmod +x start.sh

ENTRYPOINT ["./start.sh"]
