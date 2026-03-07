import json
import logging
import time
from pathlib import Path

from app.models.campaigns import ReviewItem, ReviewStatus

logger = logging.getLogger("clay-webhook-os")


class ReviewQueue:
    def __init__(self, data_dir: Path):
        self._data_dir = data_dir / "review"
        self._file = self._data_dir / "items.jsonl"
        self._items: list[ReviewItem] = []

    def load(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        if self._file.exists():
            for line in self._file.read_text().strip().splitlines():
                if line.strip():
                    self._items.append(ReviewItem(**json.loads(line)))
            logger.info("[review] Loaded %d review items", len(self._items))

    def add(self, item: ReviewItem) -> ReviewItem:
        self._items.append(item)
        self._append(item)
        return item

    def get(self, item_id: str) -> ReviewItem | None:
        for item in self._items:
            if item.id == item_id:
                return item
        return None

    def get_by_job(self, job_id: str) -> ReviewItem | None:
        for item in self._items:
            if item.job_id == job_id:
                return item
        return None

    def list_items(
        self,
        status: str | None = None,
        campaign_id: str | None = None,
        skill: str | None = None,
        limit: int = 50,
    ) -> list[ReviewItem]:
        items = self._items
        if status:
            items = [i for i in items if i.status == status]
        if campaign_id:
            items = [i for i in items if i.campaign_id == campaign_id]
        if skill:
            items = [i for i in items if i.skill == skill]
        return sorted(items, key=lambda i: i.created_at, reverse=True)[:limit]

    def pending_count(self, campaign_id: str | None = None) -> int:
        items = self._items
        if campaign_id:
            items = [i for i in items if i.campaign_id == campaign_id]
        return sum(1 for i in items if i.status == ReviewStatus.pending)

    def approve(self, item_id: str, note: str = "") -> ReviewItem | None:
        item = self.get(item_id)
        if item is None:
            return None
        item.status = ReviewStatus.approved
        item.reviewer_note = note
        item.reviewed_at = time.time()
        self._rewrite()
        return item

    def reject(self, item_id: str, note: str = "") -> ReviewItem | None:
        item = self.get(item_id)
        if item is None:
            return None
        item.status = ReviewStatus.rejected
        item.reviewer_note = note
        item.reviewed_at = time.time()
        self._rewrite()
        return item

    def revise(self, item_id: str, note: str = "", revision_job_id: str | None = None) -> ReviewItem | None:
        item = self.get(item_id)
        if item is None:
            return None
        item.status = ReviewStatus.revised
        item.reviewer_note = note
        item.revision_job_id = revision_job_id
        item.reviewed_at = time.time()
        self._rewrite()
        return item

    def compact(self, cutoff: float) -> int:
        """Remove resolved (approved/rejected/revised) items older than cutoff."""
        resolved = {ReviewStatus.approved, ReviewStatus.rejected, ReviewStatus.revised}
        orig = len(self._items)
        self._items = [
            i for i in self._items
            if i.status not in resolved or i.created_at >= cutoff
        ]
        removed = orig - len(self._items)
        if removed > 0:
            self._rewrite()
            logger.info("[review] Compacted: removed %d resolved items", removed)
        return removed

    def get_stats(self, campaign_id: str | None = None) -> dict:
        items = self._items
        if campaign_id:
            items = [i for i in items if i.campaign_id == campaign_id]
        total = len(items)
        pending = sum(1 for i in items if i.status == ReviewStatus.pending)
        approved = sum(1 for i in items if i.status == ReviewStatus.approved)
        rejected = sum(1 for i in items if i.status == ReviewStatus.rejected)
        revised = sum(1 for i in items if i.status == ReviewStatus.revised)
        approval_rate = round(approved / (approved + rejected), 3) if (approved + rejected) > 0 else 0.0
        return {
            "total": total,
            "pending": pending,
            "approved": approved,
            "rejected": rejected,
            "revised": revised,
            "approval_rate": approval_rate,
        }

    def _append(self, item: ReviewItem) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        with open(self._file, "a") as f:
            f.write(json.dumps(item.model_dump()) + "\n")

    def _rewrite(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        with open(self._file, "w") as f:
            for item in self._items:
                f.write(json.dumps(item.model_dump()) + "\n")
