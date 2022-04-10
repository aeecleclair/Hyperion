from pydantic import BaseSettings


class Settings(BaseSettings):
    """
    Settings for Hyperion
    The class is based on a dotenv file: `/.env`. All undefined variables will be populated from:
    1. An environment variable
    2. The dotenv .env file

    See [Pydantic Settings documentation](https://pydantic-docs.helpmanual.io/usage/settings/#dotenv-env-support) for more informations
    """

    # Token validity
    USER_ACTIVATION_TOKEN_EXPIRES_HOURS = 24
    PASSWORD_RESET_TOKEN_EXPIRES_HOURS = 12

    # SMTP configuration using starttls
    SMTP_ACTIVE: bool
    SMTP_PORT: int
    SMTP_SERVER: str
    SMTP_USERNAME: str
    SMTP_PASSWORD: str
    SMTP_EMAIL: str

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


settings = Settings()
