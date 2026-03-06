import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.core.cache import ResultCache
from app.core.job_queue import JobQueue
from app.core.skill_loader import list_skills
from app.core.worker_pool import WorkerPool
from app.middleware.auth import ApiKeyMiddleware
from app.middleware.error_handler import ErrorHandlerMiddleware
from app.routers import batch, health, pipeline, webhook

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger("clay-webhook-os")

app = FastAPI(
    title="Clay Webhook OS",
    description="AI-powered webhook server for Clay HTTP Actions",
    version="1.0.0",
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


@app.on_event("startup")
async def startup():
    app.state.pool = WorkerPool(max_workers=settings.max_workers)
    app.state.cache = ResultCache(ttl=settings.cache_ttl)
    app.state.job_queue = JobQueue(pool=app.state.pool)
    await app.state.job_queue.start_workers(num_workers=settings.max_workers)

    skills = list_skills()
    logger.info("Clay Webhook OS started")
    logger.info("  Engine: claude --print (Max subscription)")
    logger.info("  Workers: %d", settings.max_workers)
    logger.info("  Queue workers: %d", settings.max_workers)
    logger.info("  Skills: %s", ", ".join(skills) if skills else "none")
    logger.info("  Auth: %s", "enabled" if settings.webhook_api_key else "disabled")
    logger.info("  Cache TTL: %ds", settings.cache_ttl)
