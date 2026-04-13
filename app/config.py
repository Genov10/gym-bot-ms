from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    telegram_bot_token: str
    database_url: str

    external_api_base_url: str = "http://localhost:8080"
    external_api_key: str | None = None
    external_api_timeout_sec: float = 30.0


settings = Settings()
