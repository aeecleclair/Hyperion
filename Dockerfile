# PROD
FROM python:3.11-rc-slim

WORKDIR /code

COPY ./requirements-dev.txt /code/requirements-dev.txt
COPY ./requirements.txt /code/requirements.txt
COPY ./.env /code/.env
COPY ./alembic.ini /code/alembic.ini
COPY ./migrations /code/migrations

RUN pip install --upgrade -r /code/requirements-dev.txt

COPY ./app /code/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]