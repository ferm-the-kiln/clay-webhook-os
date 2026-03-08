import time
from unittest.mock import patch

from app.core.cache import ResultCache


class TestCacheGetPut:
    def test_put_and_get(self):
        cache = ResultCache(ttl=60)
        cache.put("skill1", {"key": "val"}, None, {"result": "ok"})
        result = cache.get("skill1", {"key": "val"})
        assert result == {"result": "ok"}

    def test_get_miss_returns_none(self):
        cache = ResultCache(ttl=60)
        assert cache.get("nonexistent", {}) is None

    def test_cache_size(self):
        cache = ResultCache(ttl=60)
        assert cache.size == 0
        cache.put("s1", {}, None, {"r": 1})
        cache.put("s2", {}, None, {"r": 2})
        assert cache.size == 2

    def test_put_overwrites_same_key(self):
        cache = ResultCache(ttl=60)
        cache.put("s", {"k": 1}, None, {"old": True})
        cache.put("s", {"k": 1}, None, {"new": True})
        assert cache.get("s", {"k": 1}) == {"new": True}
        assert cache.size == 1


class TestCacheTTL:
    def test_expired_entry_returns_none(self):
        cache = ResultCache(ttl=1)
        cache.put("s", {}, None, {"r": 1})
        with patch("app.core.cache.time") as mock_time:
            mock_time.time.return_value = time.time() + 2
            assert cache.get("s", {}) is None

    def test_not_yet_expired(self):
        cache = ResultCache(ttl=100)
        cache.put("s", {}, None, {"r": 1})
        assert cache.get("s", {}) == {"r": 1}

    def test_evict_expired(self):
        cache = ResultCache(ttl=1)
        cache.put("s1", {"a": 1}, None, {"r": 1})
        cache.put("s2", {"a": 2}, None, {"r": 2})
        with patch("app.core.cache.time") as mock_time:
            mock_time.time.return_value = time.time() + 2
            evicted = cache.evict_expired()
        assert evicted == 2
        assert cache.size == 0


class TestCacheDisabled:
    def test_ttl_zero_get_always_returns_none(self):
        cache = ResultCache(ttl=0)
        cache.put("s", {}, None, {"r": 1})
        assert cache.get("s", {}) is None

    def test_ttl_zero_put_does_not_store(self):
        cache = ResultCache(ttl=0)
        cache.put("s", {}, None, {"r": 1})
        assert cache.size == 0

    def test_ttl_negative_disabled(self):
        cache = ResultCache(ttl=-1)
        cache.put("s", {}, None, {"r": 1})
        assert cache.size == 0
        assert cache.get("s", {}) is None


class TestCacheStats:
    def test_hit_miss_counting(self):
        cache = ResultCache(ttl=60)
        cache.put("s", {}, None, {"r": 1})
        cache.get("s", {})  # hit
        cache.get("s", {})  # hit
        cache.get("missing", {})  # miss
        assert cache.hits == 2
        assert cache.misses == 1

    def test_hit_rate(self):
        cache = ResultCache(ttl=60)
        assert cache.hit_rate == 0.0
        cache.put("s", {}, None, {"r": 1})
        cache.get("s", {})  # hit
        cache.get("miss", {})  # miss
        assert cache.hit_rate == 0.5


class TestCacheKeyDeterminism:
    def test_same_inputs_same_key(self):
        cache = ResultCache(ttl=60)
        k1 = cache._key("s", {"a": 1, "b": 2}, None)
        k2 = cache._key("s", {"b": 2, "a": 1}, None)
        assert k1 == k2

    def test_different_inputs_different_key(self):
        cache = ResultCache(ttl=60)
        k1 = cache._key("s1", {}, None)
        k2 = cache._key("s2", {}, None)
        assert k1 != k2

    def test_model_affects_key(self):
        cache = ResultCache(ttl=60)
        k1 = cache._key("s", {}, None, model="opus")
        k2 = cache._key("s", {}, None, model="haiku")
        assert k1 != k2

    def test_instructions_affect_key(self):
        cache = ResultCache(ttl=60)
        k1 = cache._key("s", {}, "do X")
        k2 = cache._key("s", {}, "do Y")
        assert k1 != k2

    def test_none_model_same_as_no_model(self):
        cache = ResultCache(ttl=60)
        k1 = cache._key("s", {}, None, model=None)
        k2 = cache._key("s", {}, None)
        assert k1 == k2


class TestCacheClear:
    def test_clear_empties_store(self):
        cache = ResultCache(ttl=60)
        cache.put("s1", {}, None, {"r": 1})
        cache.put("s2", {}, None, {"r": 2})
        cache.clear()
        assert cache.size == 0

    def test_clear_does_not_reset_stats(self):
        cache = ResultCache(ttl=60)
        cache.put("s", {}, None, {"r": 1})
        cache.get("s", {})  # hit
        cache.get("miss", {})  # miss
        cache.clear()
        assert cache.hits == 1
        assert cache.misses == 1

    def test_clear_then_get_returns_none(self):
        cache = ResultCache(ttl=60)
        cache.put("s", {}, None, {"r": 1})
        cache.clear()
        assert cache.get("s", {}) is None


# ---------------------------------------------------------------------------
# get/put with model and instructions params
# ---------------------------------------------------------------------------


class TestCacheWithParams:
    def test_get_put_with_model(self):
        cache = ResultCache(ttl=60)
        cache.put("s", {"k": 1}, None, {"r": "opus"}, model="opus")
        assert cache.get("s", {"k": 1}, model="opus") == {"r": "opus"}

    def test_different_models_separate_entries(self):
        cache = ResultCache(ttl=60)
        cache.put("s", {}, None, {"r": "opus"}, model="opus")
        cache.put("s", {}, None, {"r": "haiku"}, model="haiku")
        assert cache.size == 2
        assert cache.get("s", {}, model="opus") == {"r": "opus"}
        assert cache.get("s", {}, model="haiku") == {"r": "haiku"}

    def test_model_none_vs_no_model(self):
        """model=None should match no model param."""
        cache = ResultCache(ttl=60)
        cache.put("s", {}, None, {"r": 1}, model=None)
        assert cache.get("s", {}) == {"r": 1}

    def test_get_put_with_instructions(self):
        cache = ResultCache(ttl=60)
        cache.put("s", {}, "focus on email", {"r": "custom"})
        assert cache.get("s", {}, "focus on email") == {"r": "custom"}

    def test_different_instructions_separate_entries(self):
        cache = ResultCache(ttl=60)
        cache.put("s", {}, "style A", {"r": "a"})
        cache.put("s", {}, "style B", {"r": "b"})
        assert cache.size == 2
        assert cache.get("s", {}, "style A") == {"r": "a"}

    def test_instructions_none_vs_missing(self):
        cache = ResultCache(ttl=60)
        cache.put("s", {}, None, {"r": 1})
        assert cache.get("s", {}, None) == {"r": 1}

    def test_model_and_instructions_combined(self):
        cache = ResultCache(ttl=60)
        cache.put("s", {}, "instr", {"r": 1}, model="opus")
        assert cache.get("s", {}, "instr", model="opus") == {"r": 1}
        assert cache.get("s", {}, "instr", model="haiku") is None
        assert cache.get("s", {}, "other", model="opus") is None


# ---------------------------------------------------------------------------
# Key edge cases
# ---------------------------------------------------------------------------


class TestCacheKeyEdges:
    def test_empty_string_model_not_included(self):
        """Empty string model is falsy, so treated same as None."""
        cache = ResultCache(ttl=60)
        k1 = cache._key("s", {}, None, model="")
        k2 = cache._key("s", {}, None, model=None)
        assert k1 == k2

    def test_nested_data_key(self):
        cache = ResultCache(ttl=60)
        data = {"company": {"name": "Acme", "size": 100}, "tags": ["a", "b"]}
        k1 = cache._key("s", data, None)
        k2 = cache._key("s", data, None)
        assert k1 == k2

    def test_key_is_sha256_hex(self):
        cache = ResultCache(ttl=60)
        key = cache._key("s", {}, None)
        assert len(key) == 64  # sha256 hex digest
        assert all(c in "0123456789abcdef" for c in key)

    def test_data_order_invariant(self):
        """Dict key order shouldn't affect cache key (sort_keys=True)."""
        cache = ResultCache(ttl=60)
        cache.put("s", {"z": 1, "a": 2}, None, {"r": 1})
        assert cache.get("s", {"a": 2, "z": 1}) == {"r": 1}


# ---------------------------------------------------------------------------
# TTL and expiration edge cases
# ---------------------------------------------------------------------------


class TestCacheTTLEdges:
    def test_expired_entry_removed_from_store(self):
        """Getting an expired entry should delete it from the store."""
        cache = ResultCache(ttl=1)
        cache.put("s", {}, None, {"r": 1})
        assert cache.size == 1
        with patch("app.core.cache.time") as mock_time:
            mock_time.time.return_value = time.time() + 2
            cache.get("s", {})
        assert cache.size == 0

    def test_expired_entry_counts_as_miss(self):
        cache = ResultCache(ttl=1)
        cache.put("s", {}, None, {"r": 1})
        with patch("app.core.cache.time") as mock_time:
            mock_time.time.return_value = time.time() + 2
            cache.get("s", {})
        assert cache.misses == 1
        assert cache.hits == 0

    def test_evict_partial(self):
        """Only expired entries should be evicted."""
        cache = ResultCache(ttl=10)
        now = time.time()
        cache._store["old"] = (now - 20, {"r": "old"})
        cache._store["new"] = (now, {"r": "new"})
        evicted = cache.evict_expired()
        assert evicted == 1
        assert cache.size == 1
        assert "new" in cache._store

    def test_evict_empty_cache(self):
        cache = ResultCache(ttl=60)
        assert cache.evict_expired() == 0

    def test_exactly_at_ttl_boundary(self):
        """Entry at exactly TTL age should still be expired (> not >=)."""
        cache = ResultCache(ttl=10)
        now = time.time()
        cache.put("s", {}, None, {"r": 1})
        with patch("app.core.cache.time") as mock_time:
            # Exactly at TTL + epsilon
            mock_time.time.return_value = now + 10.001
            assert cache.get("s", {}) is None

    def test_just_before_ttl_boundary(self):
        """Entry just before TTL should still be valid."""
        cache = ResultCache(ttl=10)
        now = time.time()
        with patch("app.core.cache.time") as mock_time:
            mock_time.time.return_value = now
            cache.put("s", {}, None, {"r": 1})
            mock_time.time.return_value = now + 9.999
            assert cache.get("s", {}) == {"r": 1}


# ---------------------------------------------------------------------------
# Stats edge cases
# ---------------------------------------------------------------------------


class TestCacheStatsEdges:
    def test_hit_rate_all_hits(self):
        cache = ResultCache(ttl=60)
        cache.put("s", {}, None, {"r": 1})
        cache.get("s", {})
        cache.get("s", {})
        cache.get("s", {})
        assert cache.hit_rate == 1.0

    def test_hit_rate_all_misses(self):
        cache = ResultCache(ttl=60)
        cache.get("x", {})
        cache.get("y", {})
        assert cache.hit_rate == 0.0

    def test_hit_rate_rounding(self):
        cache = ResultCache(ttl=60)
        cache.put("s", {}, None, {"r": 1})
        cache.get("s", {})  # hit
        cache.get("x", {})  # miss
        cache.get("y", {})  # miss
        assert cache.hit_rate == 0.333  # 1/3 rounded to 3 decimals

    def test_ttl_zero_get_does_not_increment_miss(self):
        """When cache is disabled (ttl=0), get returns None without counting."""
        cache = ResultCache(ttl=0)
        cache.get("s", {})
        assert cache.misses == 0
        assert cache.hits == 0

    def test_default_ttl(self):
        cache = ResultCache()
        assert cache._ttl == 3600
