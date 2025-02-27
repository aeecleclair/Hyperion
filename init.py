import logging

from app.app import init_db
from app.core.utils.config import construct_prod_settings
from app.core.utils.log import LogConfig

# We call `construct_prod_settings()` and not the dependency `get_settings()` because:
# - we know we want to use the production settings
# - we will edit environment variables to avoid initializing the database and `get_settings()` is a cached function
settings = construct_prod_settings()

# Initialize loggers
LogConfig().initialize_loggers(settings=settings)

hyperion_error_logger = logging.getLogger("hyperion.error")

hyperion_error_logger.warning(
    "Starting Uvicorn server and initializing the database.",
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
