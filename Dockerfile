FROM ghcr.io/astral-sh/uv:0.4.5-python3.11-bookworm as uv-builder

COPY ./requirements-common.txt /requirements-common.txt
COPY ./requirements-prod.txt /requirements-prod.txt
ENV VIRTUAL_ENV=/opt/venv \
    PATH="/opt/venv/bin:$PATH"
# RUN /root/.cargo/bin/uv pip install --system --upgrade -r /requirement-prod.txt
RUN uv venv /opt/venv && \
    uv pip install --no-cache -r requirements-prod.txt

# PROD
FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11
# Image running several instances of uvicorn in parallel with gunicorn, listens on port 80
# See https://github.com/tiangolo/uvicorn-gunicorn-fastapi-docker

COPY --from=uv-builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
# Gunicorn config file must be named `gunicorn_conf.py` to be used by `uvicorn-gunicorn-fastapi`
# See https://github.com/tiangolo/uvicorn-gunicorn-docker?tab=readme-ov-file#gunicorn_conf
COPY ./gunicorn.conf.py /app/gunicorn_conf.py

COPY ./alembic.ini /app/alembic.ini
COPY ./migrations /app/migrations

COPY ./assets /app/assets

COPY ./app/ /app/app/
