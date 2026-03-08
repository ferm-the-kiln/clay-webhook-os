"""Phase 2: Agent Memory Store — persistent per-entity memory across requests.

Stores skill outputs keyed by entity (company domain, contact email).
When any skill processes an entity, prior findings are available as context.

Storage: data/memory/{entity_type}/{entity_id}.json
Pattern: Same as FeedbackStore — file-based, JSON persistence.
"""

import json
import logging
import re
import time
from pathlib import Path

logger = logging.getLogger("clay-webhook-os")

# TTL defaults (seconds)
DEFAULT_TTL = 604800  # 7 days
MAX_ENTRIES_PER_ENTITY = 50


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")


def _extract_entity_key(data: dict) -> tuple[str, str] | None:
    """Extract the primary entity identifier from request data.

    Returns (entity_type, entity_id) or None if no entity can be identified.
    """
    # Company-level keys (prefer domain)
    for key in ("company_domain", "domain", "website"):
        val = data.get(key)
        if val and isinstance(val, str):
            # Normalize domain: strip protocol, www, trailing slash
            domain = re.sub(r"^https?://", "", val).strip("/")
            domain = re.sub(r"^www\.", "", domain)
            return ("company", _slugify(domain))

    # Contact-level keys
    for key in ("email", "contact_email", "person_email"):
        val = data.get(key)
        if val and isinstance(val, str):
            return ("contact", _slugify(val))

    # Company name as fallback
    for key in ("company_name", "company"):
        val = data.get(key)
        if val and isinstance(val, str):
            return ("company", _slugify(val))

    return None


class MemoryEntry:
    __slots__ = ("skill", "timestamp", "summary", "key_fields", "ttl")

    def __init__(
        self,
        skill: str,
        timestamp: float,
        summary: str,
        key_fields: dict | None = None,
        ttl: int = DEFAULT_TTL,
    ):
        self.skill = skill
        self.timestamp = timestamp
        self.summary = summary
        self.key_fields = key_fields or {}
        self.ttl = ttl

    @property
    def is_expired(self) -> bool:
        return time.time() > (self.timestamp + self.ttl)

    def to_dict(self) -> dict:
        return {
            "skill": self.skill,
            "timestamp": self.timestamp,
            "summary": self.summary,
            "key_fields": self.key_fields,
            "ttl": self.ttl,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "MemoryEntry":
        return cls(
            skill=d["skill"],
            timestamp=d["timestamp"],
            summary=d.get("summary", ""),
            key_fields=d.get("key_fields", {}),
            ttl=d.get("ttl", DEFAULT_TTL),
        )


class MemoryStore:
    def __init__(self, data_dir: Path):
        self._base_dir = data_dir / "memory"

    def load(self) -> None:
        self._base_dir.mkdir(parents=True, exist_ok=True)
        # Count existing entities
        count = 0
        for type_dir in self._base_dir.iterdir():
            if type_dir.is_dir():
                count += sum(1 for f in type_dir.iterdir() if f.suffix == ".json")
        logger.info("[memory] Loaded store (%d entities)", count)

    def _entity_path(self, entity_type: str, entity_id: str) -> Path:
        return self._base_dir / entity_type / f"{entity_id}.json"

    def store(
        self,
        entity_type: str,
        entity_id: str,
        skill: str,
        result: dict,
        ttl: int = DEFAULT_TTL,
    ) -> None:
        """Store a memory entry for an entity after a skill completes."""
        path = self._entity_path(entity_type, entity_id)
        path.parent.mkdir(parents=True, exist_ok=True)

        entries = self._load_entries(path)

        # Build summary from result — take top-level string/number fields
        summary_parts = []
        key_fields = {}
        for k, v in result.items():
            if k.startswith("_"):
                continue
            if isinstance(v, (str, int, float, bool)):
                key_fields[k] = v
                if isinstance(v, str) and len(v) > 200:
                    continue  # Skip long text in summary
                summary_parts.append(f"{k}: {v}")
            elif isinstance(v, list) and len(v) <= 5:
                key_fields[k] = v

        summary = "; ".join(summary_parts[:10])  # Cap summary length

        entry = MemoryEntry(
            skill=skill,
            timestamp=time.time(),
            summary=summary,
            key_fields=key_fields,
            ttl=ttl,
        )

        entries.append(entry)

        # Prune expired and cap entries
        entries = [e for e in entries if not e.is_expired]
        if len(entries) > MAX_ENTRIES_PER_ENTITY:
            entries = entries[-MAX_ENTRIES_PER_ENTITY:]

        self._save_entries(path, entries)
        logger.info(
            "[memory] Stored entry: %s/%s skill=%s (%d total entries)",
            entity_type, entity_id, skill, len(entries),
        )

    def store_from_data(self, data: dict, skill: str, result: dict, ttl: int = DEFAULT_TTL) -> None:
        """Auto-extract entity key from data and store memory."""
        key = _extract_entity_key(data)
        if key is None:
            return
        entity_type, entity_id = key
        self.store(entity_type, entity_id, skill, result, ttl)

    def query(self, data: dict) -> list[MemoryEntry]:
        """Query memory for entries matching the entity in the data."""
        key = _extract_entity_key(data)
        if key is None:
            return []
        entity_type, entity_id = key
        return self.get_entity(entity_type, entity_id)

    def get_entity(self, entity_type: str, entity_id: str) -> list[MemoryEntry]:
        """Get all non-expired memory entries for an entity."""
        path = self._entity_path(entity_type, entity_id)
        if not path.exists():
            return []
        entries = self._load_entries(path)
        active = [e for e in entries if not e.is_expired]
        return active

    def prune_expired(self) -> int:
        """Remove expired entries across all entities. Returns count removed."""
        removed = 0
        for type_dir in self._base_dir.iterdir():
            if not type_dir.is_dir():
                continue
            for entity_file in type_dir.iterdir():
                if entity_file.suffix != ".json":
                    continue
                entries = self._load_entries(entity_file)
                active = [e for e in entries if not e.is_expired]
                expired = len(entries) - len(active)
                if expired > 0:
                    removed += expired
                    if active:
                        self._save_entries(entity_file, active)
                    else:
                        entity_file.unlink()
        if removed:
            logger.info("[memory] Pruned %d expired entries", removed)
        return removed

    def format_for_prompt(self, entries: list[MemoryEntry]) -> str:
        """Format memory entries as a prompt section."""
        if not entries:
            return ""
        lines = [f"# Prior Knowledge ({len(entries)} entries)\n"]
        for entry in entries:
            age_hours = (time.time() - entry.timestamp) / 3600
            if age_hours < 1:
                age_str = f"{int(age_hours * 60)}m ago"
            elif age_hours < 24:
                age_str = f"{int(age_hours)}h ago"
            else:
                age_str = f"{int(age_hours / 24)}d ago"
            lines.append(f"- **{entry.skill}** ({age_str}): {entry.summary}")
        return "\n".join(lines)

    def _load_entries(self, path: Path) -> list[MemoryEntry]:
        if not path.exists():
            return []
        try:
            data = json.loads(path.read_text())
            return [MemoryEntry.from_dict(e) for e in data.get("entries", [])]
        except (json.JSONDecodeError, KeyError):
            return []

    def _save_entries(self, path: Path, entries: list[MemoryEntry]) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {"entries": [e.to_dict() for e in entries]}
        path.write_text(json.dumps(data, indent=2))
