import hashlib
import json
import time


class ResultCache:
    def __init__(self, ttl: int = 3600):
        self._store: dict[str, tuple[float, dict]] = {}
        self._ttl = ttl
        self._hits: int = 0
        self._misses: int = 0

    @property
    def size(self) -> int:
        return len(self._store)

    @property
    def hits(self) -> int:
        return self._hits

    @property
    def misses(self) -> int:
        return self._misses

    @property
    def hit_rate(self) -> float:
        total = self._hits + self._misses
        return round(self._hits / total, 3) if total > 0 else 0.0

    def _key(self, skill: str, data: dict, instructions: str | None, model: str | None = None) -> str:
        key_data = {"skill": skill, "data": data, "instructions": instructions}
        if model:
            key_data["model"] = model
        payload = json.dumps(key_data, sort_keys=True)
        return hashlib.sha256(payload.encode()).hexdigest()

    def get(self, skill: str, data: dict, instructions: str | None = None, model: str | None = None) -> dict | None:
        if self._ttl <= 0:
            return None
        key = self._key(skill, data, instructions, model)
        entry = self._store.get(key)
        if entry is None:
            self._misses += 1
            return None
        ts, result = entry
        if time.time() - ts > self._ttl:
            del self._store[key]
            self._misses += 1
            return None
        self._hits += 1
        return result

    def put(self, skill: str, data: dict, instructions: str | None, result: dict, model: str | None = None) -> None:
        if self._ttl <= 0:
            return
        key = self._key(skill, data, instructions, model)
        self._store[key] = (time.time(), result)

    def clear(self) -> None:
        self._store.clear()

    def evict_expired(self) -> int:
        now = time.time()
        expired = [k for k, (ts, _) in self._store.items() if now - ts > self._ttl]
        for k in expired:
            del self._store[k]
        return len(expired)
