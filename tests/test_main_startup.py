"""Tests for app/main.py — verify app setup, middleware, routers, and startup lifecycle."""

from unittest.mock import AsyncMock, MagicMock, patch

# ---------------------------------------------------------------------------
# Helper for startup tests — creates mock constructors
# ---------------------------------------------------------------------------

def _mock_cls(name, has_load=False, has_start=False, has_build=False):
    instance = MagicMock(name=name)
    if has_start:
        instance.start = AsyncMock()
    if has_load:
        instance.load = MagicMock()
    if has_build:
        instance.build = MagicMock()
        instance.doc_count = 0
    instance.start_workers = AsyncMock()
    cls = MagicMock(return_value=instance)
    return cls, instance


def _build_startup_patches():
    """Create all patches for startup() with mock constructors."""
    targets = {
        "WorkerPool": {},
        "ResultCache": {},
        "EventBus": {},
        "JobQueue": {"has_start": False},
        "BatchScheduler": {"has_start": True},
        "DestinationStore": {"has_load": True},
        "ContextStore": {},
        "FeedbackStore": {"has_load": True},
        "PipelineStore": {"has_load": True},
        "PlayStore": {"has_load": True},
        "ExperimentStore": {"has_load": True},
        "UsageStore": {"has_load": True},
        "MemoryStore": {"has_load": True},
        "ContextIndex": {"has_build": True},
        "RetryWorker": {"has_load": True, "has_start": True},
        "SubscriptionMonitor": {"has_start": True},
        "DataCleanupWorker": {"has_start": True},
        "DatasetStore": {"has_load": True},
    }
    patches = {}
    instances = {}
    constructors = {}
    for name, kwargs in targets.items():
        cls, inst = _mock_cls(name, **kwargs)
        patches[name] = patch(f"app.main.{name}", cls)
        instances[name] = inst
        constructors[name] = cls
    return patches, instances, constructors


# ---------------------------------------------------------------------------
# App setup — structure, routes, middleware
# ---------------------------------------------------------------------------


class TestAppSetup:
    def test_app_title_and_version(self):
        from app.main import app
        assert app.title == "Clay Webhook OS"
        assert app.version == "3.0.0"

    def test_app_description(self):
        from app.main import app
        assert "autopilot" in app.description.lower()

    def test_all_routes_registered(self):
        from app.main import app
        routes = {r.path for r in app.routes if hasattr(r, "path")}
        # Core endpoints
        assert "/" in routes
        assert "/health" in routes
        assert "/webhook" in routes
        assert "/pipeline" in routes
        assert "/batch" in routes
        assert "/jobs" in routes
        assert "/stats" in routes
        assert "/usage" in routes
        assert "/usage/health" in routes

    def test_crud_routes_registered(self):
        from app.main import app
        routes = {r.path for r in app.routes if hasattr(r, "path")}
        assert "/destinations" in routes
        assert "/clients" in routes
        assert "/pipelines" in routes
        assert "/plays" in routes
        assert "/experiments" in routes
        assert "/feedback" in routes

    def test_middleware_stack(self):
        from app.main import app
        middleware_classes = [m.cls.__name__ for m in app.user_middleware]
        assert "ErrorHandlerMiddleware" in middleware_classes
        assert "SecurityHeadersMiddleware" in middleware_classes
        assert "RateLimitMiddleware" in middleware_classes
        assert "ApiKeyMiddleware" in middleware_classes
        assert "CORSMiddleware" in middleware_classes

    def test_middleware_order(self):
        """ErrorHandler outermost, then SecurityHeaders, RateLimit, Auth, CORS innermost."""
        from app.main import app
        names = [m.cls.__name__ for m in app.user_middleware]
        assert names.index("CORSMiddleware") < names.index("ApiKeyMiddleware")
        assert names.index("ApiKeyMiddleware") < names.index("RateLimitMiddleware")
        assert names.index("RateLimitMiddleware") < names.index("SecurityHeadersMiddleware")
        assert names.index("SecurityHeadersMiddleware") < names.index("ErrorHandlerMiddleware")

    def test_cors_restricts_origins(self):
        from app.main import app
        cors = next(m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware")
        origins = cors.kwargs["allow_origins"]
        assert "*" not in origins
        assert "https://dashboard-beta-sable-36.vercel.app" in origins
        assert "http://localhost:3000" in origins

    def test_cors_restricts_methods(self):
        from app.main import app
        cors = next(m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware")
        methods = cors.kwargs["allow_methods"]
        assert "*" not in methods
        assert "GET" in methods
        assert "POST" in methods

    def test_cors_restricts_headers(self):
        from app.main import app
        cors = next(m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware")
        headers = cors.kwargs["allow_headers"]
        assert "*" not in headers
        assert "x-api-key" in headers
        assert "Content-Type" in headers

    def test_cors_allows_credentials(self):
        from app.main import app
        cors = next(m for m in app.user_middleware if m.cls.__name__ == "CORSMiddleware")
        assert cors.kwargs["allow_credentials"] is True


# ---------------------------------------------------------------------------
# Route methods
# ---------------------------------------------------------------------------


class TestRouteMethods:
    def _get_route_methods(self):
        from app.main import app
        route_map = {}
        for r in app.routes:
            if hasattr(r, "path") and hasattr(r, "methods"):
                route_map.setdefault(r.path, set()).update(r.methods)
        return route_map

    def test_webhook_accepts_post(self):
        methods = self._get_route_methods()
        assert "POST" in methods.get("/webhook", set())

    def test_health_accepts_get(self):
        methods = self._get_route_methods()
        assert "GET" in methods.get("/health", set())

    def test_batch_accepts_post(self):
        methods = self._get_route_methods()
        assert "POST" in methods.get("/batch", set())

    def test_cleanup_accepts_post(self):
        methods = self._get_route_methods()
        assert "POST" in methods.get("/cleanup", set())

    def test_stats_accepts_get(self):
        methods = self._get_route_methods()
        assert "GET" in methods.get("/stats", set())


# ---------------------------------------------------------------------------
# Startup lifecycle
# ---------------------------------------------------------------------------


class TestStartup:
    async def test_startup_initializes_all_state(self):
        import app.main as main_module

        patches, instances, constructors = _build_startup_patches()
        skills_patch = patch("app.main.list_skills", return_value=["email-gen"])

        with skills_patch:
            {name: p.start() for name, p in patches.items()}
            try:
                await main_module.startup()

                app = main_module.app
                # Verify key state objects are attached
                assert hasattr(app.state, "pool")
                assert hasattr(app.state, "cache")
                assert hasattr(app.state, "event_bus")
                assert hasattr(app.state, "job_queue")
                assert hasattr(app.state, "scheduler")
                assert hasattr(app.state, "destination_store")
                assert hasattr(app.state, "feedback_store")
                assert hasattr(app.state, "pipeline_store")
                assert hasattr(app.state, "play_store")
                assert hasattr(app.state, "experiment_store")
                assert hasattr(app.state, "usage_store")
                assert hasattr(app.state, "retry_worker")
                assert hasattr(app.state, "subscription_monitor")
                assert hasattr(app.state, "cleanup_worker")

                # Verify async starts were called
                app.state.job_queue.start_workers.assert_called_once()
                app.state.scheduler.start.assert_called_once()
                app.state.retry_worker.start.assert_called_once()
                app.state.subscription_monitor.start.assert_called_once()
                app.state.cleanup_worker.start.assert_called_once()

                # Verify stores were loaded
                app.state.destination_store.load.assert_called_once()
                app.state.feedback_store.load.assert_called_once()
                app.state.pipeline_store.load.assert_called_once()
                app.state.play_store.load.assert_called_once()
                app.state.experiment_store.load.assert_called_once()
                app.state.usage_store.load.assert_called_once()
                app.state.retry_worker.load.assert_called_once()
            finally:
                for p in patches.values():
                    p.stop()


# ---------------------------------------------------------------------------
# Startup — cross-wiring
# ---------------------------------------------------------------------------


class TestStartupCrossWiring:
    async def test_job_queue_experiment_store_wired(self):
        """job_queue._experiment_store is set to the experiment_store instance."""
        import app.main as main_module
        patches, instances, constructors = _build_startup_patches()

        with patch("app.main.list_skills", return_value=[]):
            for p in patches.values():
                p.start()
            try:
                await main_module.startup()
                app = main_module.app
                assert app.state.job_queue._experiment_store is app.state.experiment_store
            finally:
                for p in patches.values():
                    p.stop()

    async def test_job_queue_usage_store_wired(self):
        """job_queue._usage_store is set to the usage_store instance."""
        import app.main as main_module
        patches, instances, constructors = _build_startup_patches()

        with patch("app.main.list_skills", return_value=[]):
            for p in patches.values():
                p.start()
            try:
                await main_module.startup()
                app = main_module.app
                assert app.state.job_queue._usage_store is app.state.usage_store
            finally:
                for p in patches.values():
                    p.stop()

    async def test_job_queue_retry_worker_wired(self):
        """job_queue._retry_worker is set to the retry_worker instance."""
        import app.main as main_module
        patches, instances, constructors = _build_startup_patches()

        with patch("app.main.list_skills", return_value=[]):
            for p in patches.values():
                p.start()
            try:
                await main_module.startup()
                app = main_module.app
                assert app.state.job_queue._retry_worker is app.state.retry_worker
            finally:
                for p in patches.values():
                    p.stop()

    async def test_destination_store_retry_worker_wired(self):
        """destination_store._retry_worker is set to the retry_worker instance."""
        import app.main as main_module
        patches, instances, constructors = _build_startup_patches()

        with patch("app.main.list_skills", return_value=[]):
            for p in patches.values():
                p.start()
            try:
                await main_module.startup()
                app = main_module.app
                assert app.state.destination_store._retry_worker is app.state.retry_worker
            finally:
                for p in patches.values():
                    p.stop()


# ---------------------------------------------------------------------------
# Startup — constructor arguments
# ---------------------------------------------------------------------------


class TestStartupConstructorArgs:
    async def test_worker_pool_uses_settings_max_workers(self):
        import app.main as main_module
        patches, instances, constructors = _build_startup_patches()

        with patch("app.main.list_skills", return_value=[]), \
             patch("app.main.settings") as mock_settings:
            mock_settings.max_workers = 7
            mock_settings.cache_ttl = 300
            mock_settings.data_dir = "/tmp/data"
            mock_settings.clients_dir = "/tmp/clients"
            mock_settings.knowledge_dir = "/tmp/kb"
            mock_settings.skills_dir = "/tmp/skills"
            mock_settings.pipelines_dir = "/tmp/pipelines"
            mock_settings.plays_dir = "/tmp/plays"
            mock_settings.retry_check_interval = 60
            mock_settings.subscription_probe_interval = 120
            mock_settings.subscription_probe_interval_degraded = 30
            mock_settings.subscription_probe_interval_paused = 300
            mock_settings.cleanup_interval_seconds = 3600
            mock_settings.cleanup_job_retention_hours = 48
            mock_settings.cleanup_feedback_retention_days = 90

            mock_settings.cleanup_usage_retention_days = 90
            mock_settings.cleanup_failed_callback_days = 7
            mock_settings.webhook_api_key = ""
            mock_settings.enable_smart_routing = False
            mock_settings.parallel_api_key = ""
            mock_settings.base_dir = "/tmp"
            mock_settings.sumble_api_key = ""
            mock_settings.findymail_api_key = ""
            for p in patches.values():
                p.start()
            try:
                await main_module.startup()
                constructors["WorkerPool"].assert_called_once_with(max_workers=7)
            finally:
                for p in patches.values():
                    p.stop()

    async def test_cache_uses_settings_ttl(self):
        import app.main as main_module
        patches, instances, constructors = _build_startup_patches()

        with patch("app.main.list_skills", return_value=[]), \
             patch("app.main.settings") as mock_settings:
            mock_settings.max_workers = 3
            mock_settings.cache_ttl = 600
            mock_settings.data_dir = "/tmp/data"
            mock_settings.clients_dir = "/tmp/clients"
            mock_settings.knowledge_dir = "/tmp/kb"
            mock_settings.skills_dir = "/tmp/skills"
            mock_settings.pipelines_dir = "/tmp/pipelines"
            mock_settings.plays_dir = "/tmp/plays"
            mock_settings.retry_check_interval = 60
            mock_settings.subscription_probe_interval = 120
            mock_settings.subscription_probe_interval_degraded = 30
            mock_settings.subscription_probe_interval_paused = 300
            mock_settings.cleanup_interval_seconds = 3600
            mock_settings.cleanup_job_retention_hours = 48
            mock_settings.cleanup_feedback_retention_days = 90

            mock_settings.cleanup_usage_retention_days = 90
            mock_settings.cleanup_failed_callback_days = 7
            mock_settings.webhook_api_key = ""
            mock_settings.enable_smart_routing = False
            mock_settings.parallel_api_key = ""
            mock_settings.base_dir = "/tmp"
            mock_settings.sumble_api_key = ""
            mock_settings.findymail_api_key = ""
            for p in patches.values():
                p.start()
            try:
                await main_module.startup()
                constructors["ResultCache"].assert_called_once_with(ttl=600)
            finally:
                for p in patches.values():
                    p.stop()

    async def test_start_workers_uses_settings_max_workers(self):
        import app.main as main_module
        patches, instances, constructors = _build_startup_patches()

        with patch("app.main.list_skills", return_value=[]), \
             patch("app.main.settings") as mock_settings:
            mock_settings.max_workers = 12
            mock_settings.cache_ttl = 300
            mock_settings.data_dir = "/tmp/data"
            mock_settings.clients_dir = "/tmp/clients"
            mock_settings.knowledge_dir = "/tmp/kb"
            mock_settings.skills_dir = "/tmp/skills"
            mock_settings.pipelines_dir = "/tmp/pipelines"
            mock_settings.plays_dir = "/tmp/plays"
            mock_settings.retry_check_interval = 60
            mock_settings.subscription_probe_interval = 120
            mock_settings.subscription_probe_interval_degraded = 30
            mock_settings.subscription_probe_interval_paused = 300
            mock_settings.cleanup_interval_seconds = 3600
            mock_settings.cleanup_job_retention_hours = 48
            mock_settings.cleanup_feedback_retention_days = 90

            mock_settings.cleanup_usage_retention_days = 90
            mock_settings.cleanup_failed_callback_days = 7
            mock_settings.webhook_api_key = ""
            mock_settings.enable_smart_routing = False
            mock_settings.parallel_api_key = ""
            mock_settings.base_dir = "/tmp"
            mock_settings.sumble_api_key = ""
            mock_settings.findymail_api_key = ""
            for p in patches.values():
                p.start()
            try:
                await main_module.startup()
                app = main_module.app
                app.state.job_queue.start_workers.assert_called_once_with(num_workers=12)
            finally:
                for p in patches.values():
                    p.stop()

    async def test_scheduler_start_receives_job_queue(self):
        """scheduler.start() is called with job_queue as argument."""
        import app.main as main_module
        patches, instances, constructors = _build_startup_patches()

        with patch("app.main.list_skills", return_value=[]):
            for p in patches.values():
                p.start()
            try:
                await main_module.startup()
                app = main_module.app
                app.state.scheduler.start.assert_called_once_with(app.state.job_queue)
            finally:
                for p in patches.values():
                    p.stop()
