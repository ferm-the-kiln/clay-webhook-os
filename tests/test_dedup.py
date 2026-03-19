"""Tests for request deduplication."""
import time

from app.core.dedup import RequestDeduplicator


class TestRequestDeduplicator:
    def test_no_duplicate_on_first_request(self):
        dedup = RequestDeduplicator(window_seconds=60)
        assert dedup.check("email-gen", {"name": "Alice"}) is None

    def test_duplicate_detected_within_window(self):
        dedup = RequestDeduplicator(window_seconds=60)
        result = {"email_subject": "Hi Alice", "_meta": {"skill": "email-gen"}}
        dedup.record("email-gen", {"name": "Alice"}, None, result)
        dup = dedup.check("email-gen", {"name": "Alice"})
        assert dup is not None
        assert dup["email_subject"] == "Hi Alice"

    def test_different_skill_not_duplicate(self):
        dedup = RequestDeduplicator(window_seconds=60)
        dedup.record("email-gen", {"name": "Alice"}, None, {"result": "1"})
        assert dedup.check("linkedin-note", {"name": "Alice"}) is None

    def test_different_data_not_duplicate(self):
        dedup = RequestDeduplicator(window_seconds=60)
        dedup.record("email-gen", {"name": "Alice"}, None, {"result": "1"})
        assert dedup.check("email-gen", {"name": "Bob"}) is None

    def test_different_instructions_not_duplicate(self):
        dedup = RequestDeduplicator(window_seconds=60)
        dedup.record("email-gen", {"name": "Alice"}, "be formal", {"result": "1"})
        assert dedup.check("email-gen", {"name": "Alice"}, "be casual") is None

    def test_expired_entry_not_returned(self):
        dedup = RequestDeduplicator(window_seconds=1)
        dedup.record("email-gen", {"name": "Alice"}, None, {"result": "1"})
        # Manually expire the entry
        key = list(dedup._cache.keys())[0]
        dedup._cache[key] = (time.time() - 2, dedup._cache[key][1])
        assert dedup.check("email-gen", {"name": "Alice"}) is None

    def test_stats_tracking(self):
        dedup = RequestDeduplicator(window_seconds=60)
        dedup.check("email-gen", {"name": "Alice"})  # miss
        dedup.record("email-gen", {"name": "Alice"}, None, {"result": "1"})
        dedup.check("email-gen", {"name": "Alice"})  # hit
        stats = dedup.get_stats()
        assert stats["checks"] == 2
        assert stats["hits"] == 1
        assert stats["cached_entries"] == 1
        assert stats["hit_rate"] == 0.5

    def test_eviction_on_check(self):
        dedup = RequestDeduplicator(window_seconds=1)
        dedup.record("a", {}, None, {"r": "1"})
        dedup.record("b", {}, None, {"r": "2"})
        # Expire all entries
        for key in dedup._cache:
            dedup._cache[key] = (time.time() - 2, dedup._cache[key][1])
        dedup.check("c", {})  # triggers eviction
        assert dedup.get_stats()["cached_entries"] == 0

    def test_same_data_same_instructions_is_duplicate(self):
        dedup = RequestDeduplicator(window_seconds=60)
        dedup.record("email-gen", {"name": "Alice"}, "be formal", {"result": "1"})
        dup = dedup.check("email-gen", {"name": "Alice"}, "be formal")
        assert dup is not None
