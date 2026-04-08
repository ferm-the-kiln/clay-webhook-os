import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.cache import ResultCache
from app.core.circuit_breaker import CircuitBreaker
from app.core.cleanup_worker import DataCleanupWorker
from app.core.context_index import ContextIndex
from app.core.context_store import ContextStore
from app.core.dataset_store import DatasetStore
from app.core.dedup import RequestDeduplicator
from app.core.destination_store import DestinationStore
from app.core.event_bus import EventBus
from app.core.execution_history import ExecutionHistory
from app.core.channel_store import ChannelStore
from app.core.channel_orchestrator import ChannelOrchestrator
from app.core.channel_proxy import ChannelProxy
from app.core.experiment_store import ExperimentStore
from app.core.feedback_loop import FeedbackLoop
from app.core.feedback_store import FeedbackStore
from app.core.function_store import FunctionStore
from app.core.job_queue import JobQueue
from app.core.learning_engine import LearningEngine
from app.core.local_job_queue import LocalJobQueue
from app.core.memory_store import MemoryStore
from app.core.pipeline_store import PipelineStore
from app.core.play_store import PlayStore
from app.core.prompt_cache import PromptCache
from app.core.retry_worker import RetryWorker
from app.core.skill_loader import list_skills
from app.core.skill_version_store import SkillVersionStore
from app.core.subscription_monitor import SubscriptionMonitor
from app.core.usage_store import UsageStore
from app.core.bridge_store import BridgeStore
from app.core.run_tracker import RunTracker
from app.core.script_store import ScriptStore
from app.core.worker_pool import WorkerPool
from app.middleware.auth import DualAuthMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.rate_limiter import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.routers import (
    auth,
    bridge,
    channels,
    context,
    datasets,
    destinations,
    enrichment,
    evals,
    experiments,
    feedback,
    functions,
    health,
    pipeline,
    pipelines,
    plays,
    portal,
    research,
    sheets,
    tables,
    usage,
    webhook,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("clay-webhook-os")

app = FastAPI(
    title="Clay Webhook OS",
    description="The autopilot for outbound GTM — AI-powered campaigns with smart pipelines and confidence routing",
    version="3.0.0",
)

# Middleware (order matters: outermost first — error → security → rate limit → auth → CORS)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(DualAuthMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "x-api-key", "Authorization"],
)

# Routers
app.include_router(auth.router)
app.include_router(health.router)
app.include_router(webhook.router)
app.include_router(pipeline.router)
app.include_router(destinations.router)
app.include_router(context.router)
app.include_router(feedback.router)
app.include_router(pipelines.router)
app.include_router(experiments.router)
app.include_router(plays.router)
app.include_router(usage.router)
app.include_router(enrichment.router)
app.include_router(datasets.router)
app.include_router(functions.router)
app.include_router(evals.router)
app.include_router(sheets.router)
app.include_router(portal.router)
app.include_router(tables.router)
app.include_router(channels.router)
app.include_router(bridge.router)
app.include_router(research.router)


@app.on_event("startup")
async def startup():
    app.state.pool = WorkerPool(max_workers=settings.max_workers)
    app.state.cache = ResultCache(ttl=settings.cache_ttl, max_size=settings.cache_max_entries)
    app.state.event_bus = EventBus()
    app.state.job_queue = JobQueue(
        pool=app.state.pool,
        cache=app.state.cache,
        event_bus=app.state.event_bus,
    )
    app.state.destination_store = DestinationStore(data_dir=settings.data_dir)
    app.state.destination_store.load()
    app.state.context_store = ContextStore(
        clients_dir=settings.clients_dir,
        knowledge_dir=settings.knowledge_dir,
        skills_dir=settings.skills_dir,
    )
    app.state.feedback_store = FeedbackStore(data_dir=settings.data_dir)
    app.state.feedback_store.load()
    app.state.pipeline_store = PipelineStore(pipelines_dir=settings.pipelines_dir)
    app.state.pipeline_store.load()
    app.state.play_store = PlayStore(plays_dir=settings.plays_dir, pipelines_dir=settings.pipelines_dir)
    app.state.play_store.load()
    app.state.experiment_store = ExperimentStore(
        skills_dir=settings.skills_dir,
        data_dir=settings.data_dir,
    )
    app.state.experiment_store.load()
    app.state.usage_store = UsageStore(data_dir=settings.data_dir)
    app.state.usage_store.load()
    app.state.job_queue._experiment_store = app.state.experiment_store
    app.state.job_queue._usage_store = app.state.usage_store

    # Phase 2: Agent memory store
    app.state.memory_store = MemoryStore(data_dir=settings.data_dir)
    app.state.memory_store.load()
    app.state.job_queue._memory_store = app.state.memory_store

    # Feedback-to-Knowledge: Learning engine (persistent corrections from feedback)
    app.state.learning_engine = LearningEngine(knowledge_dir=settings.knowledge_dir)
    app.state.job_queue._learning_engine = app.state.learning_engine

    # Phase 4: Semantic context index (build before wiring to queue)
    app.state.context_index = ContextIndex(
        dirs=[settings.knowledge_dir, settings.clients_dir],
        base_dir=settings.base_dir,
    )
    app.state.context_index.build()
    app.state.job_queue._context_index = app.state.context_index

    # Context Rack (modular context injection pipeline)
    if settings.supabase_context_rack_enabled:
        from app.core.context_rack import ContextRack
        from app.core.context_providers import build_default_slots
        app.state.context_rack = ContextRack(slots=build_default_slots())
        logger.info("  Context Rack: enabled (source=%s)", settings.supabase_context_source)
    else:
        app.state.context_rack = None
        logger.info("  Context Rack: disabled (using build_prompt)")

    # Enrichment cache (Supabase-backed L2 cache for external API results + skill outputs)
    from app.core.enrichment_cache import EnrichmentCache
    app.state.enrichment_cache = EnrichmentCache()
    await app.state.enrichment_cache.init()
    app.state.job_queue._enrichment_cache = app.state.enrichment_cache

    # Dataset store
    app.state.dataset_store = DatasetStore(data_dir=settings.data_dir)
    app.state.dataset_store.load()

    # Function store
    app.state.function_store = FunctionStore(functions_dir=settings.functions_dir)
    app.state.function_store.load()

    # Table store (Clay-style table builder)
    from app.core.table_store import TableStore
    app.state.table_store = TableStore(data_dir=settings.data_dir)
    app.state.table_store.load()

    # Execution history (function run records)
    app.state.execution_history = ExecutionHistory(data_dir=settings.data_dir)

    # Local job queue (CLI runner picks up jobs from here)
    app.state.local_job_queue = LocalJobQueue(data_dir=settings.data_dir)

    # Channel store (chat session persistence)
    app.state.channel_store = ChannelStore(data_dir=settings.data_dir)
    app.state.channel_store.load()

    # Channel orchestrator (chat function execution)
    app.state.channel_orchestrator = ChannelOrchestrator(
        function_store=app.state.function_store,
        pool=app.state.pool,
    )

    # Channel proxy (free chat via Claude Code Channels)
    app.state.channel_proxy = ChannelProxy()
    logger.info("  Free chat: channel proxy → %s", settings.channel_server_url)

    # Portal store (client engagement hubs)
    from app.core.portal_store import PortalStore
    app.state.portal_store = PortalStore(
        clients_dir=settings.clients_dir,
        data_dir=settings.data_dir,
    )

    # Portal notifier (Slack notifications for portal events)
    from app.core.portal_notifier import PortalNotifier
    app.state.portal_notifier = PortalNotifier(app.state.portal_store)

    # Email notifier (email notifications for portal events)
    from app.core.email_notifier import EmailNotifier
    app.state.email_notifier = EmailNotifier(
        portal_store=app.state.portal_store,
        smtp_host=getattr(settings, "smtp_host", ""),
        smtp_port=getattr(settings, "smtp_port", 587),
        smtp_user=getattr(settings, "smtp_user", ""),
        smtp_pass=getattr(settings, "smtp_pass", ""),
        smtp_from=getattr(settings, "smtp_from", ""),
        reply_domain=getattr(settings, "portal_reply_domain", ""),
    )
    if app.state.email_notifier.available:
        logger.info("  Email notifications: enabled")
    else:
        logger.info("  Email notifications: disabled (no SMTP config)")

    # Reminder worker (due date notifications every 6h)
    from app.core.reminder_worker import ReminderWorker
    app.state.reminder_worker_portal = ReminderWorker(
        portal_store=app.state.portal_store,
        portal_notifier=app.state.portal_notifier,
    )

    # Status report worker (weekly AI-generated reports)
    from app.core.status_report_worker import StatusReportWorker
    app.state.status_report_worker = StatusReportWorker(
        portal_store=app.state.portal_store,
        portal_notifier=app.state.portal_notifier,
        email_notifier=app.state.email_notifier,
    )

    # Google Sheets integration (graceful degradation if gws not installed)
    from app.core.sheets_client import SheetsClient
    from app.core.drive_sync import DriveSync
    sheets_client = SheetsClient()
    if sheets_client.available:
        app.state.drive_sync = DriveSync(sheets_client)
        # Portal sync (pushes portal content to Google Docs)
        from app.core.portal_sync import PortalSync
        app.state.portal_sync = PortalSync(sheets_client, app.state.portal_store)
        from app.core.portal_doc_sync import PortalDocSync
        app.state.portal_doc_sync = PortalDocSync(sheets_client, app.state.portal_store)
        # Table ↔ Sheets adapter
        from app.core.sheets_adapter import SheetsAdapter
        app.state.sheets_adapter = SheetsAdapter(sheets_client, app.state.table_store)
        logger.info("  Google Sheets: enabled")
    else:
        app.state.drive_sync = None
        app.state.portal_sync = None
        app.state.portal_doc_sync = None
        app.state.sheets_adapter = None
        logger.info("  Google Sheets: disabled (gws CLI not found)")

    # Skill version store
    app.state.skill_version_store = SkillVersionStore(
        data_dir=settings.data_dir, skills_dir=settings.skills_dir
    )
    app.state.skill_version_store.load()

    # Request deduplication (60s window)
    app.state.dedup = RequestDeduplicator(window_seconds=60)

    # Bridge store (synchronous webhook bridge — Promise Parking)
    app.state.bridge_store = BridgeStore(max_pending=100, timeout_s=300)

    # Run tracker (table execution history)
    app.state.run_tracker = RunTracker(data_dir=settings.data_dir)

    # Script store (reusable named scripts)
    app.state.script_store = ScriptStore(data_dir=settings.data_dir)
    app.state.script_store.load()

    # Circuit breaker (per-model, trips after 3 failures, 60s recovery)
    app.state.circuit_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=60)

    # Prompt cache (5 min TTL for static prompt portions)
    app.state.prompt_cache = PromptCache(ttl=300, max_size=settings.prompt_cache_max_entries)

    # Feedback loop (automated re-runs with learnings)
    app.state.feedback_loop = FeedbackLoop()

    # Pattern miner (cross-client feedback analysis)
    from app.core.pattern_miner import PatternMiner
    app.state.pattern_miner = PatternMiner(knowledge_dir=settings.knowledge_dir)

    # Log research API availability
    if settings.parallel_api_key:
        logger.info("  Parallel.ai research: enabled")
    else:
        logger.info("  Parallel.ai research: disabled (no PARALLEL_API_KEY)")
    if settings.sumble_api_key:
        logger.info("  Sumble research: enabled")
    else:
        logger.info("  Sumble research: disabled (no SUMBLE_API_KEY)")
    if settings.findymail_api_key:
        logger.info("  Findymail enrichment: enabled")
    else:
        logger.info("  Findymail enrichment: disabled (no FINDYMAIL_API_KEY)")

    # Retry worker
    app.state.retry_worker = RetryWorker(
        data_dir=settings.data_dir,
        event_bus=app.state.event_bus,
        check_interval=settings.retry_check_interval,
    )
    app.state.retry_worker.load()
    app.state.job_queue._retry_worker = app.state.retry_worker
    app.state.destination_store._retry_worker = app.state.retry_worker

    # Subscription monitor
    app.state.subscription_monitor = SubscriptionMonitor(
        pool=app.state.pool,
        job_queue=app.state.job_queue,
        usage_store=app.state.usage_store,
        event_bus=app.state.event_bus,
        normal_interval=settings.subscription_probe_interval,
        degraded_interval=settings.subscription_probe_interval_degraded,
        paused_interval=settings.subscription_probe_interval_paused,
    )

    # Cleanup worker
    app.state.cleanup_worker = DataCleanupWorker(
        cache=app.state.cache,
        job_queue=app.state.job_queue,
        usage_store=app.state.usage_store,
        feedback_store=app.state.feedback_store,
        prompt_cache=app.state.prompt_cache,
        feedback_loop=app.state.feedback_loop,
        retry_worker=app.state.retry_worker,
        interval_seconds=settings.cleanup_interval_seconds,
        job_retention_hours=settings.cleanup_job_retention_hours,
        feedback_retention_days=settings.cleanup_feedback_retention_days,
        usage_retention_days=settings.cleanup_usage_retention_days,
        failed_callback_days=settings.cleanup_failed_callback_days,
    )

    await app.state.job_queue.start_workers(num_workers=settings.max_workers)
    await app.state.retry_worker.start()
    await app.state.subscription_monitor.start()
    await app.state.cleanup_worker.start()
    await app.state.reminder_worker_portal.start()
    await app.state.status_report_worker.start()

    skills = list_skills()

    # Log RSS at startup for memory baseline
    from app.core.cleanup_worker import _get_rss_mb
    logger.info("Clay Webhook OS v3.0 started — Autopilot Mode (RSS: %.1fMB)", _get_rss_mb())


@app.on_event("shutdown")
async def shutdown():
    logger.info("Clay Webhook OS shutting down — stopping background workers...")

    # Stop background workers gracefully
    if hasattr(app.state, "job_queue"):
        await app.state.job_queue.stop()
        logger.info("  Job queue stopped")

    if hasattr(app.state, "retry_worker"):
        await app.state.retry_worker.stop()
        logger.info("  Retry worker stopped")

    if hasattr(app.state, "subscription_monitor"):
        await app.state.subscription_monitor.stop()
        logger.info("  Subscription monitor stopped")

    if hasattr(app.state, "cleanup_worker"):
        await app.state.cleanup_worker.stop()
        logger.info("  Cleanup worker stopped")

    if hasattr(app.state, "reminder_worker_portal"):
        await app.state.reminder_worker_portal.stop()
        logger.info("  Portal reminder worker stopped")

    if hasattr(app.state, "status_report_worker"):
        await app.state.status_report_worker.stop()
        logger.info("  Status report worker stopped")

    if hasattr(app.state, "channel_proxy"):
        await app.state.channel_proxy.close()
        logger.info("  Channel proxy closed")

    if hasattr(app.state, "portal_notifier"):
        await app.state.portal_notifier.close()
        logger.info("  Portal notifier closed")

    if hasattr(app.state, "bridge_store"):
        await app.state.bridge_store.shutdown()
        logger.info("  Bridge store shutdown")

    logger.info("Shutdown complete")
