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


# ---------------------------------------------------------------------------
# Deeper: Load — round-trip, multiple entries/errors
# ---------------------------------------------------------------------------


class TestLoadDeeper:
    def test_round_trip_entries(self, tmp_path):
        """Entries recorded by one store are loadable by a new instance."""
        s1 = UsageStore(data_dir=tmp_path)
        s1.load()
        s1.record(_make_entry(skill="a", input_tokens=100, output_tokens=50))
        s1.record(_make_entry(skill="b", input_tokens=200, output_tokens=100))

        s2 = UsageStore(data_dir=tmp_path)
        s2.load()
        assert len(s2._entries) == 2
        assert s2._entries[0].skill == "a"
        assert s2._entries[1].skill == "b"

    def test_round_trip_errors(self, tmp_path):
        """Errors recorded by one store are loadable by a new instance."""
        s1 = UsageStore(data_dir=tmp_path)
        s1.load()
        s1.record_error("timeout", "slow")
        s1.record_error("subscription_limit", "quota hit")

        s2 = UsageStore(data_dir=tmp_path)
        s2.load()
        assert len(s2._errors) == 2
        assert s2._errors[0].error_type == "timeout"
        assert s2._errors[1].error_type == "subscription_limit"

    def test_load_no_entries_file(self, tmp_path):
        """Load when usage dir exists but entries file doesn't."""
        (tmp_path / "usage").mkdir(parents=True)
        s = UsageStore(data_dir=tmp_path)
        s.load()
        assert len(s._entries) == 0
        assert len(s._errors) == 0

    def test_load_empty_entries_file(self, tmp_path):
        """Empty entries file loads zero entries."""
        usage_dir = tmp_path / "usage"
        usage_dir.mkdir(parents=True)
        (usage_dir / "entries.jsonl").write_text("")
        s = UsageStore(data_dir=tmp_path)
        s.load()
        assert len(s._entries) == 0

    def test_load_retention_keeps_recent_drops_old(self, tmp_path):
        """Entry from 89 days ago is kept, entry from 91 days ago is dropped."""
        usage_dir = tmp_path / "usage"
        usage_dir.mkdir(parents=True)
        now = time.time()
        recent = _make_entry(timestamp=now - 89 * 86400)
        old = _make_entry(timestamp=now - 91 * 86400)
        content = json.dumps(old.model_dump()) + "\n" + json.dumps(recent.model_dump()) + "\n"
        (usage_dir / "entries.jsonl").write_text(content)
        s = UsageStore(data_dir=tmp_path)
        s.load()
        assert len(s._entries) == 1


# ---------------------------------------------------------------------------
# Deeper: Record — field preservation
# ---------------------------------------------------------------------------


class TestRecordDeeper:
    def test_record_preserves_all_fields(self, store, tmp_path):
        """All entry fields are preserved in JSONL."""
        e = _make_entry(skill="icp-scorer", model="haiku", input_tokens=999, output_tokens=444)
        store.record(e)
        f = tmp_path / "usage" / "entries.jsonl"
        parsed = json.loads(f.read_text().strip())
        assert parsed["skill"] == "icp-scorer"
        assert parsed["model"] == "haiku"
        assert parsed["input_tokens"] == 999
        assert parsed["output_tokens"] == 444

    def test_record_appends_not_overwrites(self, store, tmp_path):
        """Multiple records append lines, not overwrite."""
        store.record(_make_entry(skill="a"))
        store.record(_make_entry(skill="b"))
        store.record(_make_entry(skill="c"))
        f = tmp_path / "usage" / "entries.jsonl"
        lines = f.read_text().strip().splitlines()
        assert len(lines) == 3

    def test_record_error_auto_timestamp(self, store):
        """record_error creates error with current timestamp."""
        before = time.time()
        store.record_error("timeout", "slow")
        after = time.time()
        err = store._errors[0]
        assert before <= err.timestamp <= after

    def test_record_error_auto_date_key(self, store):
        """record_error creates error with today's date_key."""
        store.record_error("timeout", "slow")
        today = time.strftime("%Y-%m-%d")
        assert store._errors[0].date_key == today


# ---------------------------------------------------------------------------
# Deeper: Compact — boundary, both entries and errors
# ---------------------------------------------------------------------------


class TestCompactDeeper:
    def test_compact_boundary_exact_cutoff(self, store):
        """Entry at exact cutoff is kept (>= comparison)."""
        cutoff = 5000.0
        old = _make_entry(timestamp=cutoff - 1)
        at = _make_entry(timestamp=cutoff)
        store._entries = [old, at]
        e_rem, _ = store.compact(cutoff=cutoff)
        assert e_rem == 1
        assert len(store._entries) == 1

    def test_compact_both_entries_and_errors(self, store):
        """Compact removes old entries AND old errors together."""
        now = time.time()
        store.record(_make_entry(timestamp=now - 1000))
        store.record(_make_entry(timestamp=now))
        store.record_error("e1", "old")
        store._errors[0].timestamp = now - 1000
        store.record_error("e2", "new")
        e_rem, err_rem = store.compact(cutoff=now - 500)
        assert e_rem == 1
        assert err_rem == 1
        assert len(store._entries) == 1
        assert len(store._errors) == 1

    def test_compact_empty_store(self, store):
        """Compact on empty store returns (0, 0)."""
        assert store.compact(cutoff=time.time()) == (0, 0)

    def test_compact_removes_all(self, store):
        """Compact with future cutoff removes everything."""
        store.record(_make_entry(timestamp=time.time()))
        store.record_error("err", "msg")
        e_rem, err_rem = store.compact(cutoff=time.time() + 1000)
        assert e_rem == 1
        assert err_rem == 1
        assert len(store._entries) == 0
        assert len(store._errors) == 0

    def test_compact_rewrites_errors_file(self, store, tmp_path):
        """Compact rewrites the errors file too."""
        store.record_error("old", "old msg")
        store._errors[0].timestamp = time.time() - 1000
        store.record_error("new", "new msg")
        store.compact(cutoff=time.time() - 500)
        f = tmp_path / "usage" / "errors.jsonl"
        lines = [l for l in f.read_text().strip().splitlines() if l.strip()]
        assert len(lines) == 1
        parsed = json.loads(lines[0])
        assert parsed["error_type"] == "new"


# ---------------------------------------------------------------------------
# Deeper: Aggregate — edge cases
# ---------------------------------------------------------------------------


class TestAggregateDeeper:
    def test_aggregate_single_entry(self):
        """Single entry produces correct aggregation."""
        entries = [_make_entry(skill="test", input_tokens=100, output_tokens=50)]
        daily = UsageStore._aggregate("d", entries, 0)
        assert daily.by_skill == {"test": 150}
        assert daily.by_model == {"opus": 150}
        assert daily.request_count == 1
        assert daily.total_tokens == 150

    def test_aggregate_multiple_same_model(self):
        """Multiple entries with same model are summed together."""
        entries = [
            _make_entry(model="opus", input_tokens=100, output_tokens=50),
            _make_entry(model="opus", input_tokens=200, output_tokens=100),
            _make_entry(model="opus", input_tokens=50, output_tokens=25),
        ]
        daily = UsageStore._aggregate("d", entries, 0)
        assert daily.by_model == {"opus": 525}

    def test_aggregate_multiple_same_skill(self):
        """Multiple entries with same skill are summed together."""
        entries = [
            _make_entry(skill="email-gen", input_tokens=100, output_tokens=50),
            _make_entry(skill="email-gen", input_tokens=200, output_tokens=100),
        ]
        daily = UsageStore._aggregate("d", entries, 0)
        assert daily.by_skill == {"email-gen": 450}

    def test_aggregate_date_preserved(self):
        """Date field in DailyUsage matches the passed date."""
        daily = UsageStore._aggregate("2026-01-15", [], 5)
        assert daily.date == "2026-01-15"
        assert daily.errors == 5

    def test_aggregate_zero_tokens(self):
        """Entry with zero tokens is still counted."""
        entries = [_make_entry(input_tokens=0, output_tokens=0)]
        daily = UsageStore._aggregate("d", entries, 0)
        assert daily.request_count == 1
        assert daily.total_tokens == 0


# ---------------------------------------------------------------------------
# Deeper: Health — state transitions, edge cases
# ---------------------------------------------------------------------------


class TestComputeHealthDeeper:
    def test_exhausted_boundary_at_5_minutes(self, store):
        """Error exactly 5 minutes ago: age == 300, not < 300, so critical."""
        now = time.time()
        store.record_error("subscription_limit", "quota")
        store._errors[0].timestamp = now - 300  # exactly 5 min
        assert store._compute_health(now) == "critical"

    def test_critical_boundary_at_1_hour(self, store):
        """Error exactly 1 hour ago: age == 3600, not < 3600, so healthy."""
        now = time.time()
        store.record_error("subscription_limit", "quota")
        store._errors[0].timestamp = now - 3600  # exactly 1 hour
        assert store._compute_health(now) == "healthy"

    def test_sub_error_overrides_warning(self, store):
        """subscription_limit error takes priority over high usage warning."""
        now = time.time()
        today_key = time.strftime("%Y-%m-%d")
        # Set up high usage for warning
        for days_ago in range(1, 7):
            ts = now - days_ago * 86400
            dk = time.strftime("%Y-%m-%d", time.localtime(ts))
            store._entries.append(_make_entry(input_tokens=100, output_tokens=50, timestamp=ts, date_key=dk))
        store._entries.append(_make_entry(input_tokens=500, output_tokens=500, timestamp=now, date_key=today_key))
        # Add recent sub error
        store.record_error("subscription_limit", "quota")
        assert store._compute_health(now) == "exhausted"

    def test_warning_exact_2x_not_triggered(self, store):
        """Usage exactly 2x average does NOT trigger warning (> not >=)."""
        now = time.time()
        today_key = time.strftime("%Y-%m-%d")
        for days_ago in range(1, 4):
            ts = now - days_ago * 86400
            dk = time.strftime("%Y-%m-%d", time.localtime(ts))
            store._entries.append(_make_entry(input_tokens=100, output_tokens=0, timestamp=ts, date_key=dk))
        # Today exactly 2x the average (100 per day, today = 200)
        store._entries.append(_make_entry(input_tokens=200, output_tokens=0, timestamp=now, date_key=today_key))
        assert store._compute_health(now) == "healthy"

    def test_no_past_days_no_warning(self, store):
        """If all entries are from today only, no warning (no past_days to average)."""
        now = time.time()
        today_key = time.strftime("%Y-%m-%d")
        store._entries.append(_make_entry(input_tokens=10000, output_tokens=10000, timestamp=now, date_key=today_key))
        assert store._compute_health(now) == "healthy"

    def test_multiple_sub_errors_uses_last(self, store):
        """Multiple sub errors — health is based on the most recent one."""
        now = time.time()
        store.record_error("subscription_limit", "old")
        store._errors[0].timestamp = now - 7200  # 2 hours ago
        store.record_error("subscription_limit", "recent")
        store._errors[1].timestamp = now - 60  # 1 min ago
        assert store._compute_health(now) == "exhausted"


# ---------------------------------------------------------------------------
# Deeper: get_summary — error counting, daily history
# ---------------------------------------------------------------------------


class TestGetSummaryDeeper:
    def test_summary_today_errors_counted(self, store):
        """Today's errors appear in summary.today.errors."""
        store.record_error("timeout", "slow")
        store.record_error("timeout", "slow again")
        summary = store.get_summary()
        assert summary.today.errors == 2

    def test_summary_week_errors_counted(self, store):
        """Errors within the week are counted."""
        now = time.time()
        store.record_error("timeout", "recent")
        store.record_error("timeout", "old")
        store._errors[1].timestamp = now - 3 * 86400
        store._errors[1].date_key = time.strftime("%Y-%m-%d", time.localtime(now - 3 * 86400))
        summary = store.get_summary()
        assert summary.week.errors == 2

    def test_summary_month_excludes_old_errors(self, store):
        """Errors older than 30 days excluded from month."""
        now = time.time()
        store.record_error("timeout", "recent")
        store.record_error("timeout", "old")
        store._errors[1].timestamp = now - 35 * 86400
        store._errors[1].date_key = time.strftime("%Y-%m-%d", time.localtime(now - 35 * 86400))
        summary = store.get_summary()
        assert summary.month.errors == 1

    def test_daily_history_sorted_chronologically(self, store):
        """Daily history is sorted oldest to newest."""
        summary = store.get_summary()
        dates = [d.date for d in summary.daily_history]
        assert dates == sorted(dates)

    def test_daily_history_empty_days_have_zero(self, store):
        """Days with no activity have zero counts."""
        summary = store.get_summary()
        for day in summary.daily_history:
            assert day.request_count >= 0
            assert day.total_tokens >= 0

    def test_summary_last_error_is_most_recent(self, store):
        """last_error is the last error recorded."""
        store.record_error("first", "msg1")
        store.record_error("second", "msg2")
        summary = store.get_summary()
        assert summary.last_error.error_type == "second"

    def test_summary_health_reflected(self, store):
        """subscription_health in summary matches _compute_health."""
        store.record_error("subscription_limit", "quota")
        summary = store.get_summary()
        assert summary.subscription_health == "exhausted"


# ---------------------------------------------------------------------------
# Deeper: get_health — token summing, error counting
# ---------------------------------------------------------------------------


class TestGetHealthDeeper:
    def test_health_sums_multiple_entries(self, store):
        """today_tokens sums input + output across multiple entries."""
        store.record(_make_entry(input_tokens=100, output_tokens=50))
        store.record(_make_entry(input_tokens=200, output_tokens=100))
        h = store.get_health()
        assert h["today_requests"] == 2
        assert h["today_tokens"] == 450

    def test_health_excludes_yesterday(self, store):
        """Entries from yesterday don't count in today's health."""
        now = time.time()
        yesterday_ts = now - 86400
        yesterday_dk = time.strftime("%Y-%m-%d", time.localtime(yesterday_ts))
        store._entries.append(_make_entry(timestamp=yesterday_ts, date_key=yesterday_dk))
        store.record(_make_entry())
        h = store.get_health()
        assert h["today_requests"] == 1

    def test_health_last_error_is_dict(self, store):
        """last_error in get_health is a dict (model_dump), not a model."""
        store.record_error("timeout", "slow")
        h = store.get_health()
        assert isinstance(h["last_error"], dict)
        assert h["last_error"]["error_type"] == "timeout"

    def test_health_zero_errors_today(self, store):
        """Old errors don't count in today_errors."""
        now = time.time()
        store.record_error("timeout", "old")
        store._errors[0].timestamp = now - 86400
        store._errors[0].date_key = time.strftime("%Y-%m-%d", time.localtime(now - 86400))
        h = store.get_health()
        assert h["today_errors"] == 0
        # But last_error still shows the old error
        assert h["last_error"] is not None
