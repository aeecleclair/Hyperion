# PROD
FROM python:3.10-bullseye

WORKDIR /code

COPY ./requirements_dev.txt /code/requirements_dev.txt
COPY ./requirements.txt /code/requirements.txt
COPY ./.env /code/.env

RUN pip install --upgrade -r /code/requirements_dev.txt

COPY ./app /code/app

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "80"]
