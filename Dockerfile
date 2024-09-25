# PROD
FROM ghcr.io/astral-sh/uv:python3.11-bookworm

COPY ./requirements-common.txt /requirements-common.txt
COPY ./requirements-prod.txt /requirements-prod.txt
RUN uv pip install --system -r /requirements-prod.txt

COPY ./start.sh /app/start.sh
RUN chmod +x /app/start.sh

COPY ./prestart.py /app/prestart.py

COPY ./alembic.ini /app/alembic.ini
COPY ./migrations /app/migrations

COPY ./assets /app/assets

COPY ./app/ /app/app/

CMD ["/app/start.sh"]
