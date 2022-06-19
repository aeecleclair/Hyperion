from cryptography.hazmat.primitives.asymmetric import rsa
from pydantic import BaseSettings


class Settings(BaseSettings):
    """
    Settings for Hyperion
    The class is based on a dotenv file: `/.env`. All undefined variables will be populated from:
    1. An environment variable
    2. The dotenv .env file

    See [Pydantic Settings documentation](https://pydantic-docs.helpmanual.io/usage/settings/#dotenv-env-support) for more informations.
    See [FastAPI settings](https://fastapi.tiangolo.com/advanced/settings/) article for best practices with settings.

    To access these settings, the `get_settings` dependency should be used.
    """

    # Authorization using JWT
    ACCESS_TOKEN_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES = 30

    # Tokens validity
    USER_ACTIVATION_TOKEN_EXPIRES_HOURS = 24
    PASSWORD_RESET_TOKEN_EXPIRES_HOURS = 12

    # TODO: comment and rename
    RSA_PRIVATE_PEM_STRING: str

    # By default, only production's records are logged
    LOG_DEBUG_MESSAGES: bool | None

    ########################
    # Matrix configuration #
    ########################
    # Matrix configuration is optional. If configured, Hyperion will be able to send messages to a Matrix server.
    # This configuration will be used to send errors messages.
    # If the following parameters are not set, logging won't use the Matrix handler
    # MATRIX_SERVER_BASE_URL is optional, the official Matrix server will be used if not configured
    MATRIX_SERVER_BASE_URL: str | None
    MATRIX_USER_NAME: str | None
    MATRIX_USER_PASSWORD: str | None
    MATRIX_LOG_ERROR_ROOM_ID: str | None

    # SMTP configuration using starttls
    SMTP_ACTIVE: bool
    SMTP_PORT: int
    SMTP_SERVER: str
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_EMAIL: str

    class Config:
        # By default, the settings are loaded from the `.env` file but this behaviour can be overridden by using
        # `_env_file` parameter during instanciation
        # Ex: `Settings(_env_file=".env.dev")`
        env_file = ".env"
        env_file_encoding = "utf-8"
