"""Configuration for the Policy & Enforcement Service."""

import os


class Settings:
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "cis")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "cis_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "changeme_in_production")

    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))

    POLICY_PORT: int = int(os.getenv("POLICY_PORT", "8002"))
    LOG_LEVEL: str = os.getenv("POLICY_LOG_LEVEL", "info")

    STRIKE_WINDOW_DAYS: int = int(os.getenv("POLICY_STRIKE_WINDOW_DAYS", "30"))

    REDIS_STREAM_DETECTIONS: str = os.getenv("REDIS_STREAM_DETECTIONS", "cis:detections")
    REDIS_CONSUMER_GROUP: str = os.getenv("REDIS_CONSUMER_GROUP", "cis-policy")

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
