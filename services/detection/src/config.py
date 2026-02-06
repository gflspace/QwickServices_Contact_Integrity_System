"""Configuration for the Detection Service."""

import os


class Settings:
    POSTGRES_HOST: str = os.getenv("POSTGRES_HOST", "localhost")
    POSTGRES_PORT: int = int(os.getenv("POSTGRES_PORT", "5432"))
    POSTGRES_DB: str = os.getenv("POSTGRES_DB", "cis")
    POSTGRES_USER: str = os.getenv("POSTGRES_USER", "cis_user")
    POSTGRES_PASSWORD: str = os.getenv("POSTGRES_PASSWORD", "changeme_in_production")

    REDIS_HOST: str = os.getenv("REDIS_HOST", "localhost")
    REDIS_PORT: int = int(os.getenv("REDIS_PORT", "6379"))

    DETECTION_PORT: int = int(os.getenv("DETECTION_PORT", "8001"))
    LOG_LEVEL: str = os.getenv("DETECTION_LOG_LEVEL", "info")
    RULESET_VERSION: str = os.getenv("DETECTION_RULESET_VERSION", "1.0.0")

    REDIS_STREAM_MESSAGES: str = os.getenv("REDIS_STREAM_MESSAGES", "cis:messages")
    REDIS_STREAM_DETECTIONS: str = os.getenv("REDIS_STREAM_DETECTIONS", "cis:detections")
    REDIS_CONSUMER_GROUP: str = os.getenv("REDIS_CONSUMER_GROUP", "cis-workers")

    # Stage weights for combined scoring
    STAGE1_WEIGHT: float = float(os.getenv("STAGE1_WEIGHT", "0.50"))
    STAGE2_WEIGHT: float = float(os.getenv("STAGE2_WEIGHT", "0.30"))
    STAGE3_WEIGHT: float = float(os.getenv("STAGE3_WEIGHT", "0.20"))

    @property
    def database_url(self) -> str:
        return (
            f"postgresql://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def async_database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


settings = Settings()
