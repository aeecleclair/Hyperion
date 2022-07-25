import logging
import queue
from logging.handlers import QueueHandler, QueueListener

from pydantic import BaseModel

from app.core.settings import settings


class LogConfig(BaseModel):
    """
    Logging configuration to be set for the server
    We convert this class to a dict to be used by Python logging module.

    Call `LogConfig.initialize_loggers()` to configure the logging ecosystem.
    Call `LogConfig().initialize_loggers()` to configure the logging ecosystem.
    """

    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    MATRIX_LOG_FORMAT: str = "%(asctime)s - %(name)s - <code>%(levelname)s</code> - <font color ='green'>%(message)s</font>"
    MINIMUM_LOG_LEVEL: str = "DEBUG" if settings.LOG_DEBUG_MESSAGES else "INFO"

    # Logging config
    # See https://docs.python.org/3/library/logging.config.html#logging-config-dictschema
    version = 1
    disable_existing_loggers = True
    formatters = {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": LOG_FORMAT,
            "datefmt": "%d-%b-%y %H:%M:%S",
        },
        "matrix": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": MATRIX_LOG_FORMAT,
            "datefmt": "%d-%b-%y %H:%M:%S",
        },
    }
    handlers = {
        "default": {
            "formatter": "default",
            # If settings.LOG_DEBUG_MESSAGES is set, the default handlers should print DEBUG log messages to the console.
            "class": (
                "logging.StreamHandler"
                if settings.LOG_DEBUG_MESSAGES
                else "logging.NullHandler"
            ),
            # "stream": "ext://sys.stderr",
            "level": "DEBUG",
        },
        "matrix_errors": {
            # Send error to a Matrix server. If credentials are not set in settings, the handler will be disabled
            "formatter": "matrix",
            "class": "app.utils.loggers_tools.matrix_handler.MatrixHandler",
            "room_id": settings.MATRIX_LOG_ERROR_ROOM_ID,
            "enabled": (
                settings.MATRIX_USER_NAME is not None
                and settings.MATRIX_USER_PASSWORD is not None
                and settings.MATRIX_LOG_ERROR_ROOM_ID is not None
            ),
            "level": "ERROR",
        },
        "file_errors": {
            # file_errors handler logs errors in two 1024 bytes files
            # https://docs.python.org/3/library/logging.handlers.html#logging.handlers.RotatingFileHandler
            "formatter": "default",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/errors.log",
            "maxBytes": 1024,
            "backupCount": 2,
            "level": "WARNING",
        },
        "file_access": {
            # file_access should receive information about all incoming requests
            "formatter": "default",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/access.log",
            "maxBytes": 1024,
            "backupCount": 10,
            "level": "INFO",
        },
        "file_tokens": {
            # file_tokens should receive informations about JWT verifications.
            # This allows, with file_access records, to identify which user accessed a specific endpoint
            "formatter": "default",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/tokens.log",
            "maxBytes": 1024,  # *10
            "backupCount": 10,
            "level": "INFO",
        },
        "file_auth": {
            # file_auth should receive informations about auth operation, like inscription, account validation, authentification and token refresh.
            # Success and failures should be logged
            "formatter": "default",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/auth.log",
            "maxBytes": 1024,  # *10
            "backupCount": 10,
            "level": "INFO",
        },
    }

    # We define various loggers which can be used by Hyperion.
    # Each logger has:
    #  - specific handlers (ex: file_access or file_tokens), they log targeted records like endpoint access or authentification
    #  - error related handlers (ex: file_errors and matrix_errors), they log all errors regardless of their provenance
    #  - default handler which logs to the console for development and debugging purpose
    # TODO: disable default handler in production
    loggers = {
        "hyperion.access": {
            "handlers": ["file_access", "file_errors", "matrix_errors", "default"],
            "level": MINIMUM_LOG_LEVEL,
        },
        "hyperion.token": {
            "handlers": ["file_tokens", "file_errors", "matrix_errors", "default"],
            "level": MINIMUM_LOG_LEVEL,
        },
        "hyperion.auth": {
            "handlers": ["file_access", "file_errors", "default"],
            "level": MINIMUM_LOG_LEVEL,
        },
        # We disable "uvicorn.access" to replace it with our custom "hyperion.access"
        # "uvicorn.access": {"handlers": [], "level": MINIMUM_LOG_LEVEL},
        "hyperion.errors": {
            "handlers": ["file_errors", "matrix_errors", "default"],
            "level": MINIMUM_LOG_LEVEL,
        },
    }

    def initialize_loggers(self):
        """
        Initialize the logging ecosystem.

        The previous dict configuration will be used.

        Hyperion is an async FastAPI application. Logging may be done by endpoints. In order to limit the speed impact of
        logging (especially for network operations, like sending a log record to a Matrix server), it will be realized in a specific thread.
        All handlers will then be encapsulated in QueueHandlers having their own thread.
        """
        # https://rob-blackbourn.medium.com/how-to-use-python-logging-queuehandler-with-dictconfig-1e8b1284e27a
        # https://www.zopatista.com/python/2019/05/11/asyncio-logging/

        # We may be interested in https://github.com/python/cpython/pull/93269 when it will be released. See https://discuss.python.org/t/a-new-feature-is-being-added-in-logging-config-dictconfig-to-configure-queuehandler-and-queuelistener/16124

        logging.config.dictConfig(self.dict())

        loggers = [logging.getLogger(name) for name in self.loggers]

        for logger in loggers:
            # If the logger does not have any handler, we don't need to create a QueueHandler
            if len(logger.handlers) == 0:
                continue

            # We create a queue where all log records will be added
            log_queue = queue.Queue(-1)

            # queue_handler is the handler which add all log records to the queue
            queue_handler = QueueHandler(log_queue)

            # The listener will watch the queue and let the previous handler process logs records in their own thread
            listener = QueueListener(log_queue, *logger.handlers)
            listener.start()

            # We remove all previous handlers
            logger.handlers = []

            # We add our new queue_handler
            logger.addHandler(queue_handler)
