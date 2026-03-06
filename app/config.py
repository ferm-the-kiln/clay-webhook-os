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

    # Derived paths (relative to project root)
    base_dir: Path = Path(__file__).resolve().parent.parent
    skills_dir: Path = base_dir / "skills"
    knowledge_dir: Path = base_dir / "knowledge_base"
    clients_dir: Path = base_dir / "clients"
    pipelines_dir: Path = base_dir / "pipelines"
    data_dir: Path = base_dir / "data"

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}


settings = Settings()
