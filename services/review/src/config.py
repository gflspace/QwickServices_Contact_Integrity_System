"""Configuration for the Review Queue Service."""

import os


class Settings:
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "cis")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "cis_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "changeme_in_production")

    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))

    REVIEW_PORT: int = int(os.getenv("REVIEW_PORT", "8003"))
    LOG_LEVEL: str = os.getenv("REVIEW_LOG_LEVEL", "info")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
