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
