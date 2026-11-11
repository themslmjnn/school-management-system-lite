import os
from functools import lru_cache
from typing import Annotated, Literal
from urllib.parse import quote

from pydantic import Field, SecretStr, StringConstraints, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

_ENV_FILE = ".env.test" if os.getenv("ENVIRONMENT", "development") == "test" else ".env"

NonEmptyStr = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=_ENV_FILE,
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="forbid",
        env_ignore_empty=True,
    )

    APP_URL: str = "http://localhost:8000"

    ENVIRONMENT: Literal["development", "test"]

    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"

    DB_HOST: NonEmptyStr = "localhost"
    DB_PORT: int = Field(ge=1, le=65535, default=5432)
    DB_USER: NonEmptyStr
    DB_PASSWORD: SecretStr
    DB_NAME: NonEmptyStr

    DB_POOL_TIMEOUT: int = Field(ge=1, le=30, default=5)
    DB_CONNECT_TIMEOUT: int = Field(ge=1, le=60, default=5)

    REDIS_HOST: NonEmptyStr
    REDIS_PORT: int = Field(ge=1, le=65535, default=6379)
    REDIS_PASSWORD: SecretStr | None = None
    REDIS_DB: int = Field(ge=0, le=15)

    JWT_ALGORITHM: str = "HS256"
    JWT_SECRET_KEY: SecretStr

    ACCESS_TOKEN_EXPIRES_MINUTES: int = Field(ge=15, le=60, default=30)
    REFRESH_TOKEN_EXPIRES_DAYS: int = Field(ge=7, le=30, default=15)

    ACTIVATION_TOKEN_EXPIRES_HOURS: int = Field(ge=2, le=72, default=48)
    PASSWORD_RESET_TOKEN_EXPIRES_MINUTES: int = Field(ge=15, le=120, default=30)

    EMAIL_WORKER_INTERVAL: int = Field(ge=1, le=600, default=60)
    EMAIL_WORKER_BATCH_SIZE: int = Field(ge=1, le=50, default=10)

    RESEND_API_KEY: str
    MAIL_FROM: str = "noreply@sms-lite.org"
    MAIL_FROM_NAME: str = "SMS Lite"
    MAILTRAP_HOST: str = "sandbox.smtp.mailtrap.io"
    MAILTRAP_PORT: int = Field(ge=1, le=65535, default=587)
    MAILTRAP_USERNAME: str | None = None
    MAILTRAP_PASSWORD: SecretStr | None = None

    COOKIE_SECURE: bool = False

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{quote(self.DB_USER, safe='')}"
            f":{quote(self.DB_PASSWORD.get_secret_value(), safe='')}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{quote(self.DB_NAME, safe='')}"
        )

    @property
    def REDIS_URL(self) -> str:
        if self.REDIS_PASSWORD:
            password = quote(self.REDIS_PASSWORD.get_secret_value(), safe="")

            return f"redis://:{password}@{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

        return f"redis://{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @field_validator("JWT_SECRET_KEY")
    @classmethod
    def validate_jwt_secret_key(cls, v: SecretStr) -> SecretStr:
        if len(v.get_secret_value()) < 32:
            raise ValueError("JWT_SECRET_KEY must be at least 32 characters")

        return v


@lru_cache
def get_settings() -> Settings:
    return Settings()
