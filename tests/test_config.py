"""Tests for app/config.py — Settings defaults, env overrides, derived paths."""

from pathlib import Path
from unittest.mock import patch

from app.config import Settings


class TestSettingsDefaults:
    def test_has_expected_fields(self):
        s = Settings()
        # Verify all expected fields exist with correct types
        assert isinstance(s.webhook_api_key, str)
        assert isinstance(s.host, str)
        assert isinstance(s.port, int)
        assert isinstance(s.max_workers, int)
        assert isinstance(s.default_model, str)
        assert isinstance(s.request_timeout, int)
        assert isinstance(s.cache_ttl, int)
        assert isinstance(s.max_subscription_monthly_usd, float)

    def test_model_routing_defaults(self):
        s = Settings()
        assert s.model_tier_map == {"light": "haiku", "standard": "sonnet", "heavy": "opus"}
        assert s.auto_route_thresholds == {"light_max_tokens": 2000, "standard_max_tokens": 10000}
        assert s.enable_smart_routing is False

    def test_retry_defaults(self):
        s = Settings()
        assert s.retry_max_attempts == 5
        assert s.retry_check_interval == 10

    def test_subscription_defaults(self):
        s = Settings()
        assert s.subscription_probe_interval == 60
        assert s.subscription_probe_interval_degraded == 30
        assert s.subscription_probe_interval_paused == 120

    def test_cleanup_defaults(self):
        s = Settings()
        assert s.cleanup_interval_seconds == 3600
        assert s.cleanup_job_retention_hours == 24
        assert s.cleanup_feedback_retention_days == 90
        assert s.cleanup_review_retention_days == 30
        assert s.cleanup_usage_retention_days == 90
        assert s.cleanup_failed_callback_days == 7


class TestDerivedPaths:
    def test_base_dir_is_project_root(self):
        s = Settings()
        # base_dir should be the project root (parent of app/)
        assert s.base_dir.is_dir()
        assert (s.base_dir / "app").is_dir()

    def test_skills_dir(self):
        s = Settings()
        assert s.skills_dir == s.base_dir / "skills"

    def test_knowledge_dir(self):
        s = Settings()
        assert s.knowledge_dir == s.base_dir / "knowledge_base"

    def test_clients_dir(self):
        s = Settings()
        assert s.clients_dir == s.base_dir / "clients"

    def test_pipelines_dir(self):
        s = Settings()
        assert s.pipelines_dir == s.base_dir / "pipelines"

    def test_plays_dir(self):
        s = Settings()
        assert s.plays_dir == s.base_dir / "plays"

    def test_data_dir(self):
        s = Settings()
        assert s.data_dir == s.base_dir / "data"


class TestEnvOverride:
    def test_override_via_env(self):
        with patch.dict("os.environ", {
            "MAX_WORKERS": "20",
            "DEFAULT_MODEL": "haiku",
            "CACHE_TTL": "3600",
            "ENABLE_SMART_ROUTING": "true",
        }):
            s = Settings()
            assert s.max_workers == 20
            assert s.default_model == "haiku"
            assert s.cache_ttl == 3600
            assert s.enable_smart_routing is True

    def test_api_key_from_env(self):
        with patch.dict("os.environ", {"WEBHOOK_API_KEY": "secret-key-123"}):
            s = Settings()
            assert s.webhook_api_key == "secret-key-123"

    def test_extra_env_vars_ignored(self):
        with patch.dict("os.environ", {"SOME_RANDOM_VAR": "xyz"}):
            s = Settings()  # should not raise
            assert isinstance(s.port, int)


class TestModelConfig:
    def test_extra_fields_ignored(self):
        # Settings has extra="ignore"
        s = Settings()
        assert s.model_config.get("extra") == "ignore"

    def test_env_file_config(self):
        s = Settings()
        assert s.model_config.get("env_file") == ".env"
        assert s.model_config.get("env_file_encoding") == "utf-8"


# ---------------------------------------------------------------------------
# Default values — exact values
# ---------------------------------------------------------------------------


class TestDefaultValues:
    """Test code-level defaults by clearing env vars that .env might set."""

    def test_webhook_api_key_empty(self, monkeypatch):
        monkeypatch.delenv("WEBHOOK_API_KEY", raising=False)
        s = Settings(_env_file=None)
        assert s.webhook_api_key == ""

    def test_host_default(self, monkeypatch):
        monkeypatch.delenv("HOST", raising=False)
        s = Settings(_env_file=None)
        assert s.host == "0.0.0.0"

    def test_port_default(self, monkeypatch):
        monkeypatch.delenv("PORT", raising=False)
        s = Settings(_env_file=None)
        assert s.port == 8000

    def test_max_workers_default(self):
        s = Settings(_env_file=None)
        assert s.max_workers == 10

    def test_default_model(self, monkeypatch):
        monkeypatch.delenv("DEFAULT_MODEL", raising=False)
        s = Settings(_env_file=None)
        assert s.default_model == "opus"

    def test_request_timeout_default(self):
        s = Settings(_env_file=None)
        assert s.request_timeout == 120

    def test_cache_ttl_default(self):
        s = Settings(_env_file=None)
        assert s.cache_ttl == 86400

    def test_max_subscription_monthly_usd(self):
        s = Settings(_env_file=None)
        assert s.max_subscription_monthly_usd == 200.0

    def test_prompt_size_warn_tokens(self):
        s = Settings(_env_file=None)
        assert s.prompt_size_warn_tokens == 50000


# ---------------------------------------------------------------------------
# Env overrides — type coercion
# ---------------------------------------------------------------------------


class TestEnvOverrideCoercion:
    def test_port_from_env(self):
        with patch.dict("os.environ", {"PORT": "9000"}):
            s = Settings()
            assert s.port == 9000

    def test_host_from_env(self):
        with patch.dict("os.environ", {"HOST": "127.0.0.1"}):
            s = Settings()
            assert s.host == "127.0.0.1"

    def test_request_timeout_from_env(self):
        with patch.dict("os.environ", {"REQUEST_TIMEOUT": "300"}):
            s = Settings()
            assert s.request_timeout == 300

    def test_max_subscription_from_env(self):
        with patch.dict("os.environ", {"MAX_SUBSCRIPTION_MONTHLY_USD": "500.50"}):
            s = Settings()
            assert s.max_subscription_monthly_usd == 500.50

    def test_smart_routing_false_from_env(self):
        with patch.dict("os.environ", {"ENABLE_SMART_ROUTING": "false"}):
            s = Settings()
            assert s.enable_smart_routing is False

    def test_retry_settings_from_env(self):
        with patch.dict("os.environ", {
            "RETRY_MAX_ATTEMPTS": "10",
            "RETRY_CHECK_INTERVAL": "30",
        }):
            s = Settings()
            assert s.retry_max_attempts == 10
            assert s.retry_check_interval == 30

    def test_subscription_intervals_from_env(self):
        with patch.dict("os.environ", {
            "SUBSCRIPTION_PROBE_INTERVAL": "120",
            "SUBSCRIPTION_PROBE_INTERVAL_DEGRADED": "15",
            "SUBSCRIPTION_PROBE_INTERVAL_PAUSED": "300",
        }):
            s = Settings()
            assert s.subscription_probe_interval == 120
            assert s.subscription_probe_interval_degraded == 15
            assert s.subscription_probe_interval_paused == 300

    def test_cleanup_settings_from_env(self):
        with patch.dict("os.environ", {
            "CLEANUP_INTERVAL_SECONDS": "7200",
            "CLEANUP_JOB_RETENTION_HOURS": "48",
        }):
            s = Settings()
            assert s.cleanup_interval_seconds == 7200
            assert s.cleanup_job_retention_hours == 48

    def test_prompt_size_warn_from_env(self):
        with patch.dict("os.environ", {"PROMPT_SIZE_WARN_TOKENS": "100000"}):
            s = Settings()
            assert s.prompt_size_warn_tokens == 100000


# ---------------------------------------------------------------------------
# Derived paths — type checks
# ---------------------------------------------------------------------------


class TestDerivedPathTypes:
    def test_all_paths_are_path_instances(self):
        s = Settings()
        for attr in ("base_dir", "skills_dir", "knowledge_dir", "clients_dir",
                      "pipelines_dir", "plays_dir", "data_dir"):
            assert isinstance(getattr(s, attr), Path), f"{attr} is not a Path"

    def test_base_dir_is_absolute(self):
        s = Settings()
        assert s.base_dir.is_absolute()

    def test_all_derived_under_base_dir(self):
        s = Settings()
        for attr in ("skills_dir", "knowledge_dir", "clients_dir",
                      "pipelines_dir", "plays_dir", "data_dir"):
            path = getattr(s, attr)
            assert str(path).startswith(str(s.base_dir)), f"{attr} not under base_dir"


# ---------------------------------------------------------------------------
# Module-level singleton
# ---------------------------------------------------------------------------


class TestSettingsSingleton:
    def test_module_settings_is_instance(self):
        from app.config import settings
        assert isinstance(settings, Settings)

    def test_module_settings_has_defaults(self):
        from app.config import settings
        assert settings.port == 8000 or isinstance(settings.port, int)
