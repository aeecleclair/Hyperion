import logging
import multiprocessing
import os

from app.app import init_db
from app.core.config import construct_prod_settings
from app.core.log import LogConfig

# This gunicorn configuration file is based on [`uvicorn-gunicorn-docker` image config file](https://github.com/tiangolo/uvicorn-gunicorn-docker/blob/master/docker-images/gunicorn_conf.py)
# It define an `on_starting` hook that instantiate the database and run migrations

# For usage with uvicorn-gunicorn-docker image see:
# https://github.com/tiangolo/uvicorn-gunicorn-docker?tab=readme-ov-file#gunicorn_conf


workers_per_core_str = os.getenv("WORKERS_PER_CORE", "1")
max_workers_str = os.getenv("MAX_WORKERS")
use_max_workers = None
if max_workers_str:
    use_max_workers = int(max_workers_str)
web_concurrency_str = os.getenv("WEB_CONCURRENCY", None)

host = os.getenv("HOST", "0.0.0.0")
port = os.getenv("PORT", "80")
bind_env = os.getenv("BIND", None)
use_loglevel = os.getenv("LOG_LEVEL", "info")
if bind_env:  # noqa: SIM108
    use_bind = bind_env
else:
    use_bind = f"{host}:{port}"

cores = multiprocessing.cpu_count()
workers_per_core = float(workers_per_core_str)
default_web_concurrency = workers_per_core * cores
if web_concurrency_str:
    web_concurrency = int(web_concurrency_str)
    assert web_concurrency > 0  # noqa: S101
else:
    web_concurrency = max(int(default_web_concurrency), 2)
    if use_max_workers:
        web_concurrency = min(web_concurrency, use_max_workers)
accesslog_var = os.getenv("ACCESS_LOG", "-")
use_accesslog = accesslog_var or None
errorlog_var = os.getenv("ERROR_LOG", "-")
use_errorlog = errorlog_var or None
graceful_timeout_str = os.getenv("GRACEFUL_TIMEOUT", "120")
timeout_str = os.getenv("TIMEOUT", "120")
keepalive_str = os.getenv("KEEP_ALIVE", "5")

# Gunicorn config variables
loglevel = use_loglevel
workers = web_concurrency
bind = use_bind
errorlog = use_errorlog
worker_tmp_dir = "/dev/shm"  # noqa: S108
accesslog = use_accesslog
graceful_timeout = int(graceful_timeout_str)
timeout = int(timeout_str)
keepalive = int(keepalive_str)


def on_starting(server) -> None:
    """
    The hook is called just before the master process is initialized. We use it to instantiate the database and run migrations

    An gunicorn.arbiter.Arbiter instance is passed as an argument.

    See https://docs.gunicorn.org/en/stable/settings.html#on-starting
    """
    # We call `construct_prod_settings()` and not the dependency `get_settings()` because:
    # - we know we want to use the production settings
    # - we will edit environment variables to avoid initializing the database and `get_settings()` is a cached function
    settings = construct_prod_settings()

    # We set an environment variable to tell workers to avoid initializing the database
    # as we want to do it only once before workers are forked from the arbiter
    os.environ["HYPERION_INIT_DB"] = "False"

    # Initialize loggers
    LogConfig().initialize_loggers(settings=settings)

    hyperion_error_logger = logging.getLogger("hyperion.error")

    hyperion_error_logger.warning(
        "Starting Gunicorn server and initializing the database.",
    )

    init_db(
        settings=settings,
        hyperion_error_logger=hyperion_error_logger,
        drop_db=False,
    )

    if not settings.REDIS_HOST:
        hyperion_error_logger.warning(
            "Redis configuration is missing. When using multiple workers without Redis, broadcasting messages over websocket will not work correctly.",
        )
