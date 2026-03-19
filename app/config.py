from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    webhook_api_key: str = ""
    host: str = "0.0.0.0"
    port: int = 8000

    # CORS
    allowed_origins: list[str] = [
        "https://dashboard-beta-sable-36.vercel.app",
        "http://localhost:3000",
        "http://localhost:3001",
    ]

    # Rate limiting (requests per minute per IP)
    rate_limit_webhook: int = 60
    rate_limit_batch: int = 10
    rate_limit_pipeline: int = 20
    rate_limit_default: int = 120
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

    # Parallel.ai web intelligence (search + extract)
    parallel_api_key: str = ""

    # Sumble company intelligence
    sumble_api_key: str = ""
    sumble_base_url: str = "https://api.sumble.com/v3"
    sumble_timeout: int = 30

    # Findymail contact enrichment
    findymail_api_key: str = ""
    findymail_base_url: str = "https://app.findymail.com"
    findymail_timeout: int = 30

    # DeepLine enrichment (email waterfall + firmographic)
    deepline_api_key: str = ""
    deepline_base_url: str = "https://code.deepline.com"
    deepline_timeout: int = 60

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
    cleanup_usage_retention_days: int = 90
    cleanup_failed_callback_days: int = 7

    # Derived paths (relative to project root)
    base_dir: Path = Path(__file__).resolve().parent.parent
    skills_dir: Path = base_dir / "skills"
    knowledge_dir: Path = base_dir / "knowledge_base"
    clients_dir: Path = base_dir / "clients"
    pipelines_dir: Path = base_dir / "pipelines"
    plays_dir: Path = base_dir / "plays"
    functions_dir: Path = base_dir / "functions"
    data_dir: Path = base_dir / "data"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
