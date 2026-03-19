"""Tests for prompt cache."""
import os
import tempfile
import time

from app.core.prompt_cache import PromptCache


class TestPromptCache:
    def test_miss_on_empty_cache(self):
        cache = PromptCache(ttl=300)
        assert cache.get("email-gen", "acme", []) is None

    def test_hit_after_put(self):
        cache = PromptCache(ttl=300)
        cache.put("email-gen", "acme", [], "system prompt here")
        result = cache.get("email-gen", "acme", [])
        assert result == "system prompt here"

    def test_different_skill_is_miss(self):
        cache = PromptCache(ttl=300)
        cache.put("email-gen", "acme", [], "prompt")
        assert cache.get("linkedin-note", "acme", []) is None

    def test_different_client_is_miss(self):
        cache = PromptCache(ttl=300)
        cache.put("email-gen", "acme", [], "prompt")
        assert cache.get("email-gen", "other", []) is None

    def test_expired_entry_is_miss(self):
        cache = PromptCache(ttl=1)
        cache.put("email-gen", "acme", [], "prompt")
        # Expire manually
        key = list(cache._cache.keys())[0]
        cache._cache[key] = (time.time() - 2, cache._cache[key][1])
        assert cache.get("email-gen", "acme", []) is None

    def test_file_mtime_changes_invalidate(self):
        cache = PromptCache(ttl=300)
        with tempfile.NamedTemporaryFile(suffix=".md", delete=False) as f:
            f.write(b"content v1")
            f.flush()
            path = f.name

        try:
            cache.put("email-gen", None, [path], "prompt v1")
            assert cache.get("email-gen", None, [path]) == "prompt v1"

            # Modify the file (change mtime)
            time.sleep(0.1)
            with open(path, "w") as f:
                f.write("content v2")

            # Key changed because mtime changed
            assert cache.get("email-gen", None, [path]) is None
        finally:
            os.unlink(path)

    def test_none_client_slug(self):
        cache = PromptCache(ttl=300)
        cache.put("email-gen", None, [], "prompt")
        assert cache.get("email-gen", None, []) == "prompt"

    def test_stats_tracking(self):
        cache = PromptCache(ttl=300)
        cache.get("a", None, [])  # miss
        cache.put("a", None, [], "prompt")
        cache.get("a", None, [])  # hit
        cache.get("a", None, [])  # hit

        stats = cache.get_stats()
        assert stats["hits"] == 2
        assert stats["misses"] == 1
        assert stats["cached_entries"] == 1
        assert stats["hit_rate"] == 0.667

    def test_clear(self):
        cache = PromptCache(ttl=300)
        cache.put("a", None, [], "prompt")
        cache.clear()
        assert cache.get("a", None, []) is None
        assert cache.get_stats()["cached_entries"] == 0
