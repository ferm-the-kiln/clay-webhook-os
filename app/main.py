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
from app.core.context_store import ContextStore
from app.core.destination_store import DestinationStore
from app.core.feedback_store import FeedbackStore
from app.core.pipeline_store import PipelineStore
from app.core.play_store import PlayStore
from app.core.usage_store import UsageStore
from app.core.experiment_store import ExperimentStore
from app.core.campaign_store import CampaignStore
from app.core.review_queue import ReviewQueue
from app.core.campaign_runner import CampaignRunner
from app.routers import batch, campaigns, context, destinations, experiments, feedback, health, pipeline, pipelines, plays, review_queue, usage, webhook

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
app.include_router(campaigns.router)
app.include_router(plays.router)
app.include_router(review_queue.router)
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

    # Phase 3: Campaign system
    app.state.campaign_store = CampaignStore(data_dir=settings.data_dir)
    app.state.campaign_store.load()
    app.state.review_queue = ReviewQueue(data_dir=settings.data_dir)
    app.state.review_queue.load()
    app.state.campaign_runner = CampaignRunner(
        campaign_store=app.state.campaign_store,
        review_queue=app.state.review_queue,
        pool=app.state.pool,
        cache=app.state.cache,
        destination_store=app.state.destination_store,
        job_queue=app.state.job_queue,
    )

    await app.state.job_queue.start_workers(num_workers=settings.max_workers)
    await app.state.scheduler.start(app.state.job_queue)
    await app.state.campaign_runner.start()

    skills = list_skills()
    logger.info("Clay Webhook OS v3.0 started — Autopilot Mode")
    logger.info("  Engine: claude --print (Max subscription)")
    logger.info("  Workers: %d", settings.max_workers)
    logger.info("  Queue workers: %d", settings.max_workers)
    logger.info("  Skills: %s", ", ".join(skills) if skills else "none")
    logger.info("  Auth: %s", "enabled" if settings.webhook_api_key else "disabled")
    logger.info("  Cache TTL: %ds", settings.cache_ttl)
    logger.info("  Features: campaigns, review-queue, smart-pipelines, feedback-loops, retry, SSE")
