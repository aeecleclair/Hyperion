# PROD
FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11
# Image running several instances of uvicorn in parallel with gunicorn, listens on port 80
# See https://github.com/tiangolo/uvicorn-gunicorn-fastapi-docker

# Gunicorn config file must be named `gunicorn_conf.py` to be used by `uvicorn-gunicorn-fastapi`
# See https://github.com/tiangolo/uvicorn-gunicorn-docker?tab=readme-ov-file#gunicorn_conf
COPY ./gunicorn.conf.py /app/gunicorn_conf.py

COPY ./alembic.ini /app/alembic.ini
COPY ./migrations /app/migrations

COPY ./assets /app/assets

COPY ./requirements.txt /requirements.txt

RUN curl -LsSf https://astral.sh/uv/install.sh | sh
RUN /root/.cargo/bin/uv pip install --system --upgrade -r /requirement-prod.txt

COPY ./app/ /app/app/
