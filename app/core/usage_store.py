import json
import logging
import time
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path

from app.models.usage import DailyUsage, UsageEntry, UsageError, UsageSummary

logger = logging.getLogger("clay-webhook-os")

# Retention: 90 days
RETENTION_DAYS = 90
MAX_IN_MEMORY_ENTRIES = 2000
MAX_IN_MEMORY_ERRORS = 500


class UsageStore:
    def __init__(self, data_dir: Path):
        self._data_dir = data_dir / "usage"
        self._entries_file = self._data_dir / "entries.jsonl"
        self._errors_file = self._data_dir / "errors.jsonl"
        self._entries: list[UsageEntry] = []
        self._errors: list[UsageError] = []

    def load(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        cutoff = time.time() - (RETENTION_DAYS * 86400)

        if self._entries_file.exists():
            kept = []
            for line in self._entries_file.read_text().strip().splitlines():
                if line.strip():
                    entry = UsageEntry(**json.loads(line))
                    if entry.timestamp >= cutoff:
                        kept.append(entry)
            # Cap to newest MAX_IN_MEMORY_ENTRIES
            if len(kept) > MAX_IN_MEMORY_ENTRIES:
                kept = kept[-MAX_IN_MEMORY_ENTRIES:]
            self._entries = kept
            logger.info("[usage] Loaded %d entries (cap=%d)", len(self._entries), MAX_IN_MEMORY_ENTRIES)

        if self._errors_file.exists():
            kept = []
            for line in self._errors_file.read_text().strip().splitlines():
                if line.strip():
                    err = UsageError(**json.loads(line))
                    if err.timestamp >= cutoff:
                        kept.append(err)
            # Cap to newest MAX_IN_MEMORY_ERRORS
            if len(kept) > MAX_IN_MEMORY_ERRORS:
                kept = kept[-MAX_IN_MEMORY_ERRORS:]
            self._errors = kept
            logger.info("[usage] Loaded %d error events (cap=%d)", len(self._errors), MAX_IN_MEMORY_ERRORS)

    def record(self, entry: UsageEntry) -> None:
        self._entries.append(entry)
        # Trim if over soft cap
        if len(self._entries) > int(MAX_IN_MEMORY_ENTRIES * 1.5):
            self._entries = self._entries[-MAX_IN_MEMORY_ENTRIES:]
        self._data_dir.mkdir(parents=True, exist_ok=True)
        with open(self._entries_file, "a") as f:
            f.write(json.dumps(entry.model_dump()) + "\n")

    def record_error(self, error_type: str, message: str) -> None:
        err = UsageError(error_type=error_type, message=message)
        self._errors.append(err)
        # Trim if over soft cap
        if len(self._errors) > int(MAX_IN_MEMORY_ERRORS * 1.5):
            self._errors = self._errors[-MAX_IN_MEMORY_ERRORS:]
        self._data_dir.mkdir(parents=True, exist_ok=True)
        with open(self._errors_file, "a") as f:
            f.write(json.dumps(err.model_dump()) + "\n")

    def compact(self, cutoff: float) -> tuple[int, int]:
        """Remove entries and errors older than cutoff. Returns (entries_removed, errors_removed)."""
        orig_entries = len(self._entries)
        orig_errors = len(self._errors)
        self._entries = [e for e in self._entries if e.timestamp >= cutoff]
        self._errors = [e for e in self._errors if e.timestamp >= cutoff]
        entries_removed = orig_entries - len(self._entries)
        errors_removed = orig_errors - len(self._errors)
        if entries_removed > 0 or errors_removed > 0:
            self._rewrite()
            logger.info("[usage] Compacted: removed %d entries, %d errors", entries_removed, errors_removed)
        return entries_removed, errors_removed

    def _rewrite(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        with open(self._entries_file, "w") as f:
            for e in self._entries:
                f.write(json.dumps(e.model_dump()) + "\n")
        with open(self._errors_file, "w") as f:
            for e in self._errors:
                f.write(json.dumps(e.model_dump()) + "\n")

    def get_summary(self) -> UsageSummary:
        now = time.time()
        today_key = time.strftime("%Y-%m-%d")
        week_ago = now - 7 * 86400
        month_ago = now - 30 * 86400

        today_entries = [e for e in self._entries if e.date_key == today_key]
        week_entries = [e for e in self._entries if e.timestamp >= week_ago]
        month_entries = [e for e in self._entries if e.timestamp >= month_ago]

        today_errors = [e for e in self._errors if e.date_key == today_key]
        week_errors = [e for e in self._errors if e.timestamp >= week_ago]
        month_errors = [e for e in self._errors if e.timestamp >= month_ago]

        today = self._aggregate(today_key, today_entries, len(today_errors))
        week = self._aggregate("week", week_entries, len(week_errors))
        month = self._aggregate("month", month_entries, len(month_errors))

        # Daily history (last 30 days)
        daily_history = self._build_daily_history(30)

        # Subscription health heuristic
        health = self._compute_health(now)

        # Last error
        last_error = self._errors[-1] if self._errors else None

        return UsageSummary(
            today=today,
            week=week,
            month=month,
            daily_history=daily_history,
            subscription_health=health,
            last_error=last_error,
        )

    def get_health(self) -> dict:
        now = time.time()
        today_key = time.strftime("%Y-%m-%d")
        today_entries = [e for e in self._entries if e.date_key == today_key]
        today_errors = [e for e in self._errors if e.date_key == today_key]
        health = self._compute_health(now)
        return {
            "status": health,
            "today_requests": len(today_entries),
            "today_tokens": sum(e.input_tokens + e.output_tokens for e in today_entries),
            "today_errors": len(today_errors),
            "last_error": self._errors[-1].model_dump() if self._errors else None,
        }

    def _compute_health(self, now: float) -> str:
        # Check for recent subscription limit errors
        sub_errors = [e for e in self._errors if e.error_type == "subscription_limit"]
        if sub_errors:
            last = sub_errors[-1]
            age = now - last.timestamp
            if age < 300:  # 5 minutes
                return "exhausted"
            if age < 3600:  # 1 hour
                return "critical"

        # Check if daily usage is unusually high (>2x 7-day average)
        today_key = time.strftime("%Y-%m-%d")
        today_tokens = sum(
            e.input_tokens + e.output_tokens
            for e in self._entries if e.date_key == today_key
        )
        week_ago = now - 7 * 86400
        week_entries = [e for e in self._entries if e.timestamp >= week_ago]
        if week_entries:
            daily_counts: dict[str, int] = defaultdict(int)
            for e in week_entries:
                daily_counts[e.date_key] += e.input_tokens + e.output_tokens
            past_days = [v for k, v in daily_counts.items() if k != today_key]
            if past_days:
                avg_daily = sum(past_days) / len(past_days)
                if avg_daily > 0 and today_tokens > avg_daily * 2:
                    return "warning"

        return "healthy"

    @staticmethod
    def _aggregate(date: str, entries: list[UsageEntry], error_count: int) -> DailyUsage:
        input_tokens = sum(e.input_tokens for e in entries)
        output_tokens = sum(e.output_tokens for e in entries)
        by_model: dict[str, int] = defaultdict(int)
        by_skill: dict[str, int] = defaultdict(int)
        for e in entries:
            total = e.input_tokens + e.output_tokens
            by_model[e.model] += total
            if e.skill:
                by_skill[e.skill] += total

        return DailyUsage(
            date=date,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            request_count=len(entries),
            errors=error_count,
            by_model=dict(by_model),
            by_skill=dict(by_skill),
        )

    def _build_daily_history(self, days: int) -> list[DailyUsage]:
        today = datetime.now()
        date_keys = [(today - timedelta(days=i)).strftime("%Y-%m-%d") for i in range(days)]
        date_keys.reverse()

        # Group entries by date
        by_date: dict[str, list[UsageEntry]] = defaultdict(list)
        for e in self._entries:
            if e.date_key in date_keys:
                by_date[e.date_key].append(e)

        # Group errors by date
        errors_by_date: dict[str, int] = defaultdict(int)
        for e in self._errors:
            if e.date_key in date_keys:
                errors_by_date[e.date_key] += 1

        return [
            self._aggregate(dk, by_date.get(dk, []), errors_by_date.get(dk, 0))
            for dk in date_keys
        ]
