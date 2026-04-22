"""Environment-backed config for the control plane."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    postgres_dsn: str = os.environ.get("POSTGRES_DSN", "postgresql://fk:change-me@postgres:5432/fk_control")
    redis_url: str = os.environ.get("REDIS_URL", "redis://redis:6379/0")
    control_api_bind: str = os.environ.get("CONTROL_API_BIND", "0.0.0.0")
    control_api_port: int = int(os.environ.get("CONTROL_API_PORT", "8080"))
    default_material: str = os.environ.get("DEFAULT_MATERIAL", "realistic")
    default_chapter_seconds: int = int(os.environ.get("DEFAULT_CHAPTER_SECONDS", "300"))
    scheduler_consumer: str = os.environ.get("SCHEDULER_CONSUMER", "scheduler-01")
    lane_heartbeat_stale_after_seconds: int = int(os.environ.get("LANE_HEARTBEAT_STALE_AFTER_SECONDS", "45"))


settings = Settings()
