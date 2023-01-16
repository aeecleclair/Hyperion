# PROD
FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11
# Image running several instances of uvicorn in parallel with gunicorn, listens on port 80
# See https://github.com/tiangolo/uvicorn-gunicorn-fastapi-docker

COPY ./requirements.txt /requirements.txt

RUN pip install --no-cache-dir --upgrade -r /requirements.txt

COPY ./assets /app/assets
COPY ./alembic.ini /app/alembic.ini
COPY ./migrations /app/migrations

COPY ./app/ /app/app/