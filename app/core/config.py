from functools import cached_property

from jose import jwk
from pydantic import BaseSettings

from app.utils.auth import providers


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

    # NOTE: Variables without a value should not be configured in this class, but added to the dotenv .env file

    #####################################
    # SMTP configuration using starttls #
    #####################################

    SMTP_ACTIVE: bool
    SMTP_PORT: int
    SMTP_SERVER: str
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_EMAIL: str

    ###################
    # Tokens validity #
    ###################

    USER_ACTIVATION_TOKEN_EXPIRES_HOURS = 24
    PASSWORD_RESET_TOKEN_EXPIRES_HOURS = 12
    ACCESS_TOKEN_EXPIRE_MINUTES = 30
    REFRESH_TOKEN_EXPIRE_MINUTES = 120
    AUTHORIZATION_CODE_EXPIRE_MINUTES = 7

    ###############################################
    # Authorization using OAuth or Openid connect #
    ###############################################

    # ACCESS_TOKEN_SECRET_KEY should contain a random string with enough entropy to securely sign all access_tokens for OAuth and Openid connect
    ACCESS_TOKEN_SECRET_KEY: str
    # RSA_PRIVATE_PEM_STRING should be a string containing the PEM certificate of a private RSA key. It will be used to sign id_tokens for Openid connect authentification
    RSA_PRIVATE_PEM_STRING: str

    # Host or url of the API, used for Openid connect discovery endpoint
    # NOTE: A trailing / is required
    CLIENT_URL = "http://127.0.0.1:8000/"
    DOCKER_URL = "http://host.docker.internal:8000/"  # During dev, docker container can not directly access the client url

    # Openid connect issuer name
    AUTH_ISSUER = "hyperion"

    # Add an AUTH_CLIENTS variable to the .env dotenv to configure auth clients
    # This variable should have the format: [["client id", "client secret", "app.utils.auth.providers class name"]]
    # Use an empty secret `null` or `""` to use PKCE instead of a client secret
    # Ex: AUTH_CLIENTS=[["Nextcloudclient", "supersecret", "NextcloudAuthClient"], ["Piwigo", "secret2", "BaseAuthClient"], , ["mobileapp", null, "BaseAuthClient"]]
    # NOTE: AUTH_CLIENTS property should never be used in the code. To get an auth client, use `KNOWN_AUTH_CLIENTS`
    AUTH_CLIENTS: list[tuple[str, str | None, str]]

    ######################################
    # Automatically generated parameters #
    ######################################

    # The following properties can not be instantiated as class variables as them need to be computed using an other property from the class,
    # which wont be available before the .env file parsing.
    # We thus decide to use the decorator `@property` to make these methods usable as properties and not functions: as properties: Settings.RSA_PRIVATE_KEY, Settings.RSA_PUBLIC_KEY and Settings.RSA_PUBLIC_JWK
    # Their values should not change, we don't want to recompute all of them overtimes. We use the `@lru_cache` decorator to cache them.
    # The combinaison of `@property` and `@lru_cache` should be replaced by `@cached_property`
    # See https://docs.python.org/3.8/library/functools.html?highlight=#functools.cached_property

    @cached_property
    def RSA_PRIVATE_KEY(cls):
        return jwk.construct(cls.RSA_PRIVATE_PEM_STRING, algorithm="RS256")

    @cached_property
    def RSA_PUBLIC_KEY(cls):
        return cls.RSA_PRIVATE_KEY.public_key()

    @cached_property
    def RSA_PUBLIC_JWK(cls):
        JWK = cls.RSA_PUBLIC_KEY.to_dict()
        JWK.update(
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

    # Add an AUTH_CLIENTS variable to the .env dotenv to configure auth clients
    # This variable should have the format: [["client id", "client secret", "app.utils.auth.providers class name"]]
    # Use an empty secret `null` or `""` to use PKCE instead of a client secret
    # Ex: AUTH_CLIENTS=[["Nextcloudclient", "supersecret", "NextcloudAuthClient"], ["Piwigo", "secret2", "BaseAuthClient"], , ["mobileapp", null, "BaseAuthClient"]]
    AUTH_CLIENTS: list[tuple[str, str | None, str]]
    # The AUTH_CLIENTS property should never be used in the code. To get an auth client, use the following KNOWN_AUTH_CLIENTS

    # This property parse AUTH_CLIENTS to create a dictionary of auth clients:
    # {"client_id": AuthClientClassInstance}
    @cached_property
    def KNOWN_AUTH_CLIENTS(cls):
        clients = {}
        for client_id, secret, auth_client_name in cls.AUTH_CLIENTS:
            try:
                auth_client_class: type[providers.BaseAuthClient] = getattr(
                    providers, auth_client_name
                )
            except AttributeError:
                # logger.error()
                raise ValueError(
                    ".env AUTH_CLIENTS is invalid: {auth_client_name} is not an auth_client from app.utils.auth.providers"
                )
            # If the secret is empty, this mean the client is expected to use PKCE
            # We need to pass a None value to the auth_client_class
            if not secret:
                secret = None
            # We can create a new instance of the auth_client_class with the client id and secret
            clients[client_id] = auth_client_class(client_id=client_id, secret=secret)

        return clients

    class Config:
        # By default, the settings are loaded from the `.env` file but this behaviour can be overridden by using
        # `_env_file` parameter during instanciation
        # Ex: `Settings(_env_file=".env.dev")`
        env_file = ".env"
        env_file_encoding = "utf-8"

        # Without this property, @cached_property decorator raise "TypeError: cannot pickle '_thread.RLock' object"
        # See https://github.com/samuelcolvin/pydantic/issues/1241
        keep_untouched = (cached_property,)
