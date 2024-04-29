from pydantic_settings import BaseSettings, SettingsConfigDict


class DriveSettings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".google.env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    REFRESH_TOKEN: str
    API_KEY: str
    CLIENT_ID: str
    CLIENT_SECRET: str
