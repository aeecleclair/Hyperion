import logging
import os

from app.app import init_db
from app.core.config import construct_prod_settings
from app.core.log import LogConfig


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
