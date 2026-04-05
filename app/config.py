from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    All app configuration lives here.

    pydantic-settings automatically reads from our .env file.
    If a variable is missing, it raises an error at startup.
    Silent misconfigurations cause hard-to-debug bugs.
    """

    # Database
    DATABASE_URL: str

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # JWT
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # App
    APP_ENV: str = "development"

    @property
    def is_production(self) -> bool:
        return self.APP_ENV == "production"

    @property
    def is_development(self) -> bool:
        return self.APP_ENV == "development"


    # Tell pydantic-settings to read from .env file
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


# Single instance used across the entire app.
# Importing `settings` anywhere gives us the same object — no re-reading .env.
settings = Settings()