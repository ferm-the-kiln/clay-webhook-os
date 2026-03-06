import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum

import httpx

from app.config import settings
from app.core.context_assembler import build_prompt
from app.core.skill_loader import load_context_files, load_skill
from app.core.worker_pool import WorkerPool

logger = logging.getLogger("clay-webhook-os")


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"


@dataclass
class Job:
    id: str
    skill: str
    data: dict
    instructions: str | None
    model: str
    callback_url: str
    row_id: str | None
    status: JobStatus = JobStatus.queued
    result: dict | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    duration_ms: int = 0


class JobQueue:
    def __init__(self, pool: WorkerPool):
        self._pool = pool
        self._queue: asyncio.Queue[Job] = asyncio.Queue()
        self._jobs: dict[str, Job] = {}
        self._workers: list[asyncio.Task] = []

    @property
    def pending(self) -> int:
        return self._queue.qsize()

    @property
    def total(self) -> int:
        return len(self._jobs)

    def get_job(self, job_id: str) -> Job | None:
        return self._jobs.get(job_id)

    def get_jobs(self, limit: int = 50) -> list[dict]:
        jobs = sorted(self._jobs.values(), key=lambda j: j.created_at, reverse=True)[:limit]
        return [
            {
                "id": j.id,
                "skill": j.skill,
                "row_id": j.row_id,
                "status": j.status,
                "duration_ms": j.duration_ms,
                "created_at": j.created_at,
            }
            for j in jobs
        ]

    async def enqueue(
        self,
        skill: str,
        data: dict,
        instructions: str | None,
        model: str,
        callback_url: str,
        row_id: str | None,
    ) -> str:
        job_id = uuid.uuid4().hex[:12]
        job = Job(
            id=job_id,
            skill=skill,
            data=data,
            instructions=instructions,
            model=model,
            callback_url=callback_url,
            row_id=row_id,
        )
        self._jobs[job_id] = job
        await self._queue.put(job)
        logger.info("[queue] Job %s enqueued (skill=%s, queue_size=%d)", job_id, skill, self._queue.qsize())
        return job_id

    async def start_workers(self, num_workers: int = 3):
        for i in range(num_workers):
            task = asyncio.create_task(self._worker(i))
            self._workers.append(task)
        logger.info("[queue] Started %d queue workers", num_workers)

    async def stop(self):
        for task in self._workers:
            task.cancel()
        await asyncio.gather(*self._workers, return_exceptions=True)

    async def _worker(self, worker_id: int):
        while True:
            job = await self._queue.get()
            job.status = JobStatus.processing
            logger.info("[queue] Worker %d processing job %s (skill=%s)", worker_id, job.id, job.skill)

            try:
                # Load skill
                skill_content = load_skill(job.skill)
                if skill_content is None:
                    raise ValueError(f"Skill '{job.skill}' not found")

                # Build prompt
                context_files = load_context_files(skill_content, job.data)
                prompt = build_prompt(skill_content, context_files, job.data, job.instructions)

                # Execute
                result = await self._pool.submit(prompt, job.model, settings.request_timeout)
                parsed = result["result"]

                job.status = JobStatus.completed
                job.result = parsed
                job.duration_ms = result["duration_ms"]
                job.completed_at = time.time()

                # Send callback
                await self._send_callback(job)

            except Exception as e:
                job.status = JobStatus.failed
                job.error = str(e)
                job.completed_at = time.time()
                logger.error("[queue] Job %s failed: %s", job.id, e)

                # Send error callback
                await self._send_callback(job)

            finally:
                self._queue.task_done()

    async def _send_callback(self, job: Job):
        if not job.callback_url:
            return

        payload = {
            "job_id": job.id,
            "skill": job.skill,
            "status": job.status,
        }

        if job.row_id:
            payload["row_id"] = job.row_id

        if job.status == JobStatus.completed:
            payload.update(job.result)
            payload["_meta"] = {
                "skill": job.skill,
                "model": job.model,
                "duration_ms": job.duration_ms,
                "cached": False,
                "async": True,
            }
        else:
            payload["error"] = True
            payload["error_message"] = job.error

        try:
            async with httpx.AsyncClient(timeout=30) as client:
                resp = await client.post(job.callback_url, json=payload)
                logger.info(
                    "[queue] Callback sent for job %s → %s (status=%d)",
                    job.id, job.callback_url, resp.status_code,
                )
        except Exception as e:
            logger.error("[queue] Callback failed for job %s: %s", job.id, e)
