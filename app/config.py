from pathlib import Path
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    webhook_api_key: str = ""
    host: str = "0.0.0.0"
    port: int = 8000
    max_workers: int = 10
    default_model: str = "opus"
    request_timeout: int = 120
    cache_ttl: int = 86400
    max_subscription_monthly_usd: float = 200.0
    prompt_size_warn_tokens: int = 50000

    # Model routing
    model_tier_map: dict[str, str] = {"light": "haiku", "standard": "sonnet", "heavy": "opus"}
    auto_route_thresholds: dict[str, int] = {"light_max_tokens": 2000, "standard_max_tokens": 10000}
    enable_smart_routing: bool = False

    # Exa pre-fetch
    exa_api_key: str = ""
    exa_enabled: bool = True
    exa_num_results: int = 10
    exa_cache_ttl: int = 3600

    # Sumble pre-fetch
    sumble_api_key: str = ""
    sumble_enabled: bool = True
    sumble_base_url: str = "https://api.sumble.com/v3"
    sumble_cache_ttl: int = 3600
    sumble_timeout: int = 30

    # Retry worker
    retry_max_attempts: int = 5
    retry_check_interval: int = 10

    # Subscription monitor
    subscription_probe_interval: int = 60
    subscription_probe_interval_degraded: int = 30
    subscription_probe_interval_paused: int = 120

    # Cleanup worker
    cleanup_interval_seconds: int = 3600
    cleanup_job_retention_hours: int = 24
    cleanup_feedback_retention_days: int = 90
    cleanup_review_retention_days: int = 30
    cleanup_usage_retention_days: int = 90
    cleanup_failed_callback_days: int = 7

    # Derived paths (relative to project root)
    base_dir: Path = Path(__file__).resolve().parent.parent
    skills_dir: Path = base_dir / "skills"
    knowledge_dir: Path = base_dir / "knowledge_base"
    clients_dir: Path = base_dir / "clients"
    pipelines_dir: Path = base_dir / "pipelines"
    plays_dir: Path = base_dir / "plays"
    data_dir: Path = base_dir / "data"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
