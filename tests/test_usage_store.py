import json
import time
from pathlib import Path

import pytest

from app.core.usage_store import UsageStore
from app.models.usage import UsageEntry, UsageError


def _make_entry(
    skill: str = "email-gen",
    model: str = "opus",
    input_tokens: int = 100,
    output_tokens: int = 50,
    timestamp: float | None = None,
    date_key: str | None = None,
) -> UsageEntry:
    ts = timestamp or time.time()
    dk = date_key or time.strftime("%Y-%m-%d", time.localtime(ts))
    return UsageEntry(
        skill=skill, model=model,
        input_tokens=input_tokens, output_tokens=output_tokens,
        timestamp=ts, date_key=dk,
    )


@pytest.fixture
def store(tmp_path: Path) -> UsageStore:
    s = UsageStore(data_dir=tmp_path)
    s.load()
    return s


# ---------------------------------------------------------------------------
# Load / persist
# ---------------------------------------------------------------------------


class TestLoadPersist:
    def test_load_creates_directory(self, tmp_path):
        s = UsageStore(data_dir=tmp_path)
        s.load()
        assert (tmp_path / "usage").is_dir()

    def test_load_empty(self, store):
        summary = store.get_summary()
        assert summary.today.request_count == 0

    def test_load_existing_entries(self, tmp_path):
        usage_dir = tmp_path / "usage"
        usage_dir.mkdir(parents=True)
        entry = _make_entry()
        (usage_dir / "entries.jsonl").write_text(json.dumps(entry.model_dump()) + "\n")
        (usage_dir / "errors.jsonl").write_text("")
        s = UsageStore(data_dir=tmp_path)
        s.load()
        assert len(s._entries) == 1

    def test_load_filters_old_entries(self, tmp_path):
        usage_dir = tmp_path / "usage"
        usage_dir.mkdir(parents=True)
        old = _make_entry(timestamp=time.time() - 91 * 86400)  # >90 days old
        new = _make_entry()
        content = json.dumps(old.model_dump()) + "\n" + json.dumps(new.model_dump()) + "\n"
        (usage_dir / "entries.jsonl").write_text(content)
        s = UsageStore(data_dir=tmp_path)
        s.load()
        assert len(s._entries) == 1

    def test_load_existing_errors(self, tmp_path):
        usage_dir = tmp_path / "usage"
        usage_dir.mkdir(parents=True)
        err = UsageError(error_type="timeout", message="slow")
        (usage_dir / "errors.jsonl").write_text(json.dumps(err.model_dump()) + "\n")
        (usage_dir / "entries.jsonl").write_text("")
        s = UsageStore(data_dir=tmp_path)
        s.load()
        assert len(s._errors) == 1
        assert s._errors[0].error_type == "timeout"

    def test_load_filters_old_errors(self, tmp_path):
        usage_dir = tmp_path / "usage"
        usage_dir.mkdir(parents=True)
        old_err = UsageError(error_type="old", message="old", timestamp=time.time() - 91 * 86400)
        new_err = UsageError(error_type="new", message="new")
        content = json.dumps(old_err.model_dump()) + "\n" + json.dumps(new_err.model_dump()) + "\n"
        (usage_dir / "errors.jsonl").write_text(content)
        s = UsageStore(data_dir=tmp_path)
        s.load()
        assert len(s._errors) == 1
        assert s._errors[0].error_type == "new"

    def test_load_handles_blank_lines(self, tmp_path):
        usage_dir = tmp_path / "usage"
        usage_dir.mkdir(parents=True)
        entry = _make_entry()
        content = json.dumps(entry.model_dump()) + "\n\n  \n" + json.dumps(entry.model_dump()) + "\n"
        (usage_dir / "entries.jsonl").write_text(content)
        s = UsageStore(data_dir=tmp_path)
        s.load()
        assert len(s._entries) == 2


# ---------------------------------------------------------------------------
# Record
# ---------------------------------------------------------------------------


class TestRecord:
    def test_record_appends_entry(self, store):
        store.record(_make_entry())
        assert len(store._entries) == 1

    def test_record_persists_to_file(self, store, tmp_path):
        store.record(_make_entry())
        f = tmp_path / "usage" / "entries.jsonl"
        assert f.exists()
        lines = f.read_text().strip().splitlines()
        assert len(lines) == 1

    def test_record_multiple(self, store):
        store.record(_make_entry(skill="a"))
        store.record(_make_entry(skill="b"))
        assert len(store._entries) == 2


class TestRecordError:
    def test_record_error(self, store):
        store.record_error("subscription_limit", "quota exceeded")
        assert len(store._errors) == 1
        assert store._errors[0].error_type == "subscription_limit"

    def test_record_error_persists(self, store, tmp_path):
        store.record_error("timeout", "timed out")
        f = tmp_path / "usage" / "errors.jsonl"
        assert f.exists()
        lines = f.read_text().strip().splitlines()
        assert len(lines) == 1


# ---------------------------------------------------------------------------
# Compact
# ---------------------------------------------------------------------------


class TestCompact:
    def test_compact_removes_old(self, store):
        store.record(_make_entry(timestamp=time.time() - 1000))
        store.record(_make_entry(timestamp=time.time()))
        entries_removed, errors_removed = store.compact(cutoff=time.time() - 500)
        assert entries_removed == 1
        assert errors_removed == 0
        assert len(store._entries) == 1

    def test_compact_removes_old_errors(self, store):
        store.record_error("e1", "old")
        store._errors[0].timestamp = time.time() - 1000
        store.record_error("e2", "new")
        _, errors_removed = store.compact(cutoff=time.time() - 500)
        assert errors_removed == 1

    def test_compact_nothing(self, store):
        store.record(_make_entry())
        e_rem, err_rem = store.compact(cutoff=time.time() - 500)
        assert e_rem == 0
        assert err_rem == 0

    def test_compact_rewrites_files(self, store, tmp_path):
        store.record(_make_entry(timestamp=time.time() - 1000))
        store.record(_make_entry())
        store.compact(cutoff=time.time() - 500)
        # Rewritten file should have only 1 entry
        f = tmp_path / "usage" / "entries.jsonl"
        lines = [l for l in f.read_text().strip().splitlines() if l.strip()]
        assert len(lines) == 1

    def test_compact_no_rewrite_when_nothing_removed(self, store, tmp_path):
        store.record(_make_entry())
        # Record an entry so file exists
        f = tmp_path / "usage" / "entries.jsonl"
        mtime_before = f.stat().st_mtime_ns
        import time as _time
        _time.sleep(0.01)
        store.compact(cutoff=time.time() - 500)
        # File should not be rewritten
        assert f.stat().st_mtime_ns == mtime_before


# ---------------------------------------------------------------------------
# Aggregate (static method)
# ---------------------------------------------------------------------------


class TestAggregate:
    def test_aggregate_empty(self):
        daily = UsageStore._aggregate("2026-03-08", [], 0)
        assert daily.request_count == 0
        assert daily.total_tokens == 0
        assert daily.errors == 0

    def test_aggregate_sums_tokens(self):
        entries = [
            _make_entry(input_tokens=100, output_tokens=50),
            _make_entry(input_tokens=200, output_tokens=100),
        ]
        daily = UsageStore._aggregate("2026-03-08", entries, 1)
        assert daily.input_tokens == 300
        assert daily.output_tokens == 150
        assert daily.total_tokens == 450
        assert daily.request_count == 2
        assert daily.errors == 1

    def test_aggregate_by_model(self):
        entries = [
            _make_entry(model="opus", input_tokens=100, output_tokens=50),
            _make_entry(model="haiku", input_tokens=200, output_tokens=100),
            _make_entry(model="opus", input_tokens=50, output_tokens=25),
        ]
        daily = UsageStore._aggregate("d", entries, 0)
        assert daily.by_model["opus"] == 225  # 150 + 75
        assert daily.by_model["haiku"] == 300

    def test_aggregate_by_skill(self):
        entries = [
            _make_entry(skill="email-gen", input_tokens=100, output_tokens=50),
            _make_entry(skill="icp-scorer", input_tokens=200, output_tokens=100),
        ]
        daily = UsageStore._aggregate("d", entries, 0)
        assert daily.by_skill["email-gen"] == 150
        assert daily.by_skill["icp-scorer"] == 300

    def test_aggregate_empty_skill_excluded(self):
        """Entries with empty string skill are not added to by_skill."""
        entries = [_make_entry(skill="", input_tokens=100, output_tokens=50)]
        daily = UsageStore._aggregate("d", entries, 0)
        assert "" not in daily.by_skill
        assert daily.request_count == 1


# ---------------------------------------------------------------------------
# Health computation
# ---------------------------------------------------------------------------


class TestComputeHealth:
    def test_healthy_default(self, store):
        assert store._compute_health(time.time()) == "healthy"

    def test_exhausted_recent_sub_error(self, store):
        store.record_error("subscription_limit", "quota")
        # Error just happened
        assert store._compute_health(time.time()) == "exhausted"

    def test_critical_sub_error_older_than_5min(self, store):
        store.record_error("subscription_limit", "quota")
        store._errors[0].timestamp = time.time() - 600  # 10 min ago
        assert store._compute_health(time.time()) == "critical"

    def test_healthy_sub_error_older_than_1h(self, store):
        store.record_error("subscription_limit", "quota")
        store._errors[0].timestamp = time.time() - 7200  # 2 hours ago
        assert store._compute_health(time.time()) == "healthy"

    def test_non_sub_errors_dont_affect_health(self, store):
        store.record_error("timeout", "timed out")
        assert store._compute_health(time.time()) == "healthy"

    def test_warning_high_daily_usage(self, store):
        """Daily usage > 2x weekly average triggers warning."""
        now = time.time()
        today_key = time.strftime("%Y-%m-%d")
        # Add moderate entries for past days
        for days_ago in range(1, 7):
            ts = now - days_ago * 86400
            dk = time.strftime("%Y-%m-%d", time.localtime(ts))
            store._entries.append(_make_entry(input_tokens=100, output_tokens=50, timestamp=ts, date_key=dk))
        # Add huge usage today (>2x average of 150 per day = >300)
        store._entries.append(_make_entry(input_tokens=500, output_tokens=500, timestamp=now, date_key=today_key))
        assert store._compute_health(now) == "warning"

    def test_no_warning_when_usage_within_normal(self, store):
        """Daily usage within 2x average stays healthy."""
        now = time.time()
        today_key = time.strftime("%Y-%m-%d")
        for days_ago in range(1, 7):
            ts = now - days_ago * 86400
            dk = time.strftime("%Y-%m-%d", time.localtime(ts))
            store._entries.append(_make_entry(input_tokens=100, output_tokens=50, timestamp=ts, date_key=dk))
        # Normal usage today (150 is within 2x of 150 avg)
        store._entries.append(_make_entry(input_tokens=100, output_tokens=50, timestamp=now, date_key=today_key))
        assert store._compute_health(now) == "healthy"


# ---------------------------------------------------------------------------
# get_summary
# ---------------------------------------------------------------------------


class TestGetSummary:
    def test_summary_structure(self, store):
        summary = store.get_summary()
        assert summary.today is not None
        assert summary.week is not None
        assert summary.month is not None
        assert isinstance(summary.daily_history, list)
        assert summary.subscription_health == "healthy"
        assert summary.last_error is None

    def test_summary_with_data(self, store):
        store.record(_make_entry())
        summary = store.get_summary()
        assert summary.today.request_count == 1

    def test_summary_last_error(self, store):
        store.record_error("timeout", "slow")
        summary = store.get_summary()
        assert summary.last_error is not None
        assert summary.last_error.error_type == "timeout"

    def test_daily_history_length(self, store):
        summary = store.get_summary()
        assert len(summary.daily_history) == 30

    def test_daily_history_includes_today(self, store):
        store.record(_make_entry(input_tokens=200, output_tokens=100))
        summary = store.get_summary()
        today_key = time.strftime("%Y-%m-%d")
        today_entry = [d for d in summary.daily_history if d.date == today_key]
        assert len(today_entry) == 1
        assert today_entry[0].request_count == 1
        assert today_entry[0].total_tokens == 300

    def test_summary_week_aggregation(self, store):
        now = time.time()
        # Entry from 3 days ago (within week window)
        ts = now - 3 * 86400
        dk = time.strftime("%Y-%m-%d", time.localtime(ts))
        store._entries.append(_make_entry(timestamp=ts, date_key=dk))
        # Entry from today
        store.record(_make_entry())
        summary = store.get_summary()
        assert summary.week.request_count == 2

    def test_summary_month_excludes_older(self, store):
        now = time.time()
        # Entry from 35 days ago (outside month window)
        ts = now - 35 * 86400
        dk = time.strftime("%Y-%m-%d", time.localtime(ts))
        store._entries.append(_make_entry(timestamp=ts, date_key=dk))
        # Entry from today
        store.record(_make_entry())
        summary = store.get_summary()
        assert summary.month.request_count == 1


# ---------------------------------------------------------------------------
# get_health
# ---------------------------------------------------------------------------


class TestGetHealth:
    def test_health_structure(self, store):
        h = store.get_health()
        assert "status" in h
        assert "today_requests" in h
        assert "today_tokens" in h
        assert "today_errors" in h
        assert h["status"] == "healthy"
        assert h["last_error"] is None

    def test_health_with_entries(self, store):
        store.record(_make_entry(input_tokens=500, output_tokens=200))
        h = store.get_health()
        assert h["today_requests"] == 1
        assert h["today_tokens"] == 700

    def test_health_with_errors(self, store):
        store.record_error("subscription_limit", "quota")
        h = store.get_health()
        assert h["today_errors"] == 1
        assert h["status"] == "exhausted"
        assert h["last_error"] is not None

    def test_health_last_error_structure(self, store):
        store.record_error("timeout", "slow response")
        h = store.get_health()
        err = h["last_error"]
        assert err["error_type"] == "timeout"
        assert err["message"] == "slow response"
        assert "timestamp" in err
        assert "date_key" in err
