from pydantic import BaseSettings


class Settings(BaseSettings):
    SECRET_KEY: str = "f586300d36595da3bb5698a1efc32b34acf26010bcd1802f45ed9575ba173b22"
    # 30 minutes
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30


settings = Settings()
