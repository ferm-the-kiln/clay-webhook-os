import hashlib
import json
import time


class ResultCache:
    def __init__(self, ttl: int = 3600):
        self._store: dict[str, tuple[float, dict]] = {}
        self._ttl = ttl

    @property
    def size(self) -> int:
        return len(self._store)

    def _key(self, skill: str, data: dict, instructions: str | None) -> str:
        payload = json.dumps({"skill": skill, "data": data, "instructions": instructions}, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, skill: str, data: dict, instructions: str | None = None) -> dict | None:
        if self._ttl <= 0:
            return None
        key = self._key(skill, data, instructions)
        entry = self._store.get(key)
        if entry is None:
            return None
        ts, result = entry
        if time.time() - ts > self._ttl:
            del self._store[key]
            return None
        return result

    def put(self, skill: str, data: dict, instructions: str | None, result: dict) -> None:
        if self._ttl <= 0:
            return
        key = self._key(skill, data, instructions)
        self._store[key] = (time.time(), result)

    def clear(self) -> None:
        self._store.clear()

    def evict_expired(self) -> int:
        now = time.time()
        expired = [k for k, (ts, _) in self._store.items() if now - ts > self._ttl]
        for k in expired:
            del self._store[k]
        return len(expired)
