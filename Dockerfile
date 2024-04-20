# PROD
FROM tiangolo/uvicorn-gunicorn-fastapi:python3.11
# Image running several instances of uvicorn in parallel with gunicorn, listens on port 80
# See https://github.com/tiangolo/uvicorn-gunicorn-fastapi-docker

COPY ./alembic.ini /app/alembic.ini
COPY ./migrations /app/migrations

COPY ./assets /app/assets

COPY ./requirements-common.txt /requirements-common.txt
COPY ./requirements-prod.txt /requirements-prod.txt
RUN pip install --upgrade -r /requirements-prod.txt

COPY ./app/ /app/app/