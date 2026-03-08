import json
import time
from pathlib import Path

import pytest

from app.core.feedback_store import FeedbackStore
from app.models.feedback import FeedbackEntry, Rating


def _make_entry(
    job_id: str = "j1",
    skill: str = "email-gen",
    rating: str = "thumbs_up",
    client_slug: str | None = None,
    created_at: float | None = None,
) -> FeedbackEntry:
    return FeedbackEntry(
        job_id=job_id,
        skill=skill,
        rating=Rating(rating),
        client_slug=client_slug,
        created_at=created_at or time.time(),
    )


@pytest.fixture
def store(tmp_path: Path) -> FeedbackStore:
    s = FeedbackStore(data_dir=tmp_path)
    s.load()
    return s


# ---------------------------------------------------------------------------
# Load / persist
# ---------------------------------------------------------------------------


class TestLoadPersist:
    def test_load_creates_directory(self, tmp_path):
        s = FeedbackStore(data_dir=tmp_path)
        s.load()
        assert (tmp_path / "feedback").is_dir()

    def test_load_empty_dir(self, store):
        assert store.get_analytics().total_ratings == 0

    def test_load_existing_entries(self, tmp_path):
        fb_dir = tmp_path / "feedback"
        fb_dir.mkdir(parents=True)
        entry = _make_entry()
        (fb_dir / "entries.jsonl").write_text(
            json.dumps(entry.model_dump()) + "\n"
        )
        s = FeedbackStore(data_dir=tmp_path)
        s.load()
        assert s.get_analytics().total_ratings == 1

    def test_load_skips_blank_lines(self, tmp_path):
        fb_dir = tmp_path / "feedback"
        fb_dir.mkdir(parents=True)
        entry = _make_entry()
        content = json.dumps(entry.model_dump()) + "\n\n\n"
        (fb_dir / "entries.jsonl").write_text(content)
        s = FeedbackStore(data_dir=tmp_path)
        s.load()
        assert s.get_analytics().total_ratings == 1


# ---------------------------------------------------------------------------
# Submit
# ---------------------------------------------------------------------------


class TestSubmit:
    def test_submit_returns_entry(self, store):
        entry = _make_entry()
        result = store.submit(entry)
        assert result.id == entry.id

    def test_submit_persists_to_file(self, store, tmp_path):
        store.submit(_make_entry())
        entries_file = tmp_path / "feedback" / "entries.jsonl"
        assert entries_file.exists()
        lines = entries_file.read_text().strip().splitlines()
        assert len(lines) == 1

    def test_submit_updates_summary_file(self, store, tmp_path):
        store.submit(_make_entry())
        summary_file = tmp_path / "feedback" / "summary.json"
        assert summary_file.exists()
        summary = json.loads(summary_file.read_text())
        assert summary["total_ratings"] == 1

    def test_multiple_submits(self, store):
        store.submit(_make_entry(job_id="j1"))
        store.submit(_make_entry(job_id="j2"))
        assert store.get_analytics().total_ratings == 2


# ---------------------------------------------------------------------------
# Get entry / Get job feedback
# ---------------------------------------------------------------------------


class TestGetEntry:
    def test_get_entry_found(self, store):
        entry = _make_entry()
        store.submit(entry)
        found = store.get_entry(entry.id)
        assert found is not None
        assert found.id == entry.id

    def test_get_entry_not_found(self, store):
        assert store.get_entry("nonexistent") is None

    def test_get_job_feedback(self, store):
        store.submit(_make_entry(job_id="j1"))
        store.submit(_make_entry(job_id="j1", rating="thumbs_down"))
        store.submit(_make_entry(job_id="j2"))
        results = store.get_job_feedback("j1")
        assert len(results) == 2
        assert all(e.job_id == "j1" for e in results)

    def test_get_job_feedback_empty(self, store):
        assert store.get_job_feedback("nope") == []


# ---------------------------------------------------------------------------
# Delete
# ---------------------------------------------------------------------------


class TestDelete:
    def test_delete_existing(self, store):
        entry = _make_entry()
        store.submit(entry)
        assert store.delete(entry.id) is True
        assert store.get_entry(entry.id) is None
        assert store.get_analytics().total_ratings == 0

    def test_delete_nonexistent(self, store):
        assert store.delete("nope") is False

    def test_delete_rewrites_file(self, store, tmp_path):
        e1 = _make_entry(job_id="j1")
        e2 = _make_entry(job_id="j2")
        store.submit(e1)
        store.submit(e2)
        store.delete(e1.id)
        entries_file = tmp_path / "feedback" / "entries.jsonl"
        lines = entries_file.read_text().strip().splitlines()
        assert len(lines) == 1


# ---------------------------------------------------------------------------
# Compact
# ---------------------------------------------------------------------------


class TestCompact:
    def test_compact_removes_old_entries(self, store):
        old = _make_entry(job_id="old", created_at=time.time() - 1000)
        new = _make_entry(job_id="new", created_at=time.time())
        store.submit(old)
        store.submit(new)
        removed = store.compact(cutoff=time.time() - 500)
        assert removed == 1
        assert store.get_analytics().total_ratings == 1

    def test_compact_nothing_to_remove(self, store):
        store.submit(_make_entry(created_at=time.time()))
        removed = store.compact(cutoff=time.time() - 500)
        assert removed == 0

    def test_compact_removes_all(self, store):
        store.submit(_make_entry(created_at=time.time() - 1000))
        store.submit(_make_entry(created_at=time.time() - 900))
        removed = store.compact(cutoff=time.time())
        assert removed == 2
        assert store.get_analytics().total_ratings == 0


# ---------------------------------------------------------------------------
# Analytics
# ---------------------------------------------------------------------------


class TestAnalytics:
    def test_empty_analytics(self, store):
        a = store.get_analytics()
        assert a.total_ratings == 0
        assert a.overall_approval_rate == 0.0
        assert a.by_skill == []
        assert a.by_client == {}

    def test_approval_rate(self, store):
        store.submit(_make_entry(rating="thumbs_up"))
        store.submit(_make_entry(rating="thumbs_up"))
        store.submit(_make_entry(rating="thumbs_down"))
        a = store.get_analytics()
        assert a.total_ratings == 3
        assert a.overall_approval_rate == pytest.approx(0.667, abs=0.001)

    def test_by_skill_breakdown(self, store):
        store.submit(_make_entry(skill="a", rating="thumbs_up"))
        store.submit(_make_entry(skill="a", rating="thumbs_down"))
        store.submit(_make_entry(skill="b", rating="thumbs_up"))
        a = store.get_analytics()
        assert len(a.by_skill) == 2
        skill_a = next(s for s in a.by_skill if s.skill == "a")
        assert skill_a.total == 2
        assert skill_a.thumbs_up == 1
        assert skill_a.thumbs_down == 1
        assert skill_a.approval_rate == 0.5

    def test_by_client_breakdown(self, store):
        store.submit(_make_entry(client_slug="acme", rating="thumbs_up"))
        store.submit(_make_entry(client_slug="acme", rating="thumbs_down"))
        store.submit(_make_entry(client_slug="beta", rating="thumbs_up"))
        store.submit(_make_entry(client_slug=None, rating="thumbs_up"))  # no client
        a = store.get_analytics()
        assert "acme" in a.by_client
        assert a.by_client["acme"]["total"] == 2
        assert a.by_client["acme"]["thumbs_up"] == 1
        assert "beta" in a.by_client
        # None client not in by_client
        assert len(a.by_client) == 2

    def test_filter_by_skill(self, store):
        store.submit(_make_entry(skill="a"))
        store.submit(_make_entry(skill="b"))
        a = store.get_analytics(skill="a")
        assert a.total_ratings == 1

    def test_filter_by_client(self, store):
        store.submit(_make_entry(client_slug="acme"))
        store.submit(_make_entry(client_slug="beta"))
        a = store.get_analytics(client_slug="acme")
        assert a.total_ratings == 1

    def test_filter_by_days(self, store):
        store.submit(_make_entry(created_at=time.time() - 86400 * 10))  # 10 days ago
        store.submit(_make_entry(created_at=time.time()))  # now
        a = store.get_analytics(days=5)
        assert a.total_ratings == 1

    def test_combined_filters(self, store):
        store.submit(_make_entry(skill="a", client_slug="acme", created_at=time.time()))
        store.submit(_make_entry(skill="a", client_slug="beta", created_at=time.time()))
        store.submit(_make_entry(skill="b", client_slug="acme", created_at=time.time()))
        a = store.get_analytics(skill="a", client_slug="acme")
        assert a.total_ratings == 1
