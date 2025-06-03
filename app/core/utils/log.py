import logging
import logging.config
import queue
from enum import Enum
from logging.handlers import QueueHandler, QueueListener
from pathlib import Path
from typing import Any

import uvicorn

from app.core.utils.config import Settings


class ColoredConsoleFormatter(uvicorn.logging.DefaultFormatter):
    class ConsoleColors(str, Enum):
        """Colors can be found here: https://talyian.github.io/ansicolors/"""

        DEBUG = "\033[38;5;12m"
        INFO = "\033[38;5;10m"
        WARNING = "\033[38;5;11m"
        ERROR = "\033[38;5;9m"
        CRITICAL = "\033[38;5;1m"
        BOLD = "\033[1m"
        END = "\033[0m"

    def __init__(self, *args, **kwargs):
        super().__init__(datefmt="%d-%b-%y %H:%M:%S")

        self.formatters = {}

        for level in [
            logging.DEBUG,
            logging.INFO,
            logging.WARNING,
            logging.ERROR,
            logging.CRITICAL,
        ]:
            fmt = (
                "%(asctime)s - %(name)s - "
                + self.ConsoleColors.BOLD
                + "%(levelname)s"
                + self.ConsoleColors.END
                + " - "
                + self.ConsoleColors[logging.getLevelName(level)]
                + "%(message)s"
                + self.ConsoleColors.END
            )
            level_formatter = logging.Formatter(fmt, self.datefmt)
            self.formatters[level] = level_formatter

    def format(self, record: logging.LogRecord) -> str:
        formatter: logging.Formatter = self.formatters.get(
            record.levelno,
            self.formatters[logging.ERROR],
        )
        return formatter.format(record)


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
    MATRIX_LOG_FORMAT: str = "%(asctime)s - %(name)s - <code>%(levelname)s</code> - <font color ='green'>%(message)s</font>"
    MYECLPAY_LOG_FORMAT: str = "%(message)s"  # Do not change at any cost

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
                    "()": "app.core.utils.log.ColoredConsoleFormatter",
                },
                "matrix": {
                    "format": self.MATRIX_LOG_FORMAT,
                    "datefmt": "%d-%b-%y %H:%M:%S",
                },
                "myeclpay": {
                    "format": self.MYECLPAY_LOG_FORMAT,
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
                "myeclpay_s3": {
                    "formatter": "myeclpay",
                    "class": "app.utils.loggers_tools.s3_handler.S3LogHandler",
                    "failure_logger": "hyperion.myeclpay.fallback",
                    "s3_bucket_name": settings.S3_BUCKET_NAME,
                    "s3_access_key_id": settings.S3_ACCESS_KEY_ID,
                    "s3_secret_access_key": settings.S3_SECRET_ACCESS_KEY,
                    "folder": "myeclpay",
                    "retention": 365 * 10,
                },
                "s3": {
                    "formatter": "myeclpay",
                    "class": "app.utils.loggers_tools.s3_handler.S3LogHandler",
                    "failure_logger": "hyperion.s3.fallback",
                    "s3_bucket_name": settings.S3_BUCKET_NAME,
                    "s3_access_key_id": settings.S3_ACCESS_KEY_ID,
                    "s3_secret_access_key": settings.S3_SECRET_ACCESS_KEY,
                    "folder": "",
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
                "file_myeclpay": {
                    # file_myeclpay is there to log all operations related to MyECLPay that failed to be logged in the S3 bucket
                    "formatter": "default",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": "logs/myeclpay.log",
                    "maxBytes": 1024 * 1024 * 40,  # ~ 40 MB
                    "backupCount": 100,
                    "level": "DEBUG",
                },
                "file_s3": {
                    # file_myeclpay is there to log all operations related to MyECLPay that failed to be logged in the S3 bucket
                    "formatter": "default",
                    "class": "logging.handlers.RotatingFileHandler",
                    "filename": "logs/s3.log",
                    "maxBytes": 1024 * 1024 * 40,  # ~ 40 MB
                    "backupCount": 100,
                    "level": "DEBUG",
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
                "hyperion.myeclpay.fallback": {
                    "handlers": [
                        "file_myeclpay",
                        "matrix_errors",
                        "console",
                    ],
                    "level": "DEBUG",
                    "propagate": False,
                },
                "hyperion.myeclpay": {
                    "handlers": [
                        "myeclpay_s3",
                    ],
                    "level": "DEBUG",
                },
                "hyperion.s3.fallback": {
                    "handlers": [
                        "file_s3",
                        "matrix_errors",
                        "console",
                    ],
                    "level": "DEBUG",
                    "propagate": False,
                },
                "hyperion.s3": {
                    "handlers": [
                        "s3",
                    ],
                    "level": "DEBUG",
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
                "scheduler": {"handlers": ["console"], "level": MINIMUM_LOG_LEVEL},
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
                "arq.worker": {
                    "handlers": [
                        "console",
                        "file_errors",
                        "matrix_errors",
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
