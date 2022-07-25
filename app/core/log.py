import logging
import queue
from logging.handlers import QueueHandler, QueueListener

from pydantic import BaseModel


class LogConfig(BaseModel):
    """
    Logging configuration to be set for the server
    We convert this class to a dict to be used by Python logging module.

    Call `LogConfig.initialize_loggers()` to configure the logging ecosystem.
    """

    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    MATRIX_LOG_FORMAT: str = "%(asctime)s - %(name)s - <code>%(levelname)s</code> - <font color ='green'>%(message)s</font>"
    LOG_LEVEL: str = "DEBUG"

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
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "matrix_access": {
            "formatter": "matrix",
            "class": "app.utils.loggers_tools.matrix_handler.MatrixHandler",
            "level": "INFO",
        },
        "file_errors": {
            # file_errors handler logs errors in two 1024 bytes
            # https://docs.python.org/3/library/logging.handlers.html#logging.handlers.RotatingFileHandler
            "formatter": "default",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/errors.log",
            "maxBytes": 1024,
            "backupCount": 2,
            "level": "ERROR",
        },
        "file_access": {
            # file_errors handler logs errors in two 1024 bytes
            # https://docs.python.org/3/library/logging.handlers.html#logging.handlers.RotatingFileHandler
            "formatter": "default",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/access.log",
            "maxBytes": 1024,
            "backupCount": 10,
            "level": "INFO",
        },
        "file_tokens": {
            "formatter": "default",
            "class": "logging.handlers.RotatingFileHandler",
            "filename": "logs/tokens.log",
            "maxBytes": 1024,  # *10
            "backupCount": 10,
            "level": "INFO",
        },
    }

    loggers = {
        "hyperion.access": {
            "handlers": ["file_access", "file_errors", "matrix_access", "default"],
            "level": LOG_LEVEL,
        },
        "hyperion.token": {
            "handlers": ["file_tokens", "file_errors", "default"],
            "level": LOG_LEVEL,
        },
        "hyperion.auth": {
            "handlers": ["file_access", "file_errors", "default"],
            "level": LOG_LEVEL,
        },
        # We disable "uvicorn.access" to replace it with our custom "hyperion.access"
        "uvicorn.access": {"handlers": [], "level": LOG_LEVEL},
        "hyperion.errors": {"handlers": ["file_errors", "default"], "level": LOG_LEVEL},
    }

    @classmethod
    def initialize_loggers(cls):
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

        logging.config.dictConfig(cls().dict())

        loggers = [logging.getLogger(name) for name in logging.root.manager.loggerDict]

        for logger in loggers:
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
