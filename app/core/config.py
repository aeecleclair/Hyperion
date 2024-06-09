from functools import cached_property
from typing import Any

from jose import jwk
from jose.exceptions import JWKError
from pydantic import computed_field, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.utils.auth import providers


class Settings(BaseSettings):
    """
    Settings for Hyperion
    The class is based on a dotenv file: `/.env`. All undefined variables will be populated from:
    1. An environment variable
    2. The dotenv .env file

    See [Pydantic Settings documentation](https://pydantic-docs.helpmanual.io/usage/settings/#dotenv-env-support) for more information.
    See [FastAPI settings](https://fastapi.tiangolo.com/advanced/settings/) article for best practices with settings.

    To access these settings, the `get_settings` dependency should be used.
    """

    # By default, the settings are loaded from the `.env` file but this behaviour can be overridden by using
    # `_env_file` parameter during instantiation
    # Ex: `Settings(_env_file=".env.dev")`
    # Without this property, @cached_property decorator raise "TypeError: cannot pickle '_thread.RLock' object"
    # See https://github.com/samuelcolvin/pydantic/issues/1241
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # NOTE: Variables without a value should not be configured in this class, but added to the dotenv .env file

    #####################################
    # SMTP configuration using starttls #
    #####################################

    SMTP_ACTIVE: bool = False
    SMTP_PORT: int
    SMTP_SERVER: str
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_EMAIL: str

    ########################
    # Matrix configuration #
    ########################
    # Matrix configuration is optional. If configured, Hyperion will be able to send messages to a Matrix server.
    # This configuration will be used to send errors messages.
    # If the following parameters are not set, logging won't use the Matrix handler
    # MATRIX_SERVER_BASE_URL is optional, the official Matrix server will be used if not configured
    # Advanced note: Username and password will be used to ask for an access token. A Matrix custom client `Hyperion` is used to make all requests
    MATRIX_SERVER_BASE_URL: str | None = None
    MATRIX_TOKEN: str | None = None
    MATRIX_LOG_ERROR_ROOM_ID: str | None = None
    MATRIX_LOG_AMAP_ROOM_ID: str | None = None

    #############################
    # Token to use the TMDB API #
    #############################
    # This API key is required in order to send requests to the Internet Movie Database.
    # It is only used in the Cinema module.
    THE_MOVIE_DB_API: str | None = None

    ########################
    # Redis configuration #
    ########################
    # Redis configuration is needed to use the rate limiter
    # We use the default redis configuration, so the protected mode is enabled by default (see https://redis.io/docs/manual/security/#protected-mode)
    # If you want to use a custom configuration, a password and a specific binds should be used to avoid security issues
    REDIS_HOST: str
    REDIS_PORT: int
    REDIS_PASSWORD: str | None = None
    REDIS_LIMIT: int
    REDIS_WINDOW: int

    ##########################
    # Firebase Configuration #
    ##########################
    # To enable Firebase push notification capabilities, a JSON key file named `firebase.json` should be placed at Hyperion root.
    # This file can be created and downloaded from [Google cloud, IAM and administration, Service account](https://console.cloud.google.com/iam-admin/serviceaccounts) page.
    USE_FIREBASE: bool = False

    ############################
    # PostgreSQL configuration #
    ############################
    # PostgreSQL configuration is needed to use the database
    SQLITE_DB: str | None = (
        None  # If set, the application use a SQLite database instead of PostgreSQL, for testing or development purposes (should not be used if possible)
    )
    POSTGRES_HOST: str = ""
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""
    POSTGRES_TZ: str = ""
    DATABASE_DEBUG: bool = False  # If True, the database will log all queries

    #####################
    # Hyperion settings #
    #####################

    # By default, only production's records are logged
    LOG_DEBUG_MESSAGES: bool | None

    # Hyperion follows Semantic Versioning
    # https://semver.org/
    HYPERION_VERSION: str = "2.5.2-alpha"
    MINIMAL_TITAN_VERSION_CODE: int = 113

    MINIMAL_TITAN_VERSION: str = "0.0.1"  # deprecated, use MINIMAL_TITAN_VERSION_CODE

    # Origins for the CORS middleware. `["http://localhost"]` can be used for development.
    # See https://fastapi.tiangolo.com/tutorial/cors/
    # It should begin with 'http://' or 'https:// and should never end with a '/'
    CORS_ORIGINS: list[str]

    ###################
    # Tokens validity #
    ###################

    USER_ACTIVATION_TOKEN_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 12
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 14  # 14 days
    AUTHORIZATION_CODE_EXPIRE_MINUTES: int = 7

    ###############################################
    # Authorization using OAuth or Openid connect #
    ###############################################

    # ACCESS_TOKEN_SECRET_KEY should contain a random string with enough entropy (at least 32 bytes long) to securely sign all access_tokens for OAuth and Openid connect
    ACCESS_TOKEN_SECRET_KEY: str
    # RSA_PRIVATE_PEM_STRING should be a string containing the PEM certificate of a private RSA key. It will be used to sign id_tokens for Openid connect authentication
    # In the pem certificates newlines can be replaced by `\n`
    RSA_PRIVATE_PEM_STRING: str

    # Host or url of the API, used for Openid connect discovery endpoint
    # NOTE: A trailing / is required
    CLIENT_URL: str
    DOCKER_URL: (
        str  # During dev, docker container can not directly access the client url
    )

    # Openid connect issuer name
    AUTH_ISSUER: str = "hyperion"

    # Add an AUTH_CLIENTS variable to the .env dotenv to configure auth clients
    # This variable should have the format: [["client id", "client secret", "redirect_uri", "app.utils.auth.providers class name"]]
    # Use an empty secret `null` or `""` to use PKCE instead of a client secret
    # Ex: AUTH_CLIENTS=[["Nextcloudclient", "supersecret", "https://mynextcloud.instance/", "NextcloudAuthClient"], ["Piwigo", "secret2", "https://mypiwigo.instance/", "BaseAuthClient"], ["mobileapp", null, "https://titan/", "BaseAuthClient"]]
    # NOTE: AUTH_CLIENTS property should never be used in the code. To get an auth client, use `KNOWN_AUTH_CLIENTS`
    AUTH_CLIENTS: list[tuple[str, str | None, list[str], str]]

    ######################################
    # Automatically generated parameters #
    ######################################

    # The following properties can not be instantiated as class variables as them need to be computed using another property from the class,
    # which won't be available before the .env file parsing.
    # We thus decide to use the decorator `@property` to make these methods usable as properties and not functions: as properties: Settings.RSA_PRIVATE_KEY, Settings.RSA_PUBLIC_KEY and Settings.RSA_PUBLIC_JWK
    # Their values should not change, we don't want to recompute all of them overtimes. We use the `@lru_cache` decorator to cache them.
    # The combination of `@property` and `@lru_cache` should be replaced by `@cached_property`
    # See https://docs.python.org/3.8/library/functools.html?highlight=#functools.cached_property

    @computed_field  # type: ignore[misc] # Current issue with mypy, see https://docs.pydantic.dev/2.0/usage/computed_fields/ and https://github.com/python/mypy/issues/1362
    @cached_property
    def RSA_PRIVATE_KEY(cls) -> Any:
        return jwk.construct(cls.RSA_PRIVATE_PEM_STRING, algorithm="RS256")

    @computed_field  # type: ignore[misc]
    @cached_property
    def RSA_PUBLIC_KEY(cls) -> Any:
        return cls.RSA_PRIVATE_KEY.public_key()

    @computed_field  # type: ignore[misc]
    @cached_property
    def RSA_PUBLIC_JWK(cls) -> dict[str, list[dict[str, str]]]:
        JWK = cls.RSA_PUBLIC_KEY.to_dict()
        JWK.update(
            {
                "use": "sig",
                "kid": "RSA-JWK-1",  # The kid allows to identify the key in the JWKS, it should match the kid in the token header
            },
        )
        return {"keys": [JWK]}

    # Tokens validity
    USER_ACTIVATION_TOKEN_EXPIRES_HOURS: int = 24
    PASSWORD_RESET_TOKEN_EXPIRES_HOURS: int = 12

    # This property parse AUTH_CLIENTS to create a dictionary of auth clients:
    # {"client_id": AuthClientClassInstance}
    @computed_field  # type: ignore[misc]
    @cached_property
    def KNOWN_AUTH_CLIENTS(cls) -> dict[str, providers.BaseAuthClient]:
        clients = {}
        for client_id, secret, redirect_uri, auth_client_name in cls.AUTH_CLIENTS:
            try:
                auth_client_class: type[providers.BaseAuthClient] = getattr(
                    providers,
                    auth_client_name,
                )
            except AttributeError as error:
                # logger.error()
                raise ValueError(
                    f".env AUTH_CLIENTS is invalid: {auth_client_name} is not an auth_client from app.utils.auth.providers",
                ) from error
            # If the secret is empty, this mean the client is expected to use PKCE
            # We need to pass a None value to the auth_client_class
            if not secret:
                secret = None
            # We can create a new instance of the auth_client_class with the client id and secret
            clients[client_id] = auth_client_class(
                client_id=client_id,
                secret=secret,
                redirect_uri=redirect_uri,
            )

        return clients

    #######################################
    #          Fields validation          #
    #######################################

    # Validators may be used to perform more complexe validation
    # For example, we can check that at least one of two optional fields is set or that the RSA key is provided and valid

    @model_validator(mode="after")
    def check_database_settings(self) -> "Settings":
        """
        All fields are optional, but the dotenv should configure SQLITE_DB or a Postgres database
        """
        if not (
            self.SQLITE_DB
            or (
                self.POSTGRES_HOST
                and self.POSTGRES_USER
                and self.POSTGRES_PASSWORD
                and self.POSTGRES_DB
            )
        ):
            raise ValueError(
                "Either SQLITE_DB or POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD and POSTGRES_DB should be configured in the dotenv",
            )

        return self

    @model_validator(mode="after")
    def check_secrets(self) -> "Settings":
        if not self.ACCESS_TOKEN_SECRET_KEY:
            raise ValueError(
                "ACCESS_TOKEN_SECRET_KEY should be configured in the dotenv",
            )

        if not self.RSA_PRIVATE_PEM_STRING:
            raise ValueError(
                "RSA_PRIVATE_PEM_STRING should be configured in the dotenv",
            )

        try:
            jwk.construct(self.RSA_PRIVATE_PEM_STRING, algorithm="RS256")
        except JWKError as error:
            raise ValueError("RSA_PRIVATE_PEM_STRING is not a valid RSA key") from error

        return self

    @model_validator(mode="after")
    def init_cached_property(self) -> "Settings":
        """
        Cached property are not computed during the instantiation of the class, but when they are accessed for the first time.
        By calling them in this validator, we force their initialization during the instantiation of the class.
        This allow them to raise error on Hyperion startup if they are not correctly configured instead of creating an error on runtime.
        """
        self.KNOWN_AUTH_CLIENTS  # noqa
        self.RSA_PRIVATE_KEY  # noqa
        self.RSA_PUBLIC_KEY  # noqa
        self.RSA_PUBLIC_JWK  # noqa

        return self
