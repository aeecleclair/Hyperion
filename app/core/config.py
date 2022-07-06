from jose import jwk
from pydantic import BaseSettings

from app.utils.auth.providers import BaseAuthClient


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

    # TODO: rename
    # Authorization using JWT
    ACCESS_TOKEN_SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_MINUTES = 120

    # TODO: remove the DOCKER_URL
    CLIENT_URL = "http://127.0.0.1:8000/"
    DOCKER_URL = "http://host.docker.internal:8000/"  # During dev, docker container can not directly access the client url
    # Openid connect issuer name
    AUTH_ISSUER = "hyperion"
    RSA_PRIVATE_PEM_STRING: str

    @property
    def RSA_PRIVATE_KEY(self):
        return jwk.construct(self.RSA_PRIVATE_PEM_STRING, algorithm="RS256")

    @property
    def RSA_PUBLIC_KEY(self):
        return self.RSA_PRIVATE_KEY.public_key()

    @property
    def RSA_PUBLIC_JWK(self):
        JWK = self.RSA_PUBLIC_KEY.to_dict().update(
            {
                "use": "sig",
                "kid": "RSA-JWK-1",  # The kid allows to identify the key in the JWKS, it should match the kid in the token header
            }
        )
        return {"keys": [JWK]}

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

    # Auth configuration
    # Format: {"client_id": ProviderClass}
    # TODO: How do we store the secret properly ?
    KNOWN_AUTH_CLIENTS = {
        "client_id": BaseAuthClient,
        "5507cc3a-fd29-11ec-b939-0242ac120002": BaseAuthClient,
    }

    class Config:
        # By default, the settings are loaded from the `.env` file but this behaviour can be overridden by using
        # `_env_file` parameter during instanciation
        # Ex: `Settings(_env_file=".env.dev")`
        env_file = ".env"
        env_file_encoding = "utf-8"
