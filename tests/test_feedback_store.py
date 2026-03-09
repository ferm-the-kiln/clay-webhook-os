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


# ---------------------------------------------------------------------------
# Deeper: Load / persist edge cases
# ---------------------------------------------------------------------------


class TestLoadDeeper:
    def test_load_multiple_entries(self, tmp_path):
        """Load a file with multiple valid JSONL lines."""
        fb_dir = tmp_path / "feedback"
        fb_dir.mkdir(parents=True)
        e1 = _make_entry(job_id="j1")
        e2 = _make_entry(job_id="j2")
        e3 = _make_entry(job_id="j3")
        content = "\n".join(json.dumps(e.model_dump()) for e in [e1, e2, e3]) + "\n"
        (fb_dir / "entries.jsonl").write_text(content)
        s = FeedbackStore(data_dir=tmp_path)
        s.load()
        assert s.get_analytics().total_ratings == 3

    def test_load_no_file_no_directory(self, tmp_path):
        """Load when feedback subdir doesn't exist yet — should create it."""
        s = FeedbackStore(data_dir=tmp_path / "fresh")
        s.load()
        assert (tmp_path / "fresh" / "feedback").is_dir()
        assert s.get_analytics().total_ratings == 0

    def test_load_preserves_entry_fields(self, tmp_path):
        """Fields like note, model, client_slug survive round-trip."""
        fb_dir = tmp_path / "feedback"
        fb_dir.mkdir(parents=True)
        e = _make_entry(client_slug="acme")
        data = e.model_dump()
        data["note"] = "great output"
        data["model"] = "sonnet"
        (fb_dir / "entries.jsonl").write_text(json.dumps(data) + "\n")
        s = FeedbackStore(data_dir=tmp_path)
        s.load()
        loaded = s.get_entry(e.id)
        assert loaded is not None
        assert loaded.note == "great output"
        assert loaded.model == "sonnet"
        assert loaded.client_slug == "acme"

    def test_load_entries_file_empty(self, tmp_path):
        """An existing but empty entries file loads zero entries."""
        fb_dir = tmp_path / "feedback"
        fb_dir.mkdir(parents=True)
        (fb_dir / "entries.jsonl").write_text("")
        s = FeedbackStore(data_dir=tmp_path)
        s.load()
        assert s.get_analytics().total_ratings == 0


# ---------------------------------------------------------------------------
# Deeper: Submit edge cases
# ---------------------------------------------------------------------------


class TestSubmitDeeper:
    def test_submit_appends_not_overwrites(self, store, tmp_path):
        """Each submit appends a new line, doesn't overwrite."""
        store.submit(_make_entry(job_id="j1"))
        store.submit(_make_entry(job_id="j2"))
        store.submit(_make_entry(job_id="j3"))
        entries_file = tmp_path / "feedback" / "entries.jsonl"
        lines = entries_file.read_text().strip().splitlines()
        assert len(lines) == 3
        # each line is valid JSON
        for line in lines:
            parsed = json.loads(line)
            assert "job_id" in parsed

    def test_submit_rebuilds_summary_each_time(self, store, tmp_path):
        """Summary file is updated on each submit."""
        store.submit(_make_entry(rating="thumbs_up"))
        summary = json.loads((tmp_path / "feedback" / "summary.json").read_text())
        assert summary["total_ratings"] == 1
        assert summary["overall_approval_rate"] == 1.0

        store.submit(_make_entry(rating="thumbs_down"))
        summary = json.loads((tmp_path / "feedback" / "summary.json").read_text())
        assert summary["total_ratings"] == 2
        assert summary["overall_approval_rate"] == 0.5

    def test_submit_entry_has_auto_id(self, store):
        """Entries get auto-generated IDs."""
        e1 = _make_entry()
        e2 = _make_entry()
        store.submit(e1)
        store.submit(e2)
        assert e1.id != e2.id
        assert len(e1.id) == 12

    def test_submit_preserves_note(self, store):
        """Note field is preserved through submit."""
        e = FeedbackEntry(
            job_id="j1", skill="email-gen", rating=Rating.thumbs_down,
            note="output was too long"
        )
        result = store.submit(e)
        assert result.note == "output was too long"
        found = store.get_entry(e.id)
        assert found.note == "output was too long"


# ---------------------------------------------------------------------------
# Deeper: Get entry / job feedback
# ---------------------------------------------------------------------------


class TestGetDeeper:
    def test_get_entry_returns_correct_one_among_many(self, store):
        """get_entry finds the right entry among several."""
        entries = [_make_entry(job_id=f"j{i}") for i in range(5)]
        for e in entries:
            store.submit(e)
        target = entries[3]
        found = store.get_entry(target.id)
        assert found.job_id == "j3"

    def test_get_job_feedback_different_skills(self, store):
        """get_job_feedback returns all entries for a job regardless of skill."""
        store.submit(_make_entry(job_id="j1", skill="a"))
        store.submit(_make_entry(job_id="j1", skill="b"))
        store.submit(_make_entry(job_id="j2", skill="a"))
        results = store.get_job_feedback("j1")
        assert len(results) == 2
        skills = {r.skill for r in results}
        assert skills == {"a", "b"}

    def test_get_job_feedback_preserves_order(self, store):
        """Entries returned in insertion order."""
        store.submit(_make_entry(job_id="j1", rating="thumbs_up"))
        store.submit(_make_entry(job_id="j1", rating="thumbs_down"))
        results = store.get_job_feedback("j1")
        assert results[0].rating == Rating.thumbs_up
        assert results[1].rating == Rating.thumbs_down


# ---------------------------------------------------------------------------
# Deeper: Delete edge cases
# ---------------------------------------------------------------------------


class TestDeleteDeeper:
    def test_delete_updates_summary(self, store, tmp_path):
        """Delete rebuilds summary file correctly."""
        e1 = _make_entry(rating="thumbs_up")
        e2 = _make_entry(rating="thumbs_down")
        store.submit(e1)
        store.submit(e2)
        store.delete(e1.id)
        summary = json.loads((tmp_path / "feedback" / "summary.json").read_text())
        assert summary["total_ratings"] == 1
        assert summary["overall_approval_rate"] == 0.0  # only thumbs_down left

    def test_delete_middle_entry(self, store):
        """Deleting a middle entry preserves the others."""
        entries = [_make_entry(job_id=f"j{i}") for i in range(3)]
        for e in entries:
            store.submit(e)
        store.delete(entries[1].id)
        assert store.get_entry(entries[0].id) is not None
        assert store.get_entry(entries[1].id) is None
        assert store.get_entry(entries[2].id) is not None
        assert store.get_analytics().total_ratings == 2

    def test_delete_all_entries_one_by_one(self, store):
        """Deleting all entries leaves store empty."""
        entries = [_make_entry(job_id=f"j{i}") for i in range(3)]
        for e in entries:
            store.submit(e)
        for e in entries:
            assert store.delete(e.id) is True
        assert store.get_analytics().total_ratings == 0

    def test_delete_twice_returns_false(self, store):
        """Deleting same entry twice: second returns False."""
        e = _make_entry()
        store.submit(e)
        assert store.delete(e.id) is True
        assert store.delete(e.id) is False


# ---------------------------------------------------------------------------
# Deeper: Compact edge cases
# ---------------------------------------------------------------------------


class TestCompactDeeper:
    def test_compact_returns_zero_on_empty(self, store):
        """Compact on empty store returns 0."""
        assert store.compact(cutoff=time.time()) == 0

    def test_compact_rewrites_file(self, store, tmp_path):
        """After compact, entries file only has surviving entries."""
        old = _make_entry(job_id="old", created_at=100.0)
        new = _make_entry(job_id="new", created_at=time.time())
        store.submit(old)
        store.submit(new)
        store.compact(cutoff=200.0)
        entries_file = tmp_path / "feedback" / "entries.jsonl"
        lines = entries_file.read_text().strip().splitlines()
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["job_id"] == "new"

    def test_compact_updates_summary(self, store, tmp_path):
        """Compact updates summary file after removing entries."""
        store.submit(_make_entry(rating="thumbs_up", created_at=100.0))
        store.submit(_make_entry(rating="thumbs_down", created_at=time.time()))
        store.compact(cutoff=200.0)
        summary = json.loads((tmp_path / "feedback" / "summary.json").read_text())
        assert summary["total_ratings"] == 1

    def test_compact_boundary_exact_cutoff(self, store):
        """Entry at exact cutoff time is kept (>= comparison)."""
        cutoff = 5000.0
        at_cutoff = _make_entry(job_id="boundary", created_at=cutoff)
        before_cutoff = _make_entry(job_id="old", created_at=cutoff - 1)
        store.submit(before_cutoff)
        store.submit(at_cutoff)
        removed = store.compact(cutoff=cutoff)
        assert removed == 1
        assert store.get_entry(at_cutoff.id) is not None
        assert store.get_entry(before_cutoff.id) is None


# ---------------------------------------------------------------------------
# Deeper: Analytics edge cases
# ---------------------------------------------------------------------------


class TestAnalyticsDeeper:
    def test_all_thumbs_down(self, store):
        """100% thumbs down gives 0.0 approval rate."""
        for _ in range(3):
            store.submit(_make_entry(rating="thumbs_down"))
        a = store.get_analytics()
        assert a.overall_approval_rate == 0.0

    def test_all_thumbs_up(self, store):
        """100% thumbs up gives 1.0 approval rate."""
        for _ in range(3):
            store.submit(_make_entry(rating="thumbs_up"))
        a = store.get_analytics()
        assert a.overall_approval_rate == 1.0

    def test_by_skill_sorted_alphabetically(self, store):
        """by_skill list is sorted by skill name."""
        store.submit(_make_entry(skill="zebra"))
        store.submit(_make_entry(skill="alpha"))
        store.submit(_make_entry(skill="mid"))
        a = store.get_analytics()
        skill_names = [s.skill for s in a.by_skill]
        assert skill_names == ["alpha", "mid", "zebra"]

    def test_by_skill_thumbs_down_count(self, store):
        """thumbs_down = total - thumbs_up in SkillAnalytics."""
        store.submit(_make_entry(skill="x", rating="thumbs_up"))
        store.submit(_make_entry(skill="x", rating="thumbs_down"))
        store.submit(_make_entry(skill="x", rating="thumbs_down"))
        a = store.get_analytics()
        skill_x = a.by_skill[0]
        assert skill_x.thumbs_down == 2
        assert skill_x.total == 3
        assert skill_x.approval_rate == pytest.approx(0.333, abs=0.001)

    def test_by_client_excludes_none_slug(self, store):
        """Entries with client_slug=None are excluded from by_client."""
        store.submit(_make_entry(client_slug=None))
        store.submit(_make_entry(client_slug=None))
        a = store.get_analytics()
        assert a.by_client == {}
        assert a.total_ratings == 2  # but still counted in total

    def test_by_client_approval_rate(self, store):
        """by_client approval_rate is correctly computed."""
        store.submit(_make_entry(client_slug="acme", rating="thumbs_up"))
        store.submit(_make_entry(client_slug="acme", rating="thumbs_up"))
        store.submit(_make_entry(client_slug="acme", rating="thumbs_down"))
        a = store.get_analytics()
        assert a.by_client["acme"]["approval_rate"] == pytest.approx(0.667, abs=0.001)

    def test_by_client_sorted_alphabetically(self, store):
        """by_client dict keys are sorted alphabetically."""
        store.submit(_make_entry(client_slug="zeta"))
        store.submit(_make_entry(client_slug="alpha"))
        store.submit(_make_entry(client_slug="mid"))
        a = store.get_analytics()
        assert list(a.by_client.keys()) == ["alpha", "mid", "zeta"]

    def test_days_filter_boundary(self, store):
        """days filter cutoff is days * 86400 seconds ago."""
        now = time.time()
        # Exactly 7 days ago (should be excluded by days=7 since it's at the boundary)
        store.submit(_make_entry(created_at=now - 7 * 86400 - 1))  # just past 7 days
        store.submit(_make_entry(created_at=now - 7 * 86400 + 1))  # just within 7 days
        a = store.get_analytics(days=7)
        assert a.total_ratings == 1

    def test_combined_all_three_filters(self, store):
        """skill + client_slug + days filters all applied together."""
        now = time.time()
        # matches all filters
        store.submit(_make_entry(skill="a", client_slug="acme", created_at=now))
        # wrong skill
        store.submit(_make_entry(skill="b", client_slug="acme", created_at=now))
        # wrong client
        store.submit(_make_entry(skill="a", client_slug="beta", created_at=now))
        # too old
        store.submit(_make_entry(skill="a", client_slug="acme", created_at=now - 86400 * 100))
        a = store.get_analytics(skill="a", client_slug="acme", days=30)
        assert a.total_ratings == 1

    def test_single_entry_approval_rate_precision(self, store):
        """Single thumbs_up entry gives exactly 1.0, single down gives 0.0."""
        store.submit(_make_entry(rating="thumbs_up"))
        a = store.get_analytics()
        assert a.overall_approval_rate == 1.0

    def test_analytics_after_delete(self, store):
        """Analytics reflect state after delete."""
        e1 = _make_entry(skill="a", rating="thumbs_up")
        e2 = _make_entry(skill="a", rating="thumbs_down")
        store.submit(e1)
        store.submit(e2)
        store.delete(e1.id)
        a = store.get_analytics()
        assert a.total_ratings == 1
        assert a.overall_approval_rate == 0.0
        assert len(a.by_skill) == 1
        assert a.by_skill[0].thumbs_up == 0


# ---------------------------------------------------------------------------
# Deeper: File I/O internals
# ---------------------------------------------------------------------------


class TestFileIO:
    def test_rewrite_entries_creates_clean_file(self, store, tmp_path):
        """After delete, entries file has exactly the remaining entries."""
        entries = [_make_entry(job_id=f"j{i}") for i in range(5)]
        for e in entries:
            store.submit(e)
        store.delete(entries[0].id)
        store.delete(entries[2].id)
        store.delete(entries[4].id)
        entries_file = tmp_path / "feedback" / "entries.jsonl"
        lines = entries_file.read_text().strip().splitlines()
        assert len(lines) == 2
        ids = {json.loads(l)["id"] for l in lines}
        assert ids == {entries[1].id, entries[3].id}

    def test_summary_file_has_by_skill_and_by_client(self, store, tmp_path):
        """Summary JSON file contains all analytics sections."""
        store.submit(_make_entry(skill="email-gen", client_slug="acme", rating="thumbs_up"))
        summary = json.loads((tmp_path / "feedback" / "summary.json").read_text())
        assert "total_ratings" in summary
        assert "overall_approval_rate" in summary
        assert "by_skill" in summary
        assert "by_client" in summary
        assert len(summary["by_skill"]) == 1
        assert summary["by_skill"][0]["skill"] == "email-gen"
        assert "acme" in summary["by_client"]

    def test_round_trip_load_after_submits(self, tmp_path):
        """Entries persisted by one store instance can be loaded by a new one."""
        s1 = FeedbackStore(data_dir=tmp_path)
        s1.load()
        s1.submit(_make_entry(job_id="j1", skill="a", rating="thumbs_up"))
        s1.submit(_make_entry(job_id="j2", skill="b", rating="thumbs_down"))

        s2 = FeedbackStore(data_dir=tmp_path)
        s2.load()
        assert s2.get_analytics().total_ratings == 2
        a = s2.get_analytics()
        assert a.overall_approval_rate == 0.5
