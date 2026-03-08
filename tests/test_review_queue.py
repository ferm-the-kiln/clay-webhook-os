import json
import time
from pathlib import Path

import pytest

from app.core.review_queue import ReviewQueue
from app.models.campaigns import ReviewItem, ReviewStatus


def _make_item(
    job_id: str = "j1",
    skill: str = "email-gen",
    campaign_id: str | None = "c1",
    status: ReviewStatus = ReviewStatus.pending,
    created_at: float | None = None,
) -> ReviewItem:
    return ReviewItem(
        job_id=job_id,
        skill=skill,
        campaign_id=campaign_id,
        status=status,
        created_at=created_at or time.time(),
    )


@pytest.fixture
def queue(tmp_path: Path) -> ReviewQueue:
    q = ReviewQueue(data_dir=tmp_path)
    q.load()
    return q


# ---------------------------------------------------------------------------
# Load / persist
# ---------------------------------------------------------------------------


class TestLoadPersist:
    def test_load_creates_directory(self, tmp_path):
        q = ReviewQueue(data_dir=tmp_path)
        q.load()
        assert (tmp_path / "review").is_dir()

    def test_load_empty(self, queue):
        assert queue.list_items() == []

    def test_load_existing_items(self, tmp_path):
        review_dir = tmp_path / "review"
        review_dir.mkdir(parents=True)
        item = _make_item()
        (review_dir / "items.jsonl").write_text(json.dumps(item.model_dump()) + "\n")
        q = ReviewQueue(data_dir=tmp_path)
        q.load()
        assert len(q.list_items()) == 1

    def test_load_skips_blank_lines(self, tmp_path):
        review_dir = tmp_path / "review"
        review_dir.mkdir(parents=True)
        item = _make_item()
        (review_dir / "items.jsonl").write_text(json.dumps(item.model_dump()) + "\n\n\n")
        q = ReviewQueue(data_dir=tmp_path)
        q.load()
        assert len(q.list_items()) == 1


# ---------------------------------------------------------------------------
# Add / Get
# ---------------------------------------------------------------------------


class TestAddGet:
    def test_add_returns_item(self, queue):
        item = _make_item()
        result = queue.add(item)
        assert result.id == item.id

    def test_add_persists(self, queue, tmp_path):
        queue.add(_make_item())
        f = tmp_path / "review" / "items.jsonl"
        assert f.exists()
        assert len(f.read_text().strip().splitlines()) == 1

    def test_get_by_id(self, queue):
        item = _make_item()
        queue.add(item)
        found = queue.get(item.id)
        assert found is not None
        assert found.job_id == "j1"

    def test_get_nonexistent(self, queue):
        assert queue.get("nope") is None

    def test_get_by_job(self, queue):
        queue.add(_make_item(job_id="j42"))
        found = queue.get_by_job("j42")
        assert found is not None
        assert found.job_id == "j42"

    def test_get_by_job_not_found(self, queue):
        assert queue.get_by_job("nope") is None


# ---------------------------------------------------------------------------
# List / filter
# ---------------------------------------------------------------------------


class TestListItems:
    def test_list_all(self, queue):
        queue.add(_make_item(job_id="a"))
        queue.add(_make_item(job_id="b"))
        assert len(queue.list_items()) == 2

    def test_filter_by_status(self, queue):
        queue.add(_make_item(job_id="a", status=ReviewStatus.pending))
        queue.add(_make_item(job_id="b", status=ReviewStatus.approved))
        items = queue.list_items(status="pending")
        assert len(items) == 1
        assert items[0].job_id == "a"

    def test_filter_by_campaign(self, queue):
        queue.add(_make_item(job_id="a", campaign_id="c1"))
        queue.add(_make_item(job_id="b", campaign_id="c2"))
        items = queue.list_items(campaign_id="c1")
        assert len(items) == 1

    def test_filter_by_skill(self, queue):
        queue.add(_make_item(job_id="a", skill="email-gen"))
        queue.add(_make_item(job_id="b", skill="icp-scorer"))
        items = queue.list_items(skill="email-gen")
        assert len(items) == 1

    def test_limit(self, queue):
        for i in range(10):
            queue.add(_make_item(job_id=f"j{i}"))
        items = queue.list_items(limit=3)
        assert len(items) == 3

    def test_sorted_newest_first(self, queue):
        queue.add(_make_item(job_id="old", created_at=1000.0))
        queue.add(_make_item(job_id="new", created_at=2000.0))
        items = queue.list_items()
        assert items[0].job_id == "new"


# ---------------------------------------------------------------------------
# Approve / Reject / Revise
# ---------------------------------------------------------------------------


class TestApprove:
    def test_approve(self, queue):
        item = _make_item()
        queue.add(item)
        result = queue.approve(item.id, note="looks good")
        assert result is not None
        assert result.status == ReviewStatus.approved
        assert result.reviewer_note == "looks good"
        assert result.reviewed_at is not None

    def test_approve_nonexistent(self, queue):
        assert queue.approve("nope") is None

    def test_approve_persists(self, queue, tmp_path):
        item = _make_item()
        queue.add(item)
        queue.approve(item.id)
        lines = (tmp_path / "review" / "items.jsonl").read_text().strip().splitlines()
        data = json.loads(lines[0])
        assert data["status"] == "approved"


class TestReject:
    def test_reject(self, queue):
        item = _make_item()
        queue.add(item)
        result = queue.reject(item.id, note="off-brand")
        assert result.status == ReviewStatus.rejected
        assert result.reviewer_note == "off-brand"

    def test_reject_nonexistent(self, queue):
        assert queue.reject("nope") is None


class TestRevise:
    def test_revise(self, queue):
        item = _make_item()
        queue.add(item)
        result = queue.revise(item.id, note="redo", revision_job_id="j2")
        assert result.status == ReviewStatus.revised
        assert result.revision_job_id == "j2"

    def test_revise_nonexistent(self, queue):
        assert queue.revise("nope") is None


# ---------------------------------------------------------------------------
# Pending count
# ---------------------------------------------------------------------------


class TestPendingCount:
    def test_pending_count(self, queue):
        queue.add(_make_item(status=ReviewStatus.pending))
        queue.add(_make_item(status=ReviewStatus.approved))
        queue.add(_make_item(status=ReviewStatus.pending))
        assert queue.pending_count() == 2

    def test_pending_count_by_campaign(self, queue):
        queue.add(_make_item(campaign_id="c1", status=ReviewStatus.pending))
        queue.add(_make_item(campaign_id="c2", status=ReviewStatus.pending))
        assert queue.pending_count(campaign_id="c1") == 1


# ---------------------------------------------------------------------------
# Compact
# ---------------------------------------------------------------------------


class TestCompact:
    def test_compact_removes_old_resolved(self, queue):
        queue.add(_make_item(job_id="old", status=ReviewStatus.approved, created_at=time.time() - 1000))
        queue.add(_make_item(job_id="new", status=ReviewStatus.pending))
        removed = queue.compact(cutoff=time.time() - 500)
        assert removed == 1
        assert len(queue.list_items()) == 1

    def test_compact_keeps_pending(self, queue):
        queue.add(_make_item(status=ReviewStatus.pending, created_at=time.time() - 1000))
        removed = queue.compact(cutoff=time.time() - 500)
        assert removed == 0

    def test_compact_removes_rejected_and_revised(self, queue):
        queue.add(_make_item(job_id="rej", status=ReviewStatus.rejected, created_at=time.time() - 1000))
        queue.add(_make_item(job_id="rev", status=ReviewStatus.revised, created_at=time.time() - 1000))
        removed = queue.compact(cutoff=time.time() - 500)
        assert removed == 2

    def test_compact_nothing(self, queue):
        queue.add(_make_item(status=ReviewStatus.approved, created_at=time.time()))
        removed = queue.compact(cutoff=time.time() - 500)
        assert removed == 0


# ---------------------------------------------------------------------------
# Stats
# ---------------------------------------------------------------------------


class TestGetStats:
    def test_empty_stats(self, queue):
        stats = queue.get_stats()
        assert stats["total"] == 0
        assert stats["approval_rate"] == 0.0

    def test_stats_counts(self, queue):
        queue.add(_make_item(status=ReviewStatus.pending))
        queue.add(_make_item(status=ReviewStatus.approved))
        queue.add(_make_item(status=ReviewStatus.rejected))
        queue.add(_make_item(status=ReviewStatus.revised))
        stats = queue.get_stats()
        assert stats["total"] == 4
        assert stats["pending"] == 1
        assert stats["approved"] == 1
        assert stats["rejected"] == 1
        assert stats["revised"] == 1

    def test_approval_rate(self, queue):
        queue.add(_make_item(status=ReviewStatus.approved))
        queue.add(_make_item(status=ReviewStatus.approved))
        queue.add(_make_item(status=ReviewStatus.rejected))
        stats = queue.get_stats()
        assert stats["approval_rate"] == pytest.approx(0.667, abs=0.001)

    def test_stats_by_campaign(self, queue):
        queue.add(_make_item(campaign_id="c1", status=ReviewStatus.pending))
        queue.add(_make_item(campaign_id="c2", status=ReviewStatus.pending))
        stats = queue.get_stats(campaign_id="c1")
        assert stats["total"] == 1
