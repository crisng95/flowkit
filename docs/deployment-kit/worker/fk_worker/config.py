"""Environment-backed config for a worker lane."""

from dataclasses import dataclass
import os


@dataclass(frozen=True)
class Settings:
    lane_id: str = os.environ.get("LANE_ID", "lane-01")
    flow_account_alias: str = os.environ.get("FLOW_ACCOUNT_ALIAS", "flow-account-01")
    flowkit_root: str = os.environ.get("FLOWKIT_ROOT", "/srv/flowkit/lane-01")
    flow_agent_dir: str = os.environ.get("FLOW_AGENT_DIR", "/srv/flowkit/lane-01/runtime")
    flowkit_work_dir: str = os.environ.get("FLOWKIT_WORK_DIR", "/srv/flowkit/lane-01/work")
    flowkit_log_dir: str = os.environ.get("FLOWKIT_LOG_DIR", "/srv/flowkit/lane-01/logs")
    api_host: str = os.environ.get("API_HOST", "127.0.0.1")
    api_port: int = int(os.environ.get("API_PORT", "8100"))
    redis_url: str = os.environ.get("REDIS_URL", "redis://fk-ctl-01:6379/0")
    postgres_dsn: str = os.environ.get("POSTGRES_DSN", "postgresql://fk:change-me@fk-ctl-01:5432/fk_control")
    heartbeat_ttl_seconds: int = int(os.environ.get("HEARTBEAT_TTL_SECONDS", "30"))
    heartbeat_interval_seconds: int = int(os.environ.get("HEARTBEAT_INTERVAL_SECONDS", "10"))
    worker_consumer_name: str = os.environ.get("WORKER_CONSUMER_NAME", os.uname().nodename if hasattr(os, "uname") else "flowkit-worker")
    runner_health_host: str = os.environ.get("RUNNER_HEALTH_HOST", "0.0.0.0")
    runner_health_port: int = int(os.environ.get("RUNNER_HEALTH_PORT", "8181"))
    r2_bucket: str = os.environ.get("R2_BUCKET", "flowkit-output")
    r2_prefix: str = os.environ.get("R2_PREFIX", "projects")
    r2_endpoint: str = os.environ.get("R2_ENDPOINT", "")
    r2_access_key_id: str = os.environ.get("R2_ACCESS_KEY_ID", "")
    r2_secret_access_key: str = os.environ.get("R2_SECRET_ACCESS_KEY", "")
    allow_local_artifact_fallback: bool = os.environ.get("ALLOW_LOCAL_ARTIFACT_FALLBACK", "0") == "1"

    @property
    def local_api_base(self) -> str:
        return f"http://{self.api_host}:{self.api_port}"


settings = Settings()
