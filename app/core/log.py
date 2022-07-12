from pydantic import BaseModel


class LogConfig(BaseModel):
    """
    Logging configuration to be set for the server
    We convert this class to a dict to be used by Python logging module
    """

    LOG_FORMAT: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
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
    }
    handlers = {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
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
            "handlers": ["file_access", "file_errors", "default"],
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
