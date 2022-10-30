# PROD
FROM python:3.11-rc-bullseye

WORKDIR /code

COPY ./requirements.txt /code/requirements.txt
RUN pip install --upgrade -r /code/requirements.txt

COPY ./assets /code/assets
COPY ./alembic.ini /code/alembic.ini
COPY ./migrations /code/migrations
COPY ./wait-for-it.sh /code/wait-for-it.sh

COPY ./app /code/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]