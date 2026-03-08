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
