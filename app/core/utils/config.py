import tomllib
from functools import cached_property
from pathlib import Path
from typing import Any, ClassVar

import jwt
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import load_pem_private_key
from pydantic import BaseModel, computed_field, model_validator
from pydantic_settings import (
    BaseSettings,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
    YamlConfigSettingsSource,
)

from app.core.payment.types_payment import HelloAssoConfig, HelloAssoConfigName
from app.types.exceptions import (
    DotenvInvalidAuthClientNameInError,
    DotenvInvalidVariableError,
    DotenvMissingVariableError,
    InvalidRSAKeyInDotenvError,
)
from app.utils.auth import providers


class AuthClientConfig(BaseModel):
    """
    Configuration for an auth client.
    This class is used to store the configuration of an auth client.
    It is used to create an instance of the auth client.
    """

    secret: str | None = None
    redirect_uri: list[str]
    auth_client: str


class UserDemoFactoryConfig(BaseModel):
    """
    Configuration for the user demo factory.
    This class is used to store the configuration of the user demo factory.
    It is used to create an instance of the user demo factory.
    """

    firstname: str
    name: str
    nickname: str | None
    email: str
    password: str | None  # If None, the password will be generated randomly
    groups: list[str] = []  # Groups id to which the user will be added


class Settings(BaseSettings):
    """
    Settings for Hyperion
    The class is based on a env configuration file: `/.env.yaml`.

    All undefined variables will be populated from:
    1. An environment variable
    2. A yaml .env.yaml file
    3. The dotenv .env file

    Support for dotenv is kept for compatibility reason but is deprecated. YAML file should be used instead.

    See [Pydantic Settings documentation](https://docs.pydantic.dev/latest/concepts/pydantic_settings/#dotenv-env-support) for more information.
    See [FastAPI settings](https://fastapi.tiangolo.com/advanced/settings/) article for best practices with settings.

    To access these settings, the `get_settings` dependency should be used.
    """

    # By default, the settings are loaded from the `.env.yaml` or `.env` file but this behaviour can be overridden using
    # `_env_file` and `_yaml_file` parameter during instantiation
    # Ex: `Settings(_env_file=".env.dev", _yaml_file=".env.dev.yaml")`
    # Without this property, @cached_property decorator raise "TypeError: cannot pickle '_thread.RLock' object"
    # See https://github.com/samuelcolvin/pydantic/issues/1241
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        yaml_file="config.yaml",
        case_sensitive=False,
        extra="ignore",
    )

    # Currently Pydantic does not support overriding the yaml file path using the `_yaml_file` parameter
    # as it does for the `_env_file` parameter.
    # See https://github.com/pydantic/pydantic-settings/issues/259
    # We thus override the `_yaml_file` manually during the class instantiation
    # This should be changed in the future when Pydantic will support it
    _yaml_file: ClassVar[str]

    def __init__(self, _yaml_file, _env_file, **kwargs):
        Settings._yaml_file = _yaml_file
        super().__init__(_env_file=_env_file, **kwargs)

    # We configure sources that should be used to fill settings.
    # This method should return a tuple of sources
    # The order of these source define their precedence:
    # parameters passed an initialization arguments will have
    # precedence over environment variables, yaml file and dotenv
    # See https://docs.pydantic.dev/latest/concepts/pydantic_settings/#important-notes
    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            YamlConfigSettingsSource(settings_cls, yaml_file=cls._yaml_file),
            dotenv_settings,
        )

    ###############################################
    # Authorization using OAuth or Openid connect #
    ###############################################

    # ACCESS_TOKEN_SECRET_KEY should contain a random string with enough entropy (at least 32 bytes long) to securely sign all access_tokens for OAuth and Openid connect
    ACCESS_TOKEN_SECRET_KEY: str
    # RSA_PRIVATE_PEM_STRING should be a string containing the PEM certificate of a private RSA key. It will be used to sign id_tokens for Openid connect authentication
    # In the pem certificates newlines can be replaced by `\n`
    RSA_PRIVATE_PEM_STRING: bytes

    # Host or url of the instance of Hyperion
    # This url will be especially used for oidc/oauth2 discovery endpoint and links send be email
    # NOTE: A trailing / is required
    CLIENT_URL: str

    # Sometimes, when running third services with oidc inside Docker containers, and running Hyperion on your local device
    # you may need to use a different url for call made from docker and call made from your device
    # For exemple:
    #   you will access the login page from your browser http://localhost:8000/auth/authorize
    #   but the docker container should call http://host.docker.internal:8000/auth/token and not your localhost address
    # NOTE: A trailing / is required
    OVERRIDDEN_CLIENT_URL_FOR_OIDC: str | None = None

    # Configure AuthClients, to allow services to authenticate users using OAuth2 or Openid connect
    # The following format should be used in yaml config files:
    # ```yml
    # AUTH_CLIENTS:
    #   <ClientId>:
    #     secret: <ClientSecret>
    #     redirect_uri:
    #       - <RedirectUri1>
    #       - <RedirectUri2>
    #     auth_client: <AuthClientClassName>
    # ```
    # `AuthClientClassName` should be a class from `app.utils.auth.providers`
    # `secret` may be omitted to use PKCE instead of a client secret
    # NOTE: AUTH_CLIENTS property should never be used in the code. To get an auth client, use `KNOWN_AUTH_CLIENTS`
    AUTH_CLIENTS: dict[str, AuthClientConfig] = {}

    #####################
    # Hyperion settings #
    #####################

    # By default, only production's records are logged
    LOG_DEBUG_MESSAGES: bool = False

    # Origins for the CORS middleware. `["http://localhost"]` can be used for development.
    # See https://fastapi.tiangolo.com/tutorial/cors/
    # It should begin with 'http://' or 'https:// and should never end with a '/'
    CORS_ORIGINS: list[str]

    ############################
    # PostgreSQL configuration #
    ############################
    # If set, the application use a SQLite database instead of PostgreSQL, for testing or development purposes (if possible Postgresql should be used instead)
    SQLITE_DB: str | None = None
    POSTGRES_HOST: str = ""
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""
    POSTGRES_DB: str = ""
    POSTGRES_TZ: str = ""
    DATABASE_DEBUG: bool = False  # If True, the database will log all queries
    USE_FACTORIES: bool = (
        False  # If True, the database will be populated with fake data
    )
    FACTORIES_DEMO_USERS: list[UserDemoFactoryConfig] = []
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
    # Redis configuration #
    ########################
    # Redis configuration is needed to use the rate limiter, or multiple uvicorn workers
    # We use the default redis configuration, so the protected mode is enabled by default (see https://redis.io/docs/manual/security/#protected-mode)
    # If you want to use a custom configuration, a password and a specific binds should be used to avoid security issues
    REDIS_HOST: str | None = None
    REDIS_PORT: int = 6379
    REDIS_PASSWORD: str | None = None
    REDIS_LIMIT: int = 1000
    REDIS_WINDOW: int = 60

    # Rate limit requests based on REDIS_LIMIT and REDIS_WINDOW
    # A working Redis client is required to use the rate limiter
    ENABLE_RATE_LIMITER: bool = True

    ##########################
    # Firebase Configuration #
    ##########################
    # To enable Firebase push notification capabilities, a JSON key file named `firebase.json` should be placed at Hyperion root.
    # This file can be created and downloaded from [Google cloud, IAM and administration, Service account](https://console.cloud.google.com/iam-admin/serviceaccounts) page.
    USE_FIREBASE: bool = False

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

    ####################
    # S3 configuration #
    ####################
    # S3 configuration is needed to use the S3 storage for MyECLPay logs

    S3_BUCKET_NAME: str | None = None
    S3_ACCESS_KEY_ID: str | None = None
    S3_SECRET_ACCESS_KEY: str | None = None

    ##############
    # Google API #
    ##############
    # Google API is used to upload files to Google Drive
    # See ./app/utils/google_api/README.md for more information
    GOOGLE_API_CLIENT_ID: str | None = None
    GOOGLE_API_CLIENT_SECRET: str | None = None

    # Drive configuration for the raid registering app
    RAID_DRIVE_REFRESH_TOKEN: str | None = None
    RAID_DRIVE_API_KEY: str | None = None
    RAID_DRIVE_CLIENT_ID: str | None = None
    RAID_DRIVE_CLIENT_SECRET: str | None = None

    ###########################
    # HelloAsso configuration #
    ###########################

    # To be able to use payment features using HelloAsso, you need to set a client id, secret for their API
    # HelloAsso provide a sandbox to be able to realize tests
    # HELLOASSO_API_BASE should have the format: `api.helloasso-sandbox.com`
    # HelloAsso only allow 20 simultaneous active access token. Note that each Hyperion worker will need its own access token.

    # {"<ConfigName>": {"helloasso_client_id": "<id>", "helloasso_client_secret" :"<secret>", "helloasso_slug": "<slug>", "redirection_uri": "<redirection_uri>"}}
    HELLOASSO_CONFIGURATIONS: dict[HelloAssoConfigName, HelloAssoConfig] = {}
    HELLOASSO_API_BASE: str | None = None

    # Maximum wallet balance for MyECLPay in cents, we will prevent user from adding more money to their wallet if it will make their balance exceed this value
    MYECLPAY_MAXIMUM_WALLET_BALANCE: int = 1000

    # Trusted urls is a list of redirect payment url that can be trusted by Hyperion.
    # These urls will be used to validate the redirect url provided by the front
    TRUSTED_PAYMENT_REDIRECT_URLS: list[str] = []

    # MyECLPay requires an external service to recurrently check for transactions and state integrity, this service needs an access to all the data related to the transactions and the users involved
    # This service will use a special token to access the data
    # If this token is not set, the service will not be able to access the data and no integrity check will be performed
    MYECLPAY_DATA_VERIFIER_ACCESS_TOKEN: str | None = None

    ###################
    # Tokens validity #
    ###################

    USER_ACTIVATION_TOKEN_EXPIRE_HOURS: int = 24
    PASSWORD_RESET_TOKEN_EXPIRE_HOURS: int = 12
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 14  # 14 days
    AUTHORIZATION_CODE_EXPIRE_MINUTES: int = 7
    MYECLPAY_MANAGER_TRANSFER_TOKEN_EXPIRES_MINUTES: int = 20

    #############################
    # pyproject.toml parameters #
    #############################

    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def HYPERION_VERSION(cls) -> str:
        with Path("pyproject.toml").open("rb") as pyproject_binary:
            pyproject = tomllib.load(pyproject_binary)
        return str(pyproject["project"]["version"])

    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def MINIMAL_TITAN_VERSION_CODE(cls) -> str:
        with Path("pyproject.toml").open("rb") as pyproject_binary:
            pyproject = tomllib.load(pyproject_binary)
        return str(pyproject["project"]["minimal-titan-version-code"])

    ######################################
    # Automatically generated parameters #
    ######################################

    # The following properties can not be instantiated as class variables as them need to be computed using another property from the class,
    # which won't be available before the .env file parsing.
    # We thus decide to use the decorator `@property` to make these methods usable as properties and not functions: as properties: Settings.RSA_PRIVATE_KEY, Settings.RSA_PUBLIC_KEY and Settings.RSA_PUBLIC_JWK
    # Their values should not change, we don't want to recompute all of them overtimes. We use the `@lru_cache` decorator to cache them.
    # The combination of `@property` and `@lru_cache` should be replaced by `@cached_property`
    # See https://docs.python.org/3.8/library/functools.html?highlight=#functools.cached_property

    @computed_field  # type: ignore[prop-decorator] # Current issue with mypy, see https://docs.pydantic.dev/2.0/usage/computed_fields/ and https://github.com/python/mypy/issues/1362
    @cached_property
    def RSA_PRIVATE_KEY(cls) -> rsa.RSAPrivateKey:
        # https://cryptography.io/en/latest/hazmat/primitives/asymmetric/serialization/#module-cryptography.hazmat.primitives.serialization
        private_key = load_pem_private_key(cls.RSA_PRIVATE_PEM_STRING, password=None)
        if not isinstance(private_key, rsa.RSAPrivateKey):
            raise InvalidRSAKeyInDotenvError(private_key.__class__.__name__)
        return private_key

    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def RSA_PUBLIC_KEY(cls) -> rsa.RSAPublicKey:
        return cls.RSA_PRIVATE_KEY.public_key()

    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def RSA_PUBLIC_JWK(cls) -> dict[str, list[dict[str, Any]]]:
        # See https://github.com/jpadilla/pyjwt/issues/880
        algo = jwt.get_algorithm_by_name("RS256")
        jwk = algo.to_jwk(cls.RSA_PUBLIC_KEY, as_dict=True)
        jwk.update(
            {
                "use": "sig",
                "kid": "RSA-JWK-1",  # The kid allows to identify the key in the JWKS, it should match the kid in the token header
            },
        )
        return {"keys": [jwk]}

    # This property parse AUTH_CLIENTS to create a dictionary of auth clients:
    # {"client_id": AuthClientClassInstance}
    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def KNOWN_AUTH_CLIENTS(cls) -> dict[str, providers.BaseAuthClient]:
        clients = {}
        auth_client_class: type[providers.BaseAuthClient]
        for client_id, configuration in cls.AUTH_CLIENTS.items():
            try:
                auth_client_class = getattr(
                    providers,
                    configuration.auth_client,
                )
            except AttributeError as error:
                raise DotenvInvalidAuthClientNameInError(
                    configuration.auth_client,
                ) from error

            # We can create a new instance of the auth_client_class with the client id and secret
            clients[client_id] = auth_client_class(
                client_id=client_id,
                # If the secret is empty, this mean the client is expected to use PKCE
                # We need to pass a None value to the auth_client_class instead of an other falsy value
                secret=configuration.secret or None,
                redirect_uri=configuration.redirect_uri,
            )
        return clients

    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def OIDC_ISSUER(cls) -> str:
        return cls.CLIENT_URL[:-1]

    @computed_field  # type: ignore[prop-decorator]
    @cached_property
    def REDIS_URL(cls) -> str | None:
        if cls.REDIS_HOST:
            # We need to include `:` before the password
            return (
                f"redis://:{cls.REDIS_PASSWORD or ''}@{cls.REDIS_HOST}:{cls.REDIS_PORT}"
            )
        return None

    #######################################
    #          Fields validation          #
    #######################################

    # Validators may be used to perform more complexe validation
    # For example, we can check that at least one of two optional fields is set or that the RSA key is provided and valid

    @model_validator(mode="after")
    def check_client_urls(self) -> "Settings":
        """
        All fields are optional, but the dotenv should configure SQLITE_DB or a Postgres database
        """
        if not self.CLIENT_URL[-1] == "/":
            raise DotenvInvalidVariableError(  # noqa: TRY003
                "CLIENT_URL must contains a trailing slash",
            )
        if (
            self.OVERRIDDEN_CLIENT_URL_FOR_OIDC
            and not self.OVERRIDDEN_CLIENT_URL_FOR_OIDC[-1] == "/"
        ):
            raise DotenvInvalidVariableError(  # noqa: TRY003
                "OVERRIDDEN_CLIENT_URL_FOR_OIDC must contains a trailing slash",
            )

        return self

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
            raise DotenvMissingVariableError(  # noqa: TRY003
                "Either SQLITE_DB or POSTGRES_HOST, POSTGRES_USER, POSTGRES_PASSWORD and POSTGRES_DB",
            )

        return self

    @model_validator(mode="after")
    def check_secrets(self) -> "Settings":
        if not self.ACCESS_TOKEN_SECRET_KEY:
            raise DotenvMissingVariableError(
                "ACCESS_TOKEN_SECRET_KEY",
            )

        if not self.RSA_PRIVATE_PEM_STRING:
            raise DotenvMissingVariableError(
                "RSA_PRIVATE_PEM_STRING",
            )

        return self

    @model_validator(mode="after")
    def init_cached_property(self) -> "Settings":
        """
        Cached property are not computed during the instantiation of the class, but when they are accessed for the first time.
        By calling them in this validator, we force their initialization during the instantiation of the class.
        This allow them to raise error on Hyperion startup if they are not correctly configured instead of creating an error on runtime.
        """
        self.HYPERION_VERSION  # noqa: B018
        self.MINIMAL_TITAN_VERSION_CODE  # noqa: B018
        self.KNOWN_AUTH_CLIENTS  # noqa: B018
        self.RSA_PRIVATE_KEY  # noqa: B018
        self.RSA_PUBLIC_KEY  # noqa: B018
        self.RSA_PUBLIC_JWK  # noqa: B018

        return self


def construct_prod_settings() -> Settings:
    """
    Return the production settings
    """
    return Settings(_env_file=".env", _yaml_file="config.yaml")
