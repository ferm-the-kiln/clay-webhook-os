import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.cache import ResultCache
from app.core.event_bus import EventBus
from app.core.job_queue import JobQueue
from app.core.scheduler import BatchScheduler
from app.core.skill_loader import list_skills
from app.core.worker_pool import WorkerPool
from app.middleware.auth import ApiKeyMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.core.context_index import ContextIndex
from app.core.prefetch import ExaPrefetcher
from app.core.context_store import ContextStore
from app.core.destination_store import DestinationStore
from app.core.feedback_store import FeedbackStore
from app.core.learning_engine import LearningEngine
from app.core.memory_store import MemoryStore
from app.core.pipeline_store import PipelineStore
from app.core.play_store import PlayStore
from app.core.usage_store import UsageStore
from app.core.experiment_store import ExperimentStore
from app.core.cleanup_worker import DataCleanupWorker
from app.core.retry_worker import RetryWorker
from app.core.subscription_monitor import SubscriptionMonitor
from app.routers import batch, context, destinations, experiments, feedback, health, pipeline, pipelines, plays, usage, webhook

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

# Middleware (order matters: error handler wraps auth wraps CORS wraps routes)
app.add_middleware(ErrorHandlerMiddleware)
app.add_middleware(ApiKeyMiddleware)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
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


@app.on_event("startup")
async def startup():
    app.state.pool = WorkerPool(max_workers=settings.max_workers)
    app.state.cache = ResultCache(ttl=settings.cache_ttl)
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

    # Exa pre-fetch (optional — enhances agent skills)
    if settings.exa_api_key:
        from exa_py import Exa
        exa_client = Exa(api_key=settings.exa_api_key)
        app.state.prefetcher = ExaPrefetcher(
            exa_client=exa_client,
            num_results=settings.exa_num_results,
            cache_ttl=settings.exa_cache_ttl,
        )
        logger.info("  Exa pre-fetch: enabled")
    else:
        app.state.prefetcher = None
        logger.info("  Exa pre-fetch: disabled (no EXA_API_KEY)")
    app.state.job_queue._prefetcher = app.state.prefetcher

    # Sumble pre-fetch (optional — structured company intelligence)
    if settings.sumble_api_key:
        from app.core.sumble_prefetcher import SumblePrefetcher
        app.state.sumble_prefetcher = SumblePrefetcher(
            api_key=settings.sumble_api_key,
            base_url=settings.sumble_base_url,
            cache_ttl=settings.sumble_cache_ttl,
            timeout=settings.sumble_timeout,
        )
        logger.info("  Sumble pre-fetch: enabled")
    else:
        app.state.sumble_prefetcher = None
        logger.info("  Sumble pre-fetch: disabled (no SUMBLE_API_KEY)")
    app.state.job_queue._sumble_prefetcher = app.state.sumble_prefetcher

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
    logger.info("Clay Webhook OS v3.0 started — Autopilot Mode")
    logger.info("  Engine: claude --print (Max subscription)")
    logger.info("  Workers: %d", settings.max_workers)
    logger.info("  Queue workers: %d", settings.max_workers)
    logger.info("  Skills: %s", ", ".join(skills) if skills else "none")
    logger.info("  Auth: %s", "enabled" if settings.webhook_api_key else "disabled")
    logger.info("  Cache TTL: %ds", settings.cache_ttl)
    logger.info("  Smart routing: %s", "enabled" if settings.enable_smart_routing else "disabled")
    logger.info("  Context index: %d documents", app.state.context_index.doc_count)
    logger.info("  Features: smart-pipelines, feedback-loops, retry, SSE, model-router, sub-monitor, cleanup, memory, semantic-context, parallel-pipelines, learning-engine")
