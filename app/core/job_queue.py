import asyncio
import logging
import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING

import httpx

from app.config import settings
from app.core.claude_executor import SubscriptionLimitError
from app.core.context_assembler import build_agent_prompts, build_prompt
from app.core.model_router import resolve_model
from app.core.skill_loader import load_context_files, load_skill, load_skill_config, load_skill_variant
from app.core.token_estimator import estimate_cost, estimate_tokens
from app.core.worker_pool import WorkerPool

if TYPE_CHECKING:
    from app.core.cache import ResultCache
    from app.core.event_bus import EventBus

logger = logging.getLogger("clay-webhook-os")

PRIORITY_WEIGHTS = {"high": 0, "normal": 1, "low": 2}


class JobStatus(str, Enum):
    queued = "queued"
    processing = "processing"
    completed = "completed"
    failed = "failed"
    retrying = "retrying"
    dead_letter = "dead_letter"


@dataclass
class Job:
    id: str
    skill: str
    data: dict
    instructions: str | None
    model: str
    callback_url: str
    row_id: str | None
    priority: str = "normal"
    skills: list[str] | None = None
    status: JobStatus = JobStatus.queued
    result: dict | None = None
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    completed_at: float | None = None
    duration_ms: int = 0
    retry_count: int = 0
    max_retries: int = 3
    next_retry_at: float | None = None
    input_tokens_est: int = 0
    output_tokens_est: int = 0
    cost_est_usd: float = 0.0
    batch_id: str | None = None
    experiment_id: str | None = None
    variant_id: str | None = None

    def __lt__(self, other: "Job") -> bool:
        return PRIORITY_WEIGHTS.get(self.priority, 1) < PRIORITY_WEIGHTS.get(other.priority, 1)

    def __le__(self, other: "Job") -> bool:
        return PRIORITY_WEIGHTS.get(self.priority, 1) <= PRIORITY_WEIGHTS.get(other.priority, 1)


class JobQueue:
    def __init__(
        self,
        pool: WorkerPool,
        cache: "ResultCache | None" = None,
        event_bus: "EventBus | None" = None,
    ):
        self._pool = pool
        self._cache = cache
        self._event_bus = event_bus
        self._queue: asyncio.PriorityQueue[Job] = asyncio.PriorityQueue()
        self._jobs: dict[str, Job] = {}
        self._workers: list[asyncio.Task] = []
        self._batches: dict[str, list[str]] = {}
        self._resume_event = asyncio.Event()
        self._resume_event.set()  # Starts unpaused
        self._retry_worker = None

    def pause(self) -> None:
        self._resume_event.clear()
        logger.info("[queue] Paused — workers will block before next job")

    def resume(self) -> None:
        self._resume_event.set()
        logger.info("[queue] Resumed — workers unblocked")

    @property
    def is_paused(self) -> bool:
        return not self._resume_event.is_set()

    def register_batch(self, batch_id: str, job_ids: list[str]) -> None:
        self._batches[batch_id] = job_ids

    def list_batches(self) -> list[dict]:
        """Return summary info for all registered batches, newest first."""
        result = []
        for batch_id, job_ids in self._batches.items():
            jobs = [self._jobs[jid] for jid in job_ids if jid in self._jobs]
            total = len(jobs)
            completed = sum(1 for j in jobs if j.status == "completed")
            failed = sum(1 for j in jobs if j.status in ("failed", "dead_letter"))
            done = (completed + failed) == total and total > 0
            # Use first job's skill and created_at
            skill = jobs[0].skill if jobs else ""
            created_at = min((j.created_at for j in jobs), default=0)
            result.append({
                "batch_id": batch_id,
                "skill": skill,
                "total_rows": total,
                "completed": completed,
                "failed": failed,
                "done": done,
                "created_at": created_at,
            })
        result.sort(key=lambda b: b["created_at"], reverse=True)
        return result

    def get_batch_jobs(self, batch_id: str) -> list[Job] | None:
        job_ids = self._batches.get(batch_id)
        if job_ids is None:
            return None
        return [self._jobs[jid] for jid in job_ids if jid in self._jobs]

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
                "skill": j.skills[0] if j.skills else j.skill,
                "row_id": j.row_id,
                "status": j.status,
                "duration_ms": j.duration_ms,
                "created_at": j.created_at,
                "retry_count": j.retry_count,
                "priority": j.priority,
                "input_tokens_est": j.input_tokens_est,
                "output_tokens_est": j.output_tokens_est,
                "cost_est_usd": j.cost_est_usd,
                "batch_id": j.batch_id,
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
        priority: str = "normal",
        max_retries: int = 3,
        skills: list[str] | None = None,
        batch_id: str | None = None,
        experiment_id: str | None = None,
        variant_id: str | None = None,
    ) -> str:
        # Cache dedup: check cache before creating job
        if self._cache is not None:
            cached = self._cache.get(skill, data, instructions)
            if cached is not None:
                job_id = uuid.uuid4().hex[:12]
                job = Job(
                    id=job_id,
                    skill=skill,
                    data=data,
                    instructions=instructions,
                    model=model,
                    callback_url=callback_url,
                    row_id=row_id,
                    priority=priority,
                    max_retries=max_retries,
                    skills=skills,
                    status=JobStatus.completed,
                    result=cached,
                    completed_at=time.time(),
                    batch_id=batch_id,
                    experiment_id=experiment_id,
                    variant_id=variant_id,
                )
                self._jobs[job_id] = job
                # Send callback immediately for cached results
                await self._send_callback(job, cached_result=True)
                if self._event_bus:
                    self._event_bus.publish("job_created", {"job_id": job_id, "skill": skill, "status": "completed", "cached": True})
                logger.info("[queue] Job %s cache hit (skill=%s)", job_id, skill)
                return job_id

        job_id = uuid.uuid4().hex[:12]
        job = Job(
            id=job_id,
            skill=skill,
            data=data,
            instructions=instructions,
            model=model,
            callback_url=callback_url,
            row_id=row_id,
            priority=priority,
            max_retries=max_retries,
            skills=skills,
            batch_id=batch_id,
            experiment_id=experiment_id,
            variant_id=variant_id,
        )
        self._jobs[job_id] = job
        await self._queue.put(job)
        if self._event_bus:
            self._event_bus.publish("job_created", {"job_id": job_id, "skill": skill, "status": "queued", "priority": priority})
        logger.info("[queue] Job %s enqueued (skill=%s, priority=%s, queue_size=%d)", job_id, skill, priority, self._queue.qsize())
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

    def prune_completed(self, cutoff: float) -> int:
        """Remove completed/failed/dead_letter jobs older than cutoff timestamp."""
        terminal = {JobStatus.completed, JobStatus.failed, JobStatus.dead_letter}
        to_remove = [
            jid for jid, j in self._jobs.items()
            if j.status in terminal and j.created_at < cutoff
        ]
        for jid in to_remove:
            del self._jobs[jid]
        return len(to_remove)

    async def _worker(self, worker_id: int):
        while True:
            await self._resume_event.wait()
            job = await self._queue.get()
            job.status = JobStatus.processing
            if self._event_bus:
                self._event_bus.publish("job_updated", {"job_id": job.id, "status": "processing"})
            logger.info("[queue] Worker %d processing job %s (skill=%s)", worker_id, job.id, job.skill)

            try:
                # Skill chaining: if multiple skills, run as chain
                if job.skills and len(job.skills) > 1:
                    from app.core.pipeline_runner import run_skill_chain
                    result = await run_skill_chain(
                        skills=job.skills,
                        data=job.data,
                        instructions=job.instructions,
                        model=job.model,
                        pool=self._pool,
                        cache=self._cache,
                    )
                    job.status = JobStatus.completed
                    job.result = result
                    job.duration_ms = result.get("total_duration_ms", 0)
                    job.completed_at = time.time()
                    job.input_tokens_est = estimate_tokens(result.get("total_prompt_chars", 0))
                    job.output_tokens_est = estimate_tokens(result.get("total_response_chars", 0))
                    job.cost_est_usd = estimate_cost(job.model, job.input_tokens_est, job.output_tokens_est)
                    self._record_usage(job, result.get("usage"))
                    if self._event_bus:
                        self._event_bus.publish("job_updated", {"job_id": job.id, "status": "completed"})
                    await self._send_callback(job)
                else:
                    # Single skill execution (load variant if set)
                    if job.variant_id and job.variant_id != "default":
                        skill_content = load_skill_variant(job.skill, job.variant_id)
                    else:
                        skill_content = load_skill(job.skill)
                    if skill_content is None:
                        raise ValueError(f"Skill '{job.skill}' not found")

                    context_files = load_context_files(skill_content, job.data, skill_name=job.skill)
                    skill_cfg = load_skill_config(job.skill)
                    is_agent = skill_cfg.get("executor") == "agent"

                    # Get memory and context index if available
                    mem = getattr(self, '_memory_store', None)
                    ctx_idx = getattr(self, '_context_index', None)

                    # Research skill pre-fetch: fetch external data and merge into job.data
                    from app.routers.webhook import _maybe_fetch_research
                    await _maybe_fetch_research(job.skill, job.data)

                    if is_agent:
                        prompt = build_agent_prompts(
                            skill_content, context_files, job.data, job.instructions,
                            memory_store=mem, context_index=ctx_idx,
                        )
                    else:
                        prompt = build_prompt(
                            skill_content, context_files, job.data, job.instructions,
                            memory_store=mem, context_index=ctx_idx,
                        )

                    # Smart model routing: refine model after prompt is built
                    if settings.enable_smart_routing:
                        job.model = resolve_model(
                            request_model=job.model if job.model != settings.default_model else None,
                            skill_config=skill_cfg,
                            prompt=prompt,
                            context_file_count=len(context_files),
                        )

                    # Route to appropriate executor
                    agent_timeout = skill_cfg.get("timeout", settings.request_timeout) if is_agent else settings.request_timeout
                    agent_max_turns = skill_cfg.get("max_turns", 15) if is_agent else 1
                    agent_tools = skill_cfg.get("allowed_tools") if is_agent else None
                    executor_type = "agent" if is_agent else "cli"

                    result = await self._pool.submit(
                        prompt, job.model, agent_timeout,
                        executor_type=executor_type,
                        max_turns=agent_max_turns,
                        allowed_tools=agent_tools,
                    )
                    parsed = result["result"]

                    job.status = JobStatus.completed
                    job.result = parsed
                    job.duration_ms = result["duration_ms"]
                    job.completed_at = time.time()
                    job.input_tokens_est = estimate_tokens(result.get("prompt_chars", 0))
                    job.output_tokens_est = estimate_tokens(result.get("response_chars", 0))
                    job.cost_est_usd = estimate_cost(job.model, job.input_tokens_est, job.output_tokens_est)

                    self._record_usage(job, result.get("usage"))

                    # Cache the result
                    if self._cache is not None:
                        self._cache.put(job.skill, job.data, job.instructions, parsed)

                    # Store memory for this entity
                    if hasattr(self, '_memory_store') and self._memory_store:
                        try:
                            self._memory_store.store_from_data(job.data, job.skill, parsed)
                        except Exception:
                            pass  # Non-critical

                    if self._event_bus:
                        self._event_bus.publish("job_updated", {"job_id": job.id, "status": "completed"})
                    await self._send_callback(job)

                # Update experiment results if this job is part of an experiment
                if job.experiment_id and job.variant_id and job.status == JobStatus.completed:
                    try:
                        # Access store via import — it's set on app.state but we don't have app ref here
                        # Instead we'll use a reference stored on the queue
                        if hasattr(self, '_experiment_store') and self._experiment_store:
                            self._experiment_store.update_experiment_results(
                                job.experiment_id,
                                job.variant_id,
                                job.duration_ms,
                                job.input_tokens_est + job.output_tokens_est,
                            )
                    except Exception:
                        pass  # Non-critical

            except SubscriptionLimitError as e:
                # Subscription exhausted — no point retrying, dead-letter immediately
                job.status = JobStatus.dead_letter
                job.error = str(e)
                job.completed_at = time.time()
                logger.error("[queue] Job %s dead-lettered (subscription limit): %s", job.id, e)
                if hasattr(self, '_usage_store') and self._usage_store:
                    self._usage_store.record_error("subscription_limit", str(e))
                if self._event_bus:
                    self._event_bus.publish("job_updated", {"job_id": job.id, "status": "dead_letter", "reason": "subscription_limit"})
                await self._send_callback(job)

            except Exception as e:
                if job.retry_count < job.max_retries:
                    job.retry_count += 1
                    job.status = JobStatus.retrying
                    delay = 2 ** job.retry_count
                    job.next_retry_at = time.time() + delay
                    logger.warning("[queue] Job %s retry %d/%d in %ds: %s", job.id, job.retry_count, job.max_retries, delay, e)
                    if self._event_bus:
                        self._event_bus.publish("job_updated", {"job_id": job.id, "status": "retrying", "retry_count": job.retry_count})
                    # Schedule re-enqueue after delay (task_done handled by finally)
                    loop = asyncio.get_running_loop()
                    loop.call_later(delay, lambda j=job: asyncio.ensure_future(self._re_enqueue(j)))
                else:
                    job.status = JobStatus.dead_letter
                    job.error = str(e)
                    job.completed_at = time.time()
                    logger.error("[queue] Job %s dead-lettered after %d retries: %s", job.id, job.max_retries, e)
                    if self._event_bus:
                        self._event_bus.publish("job_updated", {"job_id": job.id, "status": "dead_letter"})
                    await self._send_callback(job)

            finally:
                self._queue.task_done()

    def _record_usage(self, job: Job, usage_envelope: dict | None) -> None:
        if not hasattr(self, '_usage_store') or not self._usage_store:
            return
        from app.models.usage import UsageEntry

        if usage_envelope and isinstance(usage_envelope, dict):
            input_tokens = usage_envelope.get("input_tokens", 0)
            output_tokens = usage_envelope.get("output_tokens", 0)
            is_actual = True
        else:
            input_tokens = job.input_tokens_est
            output_tokens = job.output_tokens_est
            is_actual = False

        entry = UsageEntry(
            job_id=job.id,
            skill=job.skill,
            model=job.model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            is_actual=is_actual,
        )
        self._usage_store.record(entry)

    async def _re_enqueue(self, job: Job):
        job.status = JobStatus.queued
        job.next_retry_at = None
        await self._queue.put(job)
        logger.info("[queue] Job %s re-enqueued (retry %d/%d)", job.id, job.retry_count, job.max_retries)

    async def _send_callback(self, job: Job, cached_result: bool = False):
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
                "cached": cached_result,
                "async": True,
            }
        else:
            payload["error"] = True
            payload["error_message"] = job.error

        max_retries = 3
        delays = [1, 4, 16]
        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient(timeout=30) as client:
                    resp = await client.post(job.callback_url, json=payload)
                    logger.info(
                        "[queue] Callback sent for job %s → %s (status=%d, attempt=%d)",
                        job.id, job.callback_url, resp.status_code, attempt + 1,
                    )
                    if resp.status_code < 500:
                        return
            except Exception as e:
                logger.warning(
                    "[queue] Callback attempt %d/%d failed for job %s: %s",
                    attempt + 1, max_retries, job.id, e,
                )
            if attempt < max_retries - 1:
                await asyncio.sleep(delays[attempt])

        logger.error("[queue] Callback permanently failed for job %s after %d attempts", job.id, max_retries)
        if self._retry_worker:
            headers = {"Content-Type": "application/json"}
            self._retry_worker.enqueue(job.callback_url, payload, headers, job_id=job.id)
        else:
            self._log_failed_callback(job, payload)

    def _log_failed_callback(self, job: Job, payload: dict):
        import json as _json
        from pathlib import Path
        failed_path = Path("data/failed_callbacks.json")
        failed_path.parent.mkdir(parents=True, exist_ok=True)
        entries = []
        if failed_path.exists():
            try:
                entries = _json.loads(failed_path.read_text())
            except Exception:
                entries = []
        entries.append({
            "job_id": job.id,
            "callback_url": job.callback_url,
            "skill": job.skill,
            "status": job.status,
            "timestamp": time.time(),
        })
        # Keep last 1000 entries
        entries = entries[-1000:]
        failed_path.write_text(_json.dumps(entries, indent=2))
