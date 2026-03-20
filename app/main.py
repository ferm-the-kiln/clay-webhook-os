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
from app.core.experiment_store import ExperimentStore
from app.core.feedback_loop import FeedbackLoop
from app.core.feedback_store import FeedbackStore
from app.core.function_store import FunctionStore
from app.core.job_queue import JobQueue
from app.core.learning_engine import LearningEngine
from app.core.memory_store import MemoryStore
from app.core.pipeline_store import PipelineStore
from app.core.play_store import PlayStore
from app.core.prompt_cache import PromptCache
from app.core.retry_worker import RetryWorker
from app.core.scheduler import BatchScheduler
from app.core.skill_loader import list_skills
from app.core.skill_version_store import SkillVersionStore
from app.core.subscription_monitor import SubscriptionMonitor
from app.core.usage_store import UsageStore
from app.core.worker_pool import WorkerPool
from app.middleware.auth import ApiKeyMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.middleware.rate_limiter import RateLimitMiddleware
from app.middleware.security_headers import SecurityHeadersMiddleware
from app.routers import (
    batch,
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
app.add_middleware(ApiKeyMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["Content-Type", "x-api-key"],
)

# Routers
app.include_router(health.router)
app.include_router(webhook.router)
app.include_router(pipeline.router)
app.include_router(batch.router)
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
    app.state.scheduler = BatchScheduler()
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

    # Dataset store
    app.state.dataset_store = DatasetStore(data_dir=settings.data_dir)
    app.state.dataset_store.load()

    # Function store
    app.state.function_store = FunctionStore(functions_dir=settings.functions_dir)
    app.state.function_store.load()

    # Skill version store
    app.state.skill_version_store = SkillVersionStore(
        data_dir=settings.data_dir, skills_dir=settings.skills_dir
    )
    app.state.skill_version_store.load()

    # Request deduplication (60s window)
    app.state.dedup = RequestDeduplicator(window_seconds=60)

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
        scheduler=app.state.scheduler,
        usage_store=app.state.usage_store,
        feedback_store=app.state.feedback_store,
        prompt_cache=app.state.prompt_cache,
        interval_seconds=settings.cleanup_interval_seconds,
        job_retention_hours=settings.cleanup_job_retention_hours,
        feedback_retention_days=settings.cleanup_feedback_retention_days,
        usage_retention_days=settings.cleanup_usage_retention_days,
        failed_callback_days=settings.cleanup_failed_callback_days,
    )

    await app.state.job_queue.start_workers(num_workers=settings.max_workers)
    await app.state.scheduler.start(app.state.job_queue)
    await app.state.retry_worker.start()
    await app.state.subscription_monitor.start()
    await app.state.cleanup_worker.start()

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

    if hasattr(app.state, "scheduler"):
        await app.state.scheduler.stop()
        logger.info("  Scheduler stopped")

    if hasattr(app.state, "retry_worker"):
        await app.state.retry_worker.stop()
        logger.info("  Retry worker stopped")

    if hasattr(app.state, "subscription_monitor"):
        await app.state.subscription_monitor.stop()
        logger.info("  Subscription monitor stopped")

    if hasattr(app.state, "cleanup_worker"):
        await app.state.cleanup_worker.stop()
        logger.info("  Cleanup worker stopped")

    logger.info("Shutdown complete")
