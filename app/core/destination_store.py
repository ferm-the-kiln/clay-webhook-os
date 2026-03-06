import asyncio
import json
import logging
import time
import uuid
from pathlib import Path

import httpx

from app.core.job_queue import Job, JobStatus
from app.models.destinations import (
    CreateDestinationRequest,
    Destination,
    DestinationType,
    PushResult,
    UpdateDestinationRequest,
)

logger = logging.getLogger("clay-webhook-os")


class DestinationStore:
    def __init__(self, data_dir: Path):
        self._data_dir = data_dir
        self._file = data_dir / "destinations.json"
        self._destinations: dict[str, Destination] = {}

    def load(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        if self._file.exists():
            raw = json.loads(self._file.read_text())
            for item in raw:
                dest = Destination(**item)
                self._destinations[dest.id] = dest
            logger.info("[destinations] Loaded %d destinations", len(self._destinations))

    def _save(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        raw = [d.model_dump() for d in self._destinations.values()]
        self._file.write_text(json.dumps(raw, indent=2))

    def list_all(self) -> list[Destination]:
        return list(self._destinations.values())

    def get(self, dest_id: str) -> Destination | None:
        return self._destinations.get(dest_id)

    def create(self, data: CreateDestinationRequest) -> Destination:
        now = time.time()
        dest = Destination(
            id=uuid.uuid4().hex[:12],
            name=data.name,
            type=data.type,
            url=data.url,
            auth_header_name=data.auth_header_name,
            auth_header_value=data.auth_header_value,
            client_slug=data.client_slug,
            created_at=now,
            updated_at=now,
        )
        self._destinations[dest.id] = dest
        self._save()
        return dest

    def update(self, dest_id: str, data: UpdateDestinationRequest) -> Destination | None:
        dest = self._destinations.get(dest_id)
        if dest is None:
            return None
        updates = data.model_dump(exclude_none=True)
        if updates:
            updated = dest.model_copy(update={**updates, "updated_at": time.time()})
            self._destinations[dest_id] = updated
            self._save()
            return updated
        return dest

    def delete(self, dest_id: str) -> bool:
        if dest_id not in self._destinations:
            return False
        del self._destinations[dest_id]
        self._save()
        return True

    async def push(self, destination: Destination, jobs: list[Job]) -> PushResult:
        errors: list[dict] = []
        success = 0

        headers: dict[str, str] = {"Content-Type": "application/json"}
        if destination.auth_header_name and destination.auth_header_value:
            headers[destination.auth_header_name] = destination.auth_header_value

        async with httpx.AsyncClient(timeout=30) as client:
            for job in jobs:
                if job.status != JobStatus.completed or job.result is None:
                    continue

                payload = {**job.result}
                if job.row_id:
                    payload["row_id"] = job.row_id
                payload["_meta"] = {
                    "source": "clay-webhook-os",
                    "skill": job.skill,
                    "model": job.model,
                    "job_id": job.id,
                    "duration_ms": job.duration_ms,
                }

                try:
                    resp = await client.post(destination.url, json=payload, headers=headers)
                    resp.raise_for_status()
                    success += 1
                except Exception as e:
                    errors.append({"job_id": job.id, "error": str(e)})

                await asyncio.sleep(0.1)

        total = len([j for j in jobs if j.status == JobStatus.completed and j.result is not None])
        return PushResult(
            destination_id=destination.id,
            destination_name=destination.name,
            total=total,
            success=success,
            failed=len(errors),
            errors=errors,
        )

    async def test(self, destination: Destination) -> dict:
        headers: dict[str, str] = {"Content-Type": "application/json"}
        if destination.auth_header_name and destination.auth_header_value:
            headers[destination.auth_header_name] = destination.auth_header_value

        payload = {"_test": True, "source": "clay-webhook-os"}
        try:
            async with httpx.AsyncClient(timeout=10) as client:
                resp = await client.post(destination.url, json=payload, headers=headers)
                return {"ok": resp.status_code < 400, "status_code": resp.status_code}
        except Exception as e:
            return {"ok": False, "error": str(e)}
