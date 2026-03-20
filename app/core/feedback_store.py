import json
import logging
import time
from pathlib import Path

from app.core.atomic_writer import atomic_write_json, atomic_write_text
from app.models.feedback import FeedbackEntry, FeedbackSummary, SkillAnalytics

logger = logging.getLogger("clay-webhook-os")

MAX_IN_MEMORY = 2000
RETENTION_DAYS = 90


class FeedbackStore:
    def __init__(self, data_dir: Path):
        self._data_dir = data_dir / "feedback"
        self._entries_file = self._data_dir / "entries.jsonl"
        self._summary_file = self._data_dir / "summary.json"
        self._entries: list[FeedbackEntry] = []

    def load(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        if self._entries_file.exists():
            cutoff = time.time() - (RETENTION_DAYS * 86400)
            kept = []
            for line in self._entries_file.read_text().strip().splitlines():
                if line.strip():
                    entry = FeedbackEntry(**json.loads(line))
                    if entry.created_at >= cutoff:
                        kept.append(entry)
            # Cap to newest MAX_IN_MEMORY entries
            if len(kept) > MAX_IN_MEMORY:
                kept = kept[-MAX_IN_MEMORY:]
            self._entries = kept
            logger.info("[feedback] Loaded %d entries (retention=%dd, cap=%d)", len(self._entries), RETENTION_DAYS, MAX_IN_MEMORY)

    def submit(self, entry: FeedbackEntry) -> FeedbackEntry:
        self._entries.append(entry)
        # Trim if over soft cap
        if len(self._entries) > MAX_IN_MEMORY + 100:
            self._entries = self._entries[-MAX_IN_MEMORY:]
        self._append_entry(entry)
        self._rebuild_summary()
        return entry

    def get_job_feedback(self, job_id: str) -> list[FeedbackEntry]:
        return [e for e in self._entries if e.job_id == job_id]

    def get_entry(self, feedback_id: str) -> FeedbackEntry | None:
        for e in self._entries:
            if e.id == feedback_id:
                return e
        return None

    def delete(self, feedback_id: str) -> bool:
        original_len = len(self._entries)
        self._entries = [e for e in self._entries if e.id != feedback_id]
        if len(self._entries) == original_len:
            return False
        self._rewrite_entries()
        self._rebuild_summary()
        return True

    def compact(self, cutoff: float) -> int:
        """Remove entries older than cutoff. Returns count removed."""
        orig = len(self._entries)
        self._entries = [e for e in self._entries if e.created_at >= cutoff]
        removed = orig - len(self._entries)
        if removed > 0:
            self._rewrite_entries()
            self._rebuild_summary()
            logger.info("[feedback] Compacted: removed %d entries", removed)
        return removed

    def get_analytics(
        self,
        skill: str | None = None,
        client_slug: str | None = None,
        days: int | None = None,
    ) -> FeedbackSummary:
        entries = self._entries

        if days is not None:
            cutoff = time.time() - (days * 86400)
            entries = [e for e in entries if e.created_at >= cutoff]
        if skill is not None:
            entries = [e for e in entries if e.skill == skill]
        if client_slug is not None:
            entries = [e for e in entries if e.client_slug == client_slug]

        total = len(entries)
        up = sum(1 for e in entries if e.rating == "thumbs_up")
        overall_rate = round(up / total, 3) if total > 0 else 0.0

        # By skill
        skill_map: dict[str, dict] = {}
        for e in entries:
            s = skill_map.setdefault(e.skill, {"total": 0, "up": 0})
            s["total"] += 1
            if e.rating == "thumbs_up":
                s["up"] += 1

        by_skill = [
            SkillAnalytics(
                skill=sk,
                total=v["total"],
                thumbs_up=v["up"],
                thumbs_down=v["total"] - v["up"],
                approval_rate=round(v["up"] / v["total"], 3) if v["total"] > 0 else 0.0,
            )
            for sk, v in sorted(skill_map.items())
        ]

        # By client
        client_map: dict[str, dict] = {}
        for e in entries:
            if e.client_slug:
                c = client_map.setdefault(e.client_slug, {"total": 0, "thumbs_up": 0})
                c["total"] += 1
                if e.rating == "thumbs_up":
                    c["thumbs_up"] += 1
        by_client = {}
        for slug, v in sorted(client_map.items()):
            by_client[slug] = {
                "total": v["total"],
                "thumbs_up": v["thumbs_up"],
                "approval_rate": round(v["thumbs_up"] / v["total"], 3) if v["total"] > 0 else 0.0,
            }

        return FeedbackSummary(
            total_ratings=total,
            overall_approval_rate=overall_rate,
            by_skill=by_skill,
            by_client=by_client,
        )

    def _append_entry(self, entry: FeedbackEntry) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        with open(self._entries_file, "a") as f:
            f.write(json.dumps(entry.model_dump()) + "\n")

    def _rewrite_entries(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        content = "".join(json.dumps(e.model_dump()) + "\n" for e in self._entries)
        atomic_write_text(self._entries_file, content)

    def _rebuild_summary(self) -> None:
        summary = self.get_analytics()
        atomic_write_json(self._summary_file, summary.model_dump())
