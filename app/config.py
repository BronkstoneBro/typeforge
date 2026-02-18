from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    DATABASE_URL: str = "postgresql+asyncpg://typeforge:typeforge@db:5432/typeforge"
    SELENIUM_REMOTE_URL: str = "http://selenium:4444/wd/hub"
    SCREENSHOTS_DIR: str = "/app/screenshots"
    LOG_LEVEL: str = "INFO"


settings = Settings()
