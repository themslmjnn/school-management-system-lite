import os
from functools import lru_cache
from typing import Annotated, Literal
from urllib.parse import quote

from pydantic import Field, SecretStr, StringConstraints
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

    ENVIRONMENT: Literal["development", "test"]

    DB_HOST: NonEmptyStr = "localhost"
    DB_PORT: int = Field(ge=1, le=65535, default=5432)
    DB_USER: NonEmptyStr
    DB_PASSWORD: SecretStr
    DB_NAME: NonEmptyStr

    DB_POOL_TIMEOUT: int = Field(ge=1, le=30, default=5)
    DB_CONNECT_TIMEOUT: int = Field(ge=1, le=60, default=5)

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"postgresql+asyncpg://{quote(self.DB_USER, safe='')}"
            f":{quote(self.DB_PASSWORD.get_secret_value(), safe='')}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{quote(self.DB_NAME, safe='')}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()
