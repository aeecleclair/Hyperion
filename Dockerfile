# PROD
FROM python:3.11-rc-bullseye
# Image running several instances of uvicorn in parallel with gunicorn, listens on port 80
# See https://github.com/tiangolo/uvicorn-gunicorn-docker

COPY ./requirements.txt /requirements.txt

RUN pip install --no-cache-dir --upgrade -r /requirements.txt
RUN pip install --no-cache-dir --upgrade gunicorn

WORKDIR code
COPY ./assets /code/assets
COPY ./alembic.ini /code/alembic.ini
COPY ./migrations /code/migrations
COPY ./wait-for-it.sh /code/wait-for-it.sh

COPY ./app/ /code/app/