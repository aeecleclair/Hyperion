import logging
import logging.config
import queue
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path
from typing import Any

from app.core.config import Settings


class LogConfig:
    """
    Logging configuration to be set for the server
    We convert this class to a dict to be used by Python logging module.

    Call `LogConfig().initialize_loggers()` to configure the logging ecosystem.
    """

    # Uvicorn loggers config
    # https://github.com/encode/uvicorn/blob/b21ecabc5bf911f571e0629438315a1e5472065c/uvicorn/config.py#L95

    class console_color:
        GREEN = "\033[92m"
        BOLD = "\033[1m"
        END = "\033[0m"

    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    CONSOLE_LOG_FORMAT: str = (
        "%(asctime)s - %(name)s - "
        + console_color.BOLD
        + "%(levelname)s"
        + console_color.END
        + " - "
        + console_color.GREEN
        + "%(message)s"
        + console_color.END
    )
    MATRIX_LOG_FORMAT: str = "%(asctime)s - %(name)s - <code>%(levelname)s</code> - <font color ='green'>%(message)s</font>"

    # Logging config
    # See https://docs.python.org/3/library/logging.config.html#logging-config-dictschema
    def get_config_dict(self, settings: Settings):
        # We can't use a dependency to access settings as this function is not an endpoint. The object must thus be passed as a parameter.

        MINIMUM_LOG_LEVEL: str = "DEBUG" if settings.LOG_DEBUG_MESSAGES else "INFO"

        return {
            "version": 1,
            # If LOG_DEBUG_MESSAGES is set, we let existing loggers, including the database and uvicorn loggers
            "disable_existing_loggers": not settings.LOG_DEBUG_MESSAGES,
            "formatters": {
                "default": {
                    "format": self.LOG_FORMAT,
                    "datefmt": "%d-%b-%y %H:%M:%S",
                },
                "console_formatter": {
                    "format": self.CONSOLE_LOG_FORMAT,
                    "datefmt": "%d-%b-%y %H:%M:%S",
                },
                "matrix": {
                    "format": self.MATRIX_LOG_FORMAT,
                    "datefmt": "%d-%b-%y %H:%M:%S",
                },
            },
            "handlers": {
                # Console handler is always active, even in production.
                # It should be used to log errors and information about the server (starting up, hostname...)
                "console": {
                    "formatter": "console_formatter",
                    "class": "logging.StreamHandler",
                    "level": MINIMUM_LOG_LEVEL,
                },
                # Matrix_errors handler send text messages to a Matrix server
                "matrix_errors": {
                    # Send error to a Matrix server. If credentials are not set in settings, the handler will be disabled
                    "formatter": "matrix",
                    "class": "app.utils.loggers_tools.matrix_handler.MatrixHandler",
                    "room_id": settings.MATRIX_LOG_ERROR_ROOM_ID,
                    "token": settings.MATRIX_TOKEN,
                    "server_base_url": settings.MATRIX_SERVER_BASE_URL,
                    "enabled": (
                        settings.MATRIX_TOKEN and settings.MATRIX_LOG_ERROR_ROOM_ID
                    ),
                    "level": "ERROR",
                },
                "matrix_amap": {
                    # Send error to a Matrix server. If credentials are not set in settings, the handler will be disabled
                    "formatter": "matrix",
                    "class": "app.utils.loggers_tools.matrix_handler.MatrixHandler",
                    "room_id": settings.MATRIX_LOG_AMAP_ROOM_ID,
                    "token": settings.MATRIX_TOKEN,
                    "server_base_url": settings.MATRIX_SERVER_BASE_URL,
                    "enabled": (
                        settings.MATRIX_TOKEN and settings.MATRIX_LOG_AMAP_ROOM_ID
                    ),
                    "level": "INFO",
                },
                # There is a handler per log file #
                # They are based on RotatingFileHandler to logs in multiple 1024 bytes files
                # https://docs.python.org/3/library/logging.handlers.html#logging.handlers.RotatingFileHandler
                "file_errors": {
                    # File_errors should receive all errors, even when they are already logged elsewhere
                    "formatter": "default",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": "logs/errors.log",
                    "maxBytes": 1024 * 1024 * 10,  # ~ 10 MB
                    "backupCount": 20,
                    "level": "INFO",
                },
                "file_access": {
                    # file_access should receive information about all incoming requests and JWT verifications
                    "formatter": "default",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": "logs/access.log",
                    "maxBytes": 1024 * 1024 * 40,  # ~ 40 MB
                    "backupCount": 50,
                    "level": "INFO",
                },
                "file_security": {
                    # file_security should receive informations about auth operation, inscription, account validation, authentification and token refresh success or failure.
                    # Success and failures should be logged
                    "formatter": "default",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": "logs/security.log",
                    "maxBytes": 1024 * 1024 * 40,  # ~ 40 MB
                    "backupCount": 50,
                    "level": "INFO",
                },
                "file_amap": {
                    # file_amap should receive informations about amap operation, every operation involving a cash modification.
                    "formatter": "default",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": "logs/amap.log",
                    "maxBytes": 1024 * 1024 * 10,  # ~ 10 MB
                    "backupCount": 20,
                    "level": "INFO",
                },
                "file_raffle": {
                    # file_amap should receive informations about amap operation, every operation involving a cash modification.
                    "formatter": "default",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": "logs/raffle.log",
                    "maxBytes": 1024 * 1024 * 10,  # ~ 10 MB
                    "backupCount": 20,
                    "level": "INFO",
                },
            },
            # We define various loggers which can be used by Hyperion.
            # Each logger has:
            #  - specific handlers (ex: file_access or file_security), they log targeted records like endpoint access or authentication
            #  - error related handlers (ex: file_errors and matrix_errors), they log all errors regardless of their provenance
            #  - default handler which logs to the console for development and debugging purpose
            "loggers": {
                "root": {
                    "level": "DEBUG",
                    "handlers": ["console"],
                },
                "hyperion": {
                    "propagate": False,
                },
                # hyperion.access should log incoming request and JWT verifications
                "hyperion.access": {
                    "handlers": [
                        "file_access",
                        "console",
                    ],
                    "level": MINIMUM_LOG_LEVEL,
                },
                "hyperion.security": {
                    "handlers": [
                        "file_security",
                        "matrix_errors",
                        "console",
                    ],
                    "level": MINIMUM_LOG_LEVEL,
                },
                # hyperion.error should be used to log all errors which does not correspond to one of the specific loggers
                # Other loggers can process error messages and may be more appropriated than hyperion.error
                "hyperion.error": {
                    "handlers": [
                        "file_errors",
                        "matrix_errors",
                        "console",
                    ],
                    "level": MINIMUM_LOG_LEVEL,
                },
                "hyperion.amap": {
                    "handlers": [
                        "file_amap",
                        "matrix_amap",
                        "console",
                    ],
                    "level": MINIMUM_LOG_LEVEL,
                },
                "hyperion.raffle": {
                    "handlers": [
                        "file_raffle",
                        "console",
                    ],
                    "level": MINIMUM_LOG_LEVEL,
                },
                # We disable "uvicorn.access" to replace it with our custom "hyperion.access" which add custom information like the request_id
                "uvicorn.access": {"handlers": []},
                "uvicorn.error": {
                    "handlers": [
                        "file_errors",
                        "matrix_errors",
                        "console",
                    ],
                    "level": MINIMUM_LOG_LEVEL,
                    "propagate": False,
                },
                # In production we use gunicorn instead of uvicorn
                # We disable "uvicorn.access" to replace it with our custom "hyperion.access" which add custom information like the request_id
                "gunicorn.access": {"handlers": []},
                "gunicorn.error": {
                    "handlers": [
                        "file_errors",
                        "matrix_errors",
                        "console",
                    ],
                    "level": MINIMUM_LOG_LEVEL,
                    "propagate": False,
                },
            },
        }

    def initialize_loggers(self, settings: Settings):
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

        # If logs/ folder does not exist, the logging module won't be able to create file handlers
        Path("logs/").mkdir(parents=True, exist_ok=True)

        config_dict = self.get_config_dict(settings=settings)
        logging.config.dictConfig(config_dict)

        loggers = [logging.getLogger(name) for name in config_dict["loggers"]]

        for logger in loggers:
            # If the logger does not have any handler, we don't need to create a QueueHandler
            if len(logger.handlers) == 0:
                continue

            # We create a queue where all log records will be added
            log_queue: queue.Queue[Any] = queue.Queue(-1)

            # queue_handler is the handler which adds all log records to the queue
            queue_handler = QueueHandler(log_queue)

            # The listener will watch the queue and let the previous handler process logs records in their own thread
            listener = QueueListener(
                log_queue,
                *logger.handlers,
                respect_handler_level=True,
            )
            listener.start()

            # We remove all previous handlers
            logger.handlers = []

            # We add our new queue_handler
            logger.addHandler(queue_handler)
