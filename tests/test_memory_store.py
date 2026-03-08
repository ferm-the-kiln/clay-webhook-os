"""Tests for app/core/memory_store.py — entity memory with TTL, file persistence, prompt formatting."""

import json
import time
from pathlib import Path
from unittest.mock import patch

import pytest

from app.core.memory_store import (
    DEFAULT_TTL,
    MAX_ENTRIES_PER_ENTITY,
    MemoryEntry,
    MemoryStore,
    _extract_entity_key,
    _slugify,
)


# ---------------------------------------------------------------------------
# _slugify
# ---------------------------------------------------------------------------


class TestSlugify:
    def test_lowercase(self):
        assert _slugify("Hello") == "hello"

    def test_special_chars_replaced(self):
        assert _slugify("foo@bar.com") == "foo-bar-com"

    def test_multiple_specials_collapsed(self):
        assert _slugify("a!!b##c") == "a-b-c"

    def test_leading_trailing_stripped(self):
        assert _slugify("--hello--") == "hello"

    def test_spaces(self):
        assert _slugify("hello world") == "hello-world"

    def test_already_clean(self):
        assert _slugify("clean") == "clean"

    def test_numbers_preserved(self):
        assert _slugify("test123") == "test123"

    def test_empty_string(self):
        assert _slugify("") == ""

    def test_url_like(self):
        assert _slugify("https://example.com/path") == "https-example-com-path"


# ---------------------------------------------------------------------------
# _extract_entity_key
# ---------------------------------------------------------------------------


class TestExtractEntityKey:
    def test_company_domain_preferred(self):
        data = {"company_domain": "acme.com", "email": "bob@acme.com"}
        assert _extract_entity_key(data) == ("company", "acme-com")

    def test_domain_key(self):
        assert _extract_entity_key({"domain": "foo.io"}) == ("company", "foo-io")

    def test_website_key(self):
        assert _extract_entity_key({"website": "bar.co"}) == ("company", "bar-co")

    def test_url_protocol_stripped(self):
        assert _extract_entity_key({"domain": "https://example.com"}) == ("company", "example-com")

    def test_www_stripped(self):
        assert _extract_entity_key({"domain": "www.example.com"}) == ("company", "example-com")

    def test_trailing_slash_stripped(self):
        assert _extract_entity_key({"domain": "example.com/"}) == ("company", "example-com")

    def test_full_url_normalized(self):
        assert _extract_entity_key({"website": "https://www.example.com/"}) == ("company", "example-com")

    def test_email_key(self):
        data = {"email": "alice@test.com"}
        assert _extract_entity_key(data) == ("contact", "alice-test-com")

    def test_contact_email_key(self):
        data = {"contact_email": "bob@x.com"}
        assert _extract_entity_key(data) == ("contact", "bob-x-com")

    def test_person_email_key(self):
        data = {"person_email": "carol@y.com"}
        assert _extract_entity_key(data) == ("contact", "carol-y-com")

    def test_company_name_fallback(self):
        data = {"company_name": "Acme Corp"}
        assert _extract_entity_key(data) == ("company", "acme-corp")

    def test_company_key_fallback(self):
        data = {"company": "BigCo"}
        assert _extract_entity_key(data) == ("company", "bigco")

    def test_no_keys_returns_none(self):
        assert _extract_entity_key({}) is None
        assert _extract_entity_key({"irrelevant": "stuff"}) is None

    def test_empty_string_values_skipped(self):
        data = {"domain": "", "email": "real@test.com"}
        assert _extract_entity_key(data) == ("contact", "real-test-com")

    def test_non_string_values_skipped(self):
        data = {"domain": 123, "company_name": "Fallback"}
        assert _extract_entity_key(data) == ("company", "fallback")

    def test_priority_order_domain_over_email(self):
        data = {"email": "a@b.com", "website": "b.com"}
        assert _extract_entity_key(data) == ("company", "b-com")


# ---------------------------------------------------------------------------
# MemoryEntry
# ---------------------------------------------------------------------------


class TestMemoryEntry:
    def test_create_defaults(self):
        entry = MemoryEntry(skill="enrichment", timestamp=1000.0, summary="test")
        assert entry.skill == "enrichment"
        assert entry.timestamp == 1000.0
        assert entry.summary == "test"
        assert entry.key_fields == {}
        assert entry.ttl == DEFAULT_TTL

    def test_custom_ttl(self):
        entry = MemoryEntry(skill="s", timestamp=0, summary="", ttl=3600)
        assert entry.ttl == 3600

    def test_key_fields_set(self):
        entry = MemoryEntry(skill="s", timestamp=0, summary="", key_fields={"a": 1})
        assert entry.key_fields == {"a": 1}

    def test_is_expired_false_when_fresh(self):
        entry = MemoryEntry(skill="s", timestamp=time.time(), summary="")
        assert entry.is_expired is False

    def test_is_expired_true_when_old(self):
        entry = MemoryEntry(skill="s", timestamp=0.0, summary="", ttl=1)
        assert entry.is_expired is True

    def test_to_dict(self):
        entry = MemoryEntry(
            skill="email-gen", timestamp=1000.0, summary="sum",
            key_fields={"k": "v"}, ttl=500,
        )
        d = entry.to_dict()
        assert d == {
            "skill": "email-gen",
            "timestamp": 1000.0,
            "summary": "sum",
            "key_fields": {"k": "v"},
            "ttl": 500,
        }

    def test_from_dict(self):
        d = {"skill": "s", "timestamp": 99.0, "summary": "x", "key_fields": {"a": 1}, "ttl": 42}
        entry = MemoryEntry.from_dict(d)
        assert entry.skill == "s"
        assert entry.timestamp == 99.0
        assert entry.summary == "x"
        assert entry.key_fields == {"a": 1}
        assert entry.ttl == 42

    def test_from_dict_defaults(self):
        d = {"skill": "s", "timestamp": 0}
        entry = MemoryEntry.from_dict(d)
        assert entry.summary == ""
        assert entry.key_fields == {}
        assert entry.ttl == DEFAULT_TTL

    def test_roundtrip(self):
        original = MemoryEntry(skill="test", timestamp=12345.0, summary="round", key_fields={"x": [1, 2]}, ttl=9999)
        restored = MemoryEntry.from_dict(original.to_dict())
        assert restored.skill == original.skill
        assert restored.timestamp == original.timestamp
        assert restored.summary == original.summary
        assert restored.key_fields == original.key_fields
        assert restored.ttl == original.ttl


# ---------------------------------------------------------------------------
# MemoryStore — load
# ---------------------------------------------------------------------------


class TestMemoryStoreLoad:
    def test_load_creates_directory(self, tmp_path):
        store = MemoryStore(data_dir=tmp_path)
        memory_dir = tmp_path / "memory"
        assert not memory_dir.exists()
        store.load()
        assert memory_dir.exists()

    def test_load_counts_entities(self, tmp_path):
        memory_dir = tmp_path / "memory" / "company"
        memory_dir.mkdir(parents=True)
        (memory_dir / "acme.json").write_text('{"entries": []}')
        (memory_dir / "bigco.json").write_text('{"entries": []}')
        store = MemoryStore(data_dir=tmp_path)
        store.load()  # Should log "2 entities" without error

    def test_load_ignores_non_json(self, tmp_path):
        memory_dir = tmp_path / "memory" / "company"
        memory_dir.mkdir(parents=True)
        (memory_dir / "acme.json").write_text('{"entries": []}')
        (memory_dir / "readme.txt").write_text("ignore me")
        store = MemoryStore(data_dir=tmp_path)
        store.load()  # Should count only 1


# ---------------------------------------------------------------------------
# MemoryStore — store
# ---------------------------------------------------------------------------


class TestMemoryStoreStore:
    def _make_store(self, tmp_path):
        store = MemoryStore(data_dir=tmp_path)
        store.load()
        return store

    def test_store_creates_file(self, tmp_path):
        store = self._make_store(tmp_path)
        store.store("company", "acme", "enrichment", {"revenue": "10M"})
        path = tmp_path / "memory" / "company" / "acme.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert len(data["entries"]) == 1
        assert data["entries"][0]["skill"] == "enrichment"

    def test_store_appends_entries(self, tmp_path):
        store = self._make_store(tmp_path)
        store.store("company", "acme", "skill-a", {"a": 1})
        store.store("company", "acme", "skill-b", {"b": 2})
        path = tmp_path / "memory" / "company" / "acme.json"
        data = json.loads(path.read_text())
        assert len(data["entries"]) == 2

    def test_store_builds_summary(self, tmp_path):
        store = self._make_store(tmp_path)
        store.store("company", "acme", "enrichment", {"revenue": "10M", "employees": 50})
        path = tmp_path / "memory" / "company" / "acme.json"
        data = json.loads(path.read_text())
        summary = data["entries"][0]["summary"]
        assert "revenue: 10M" in summary
        assert "employees: 50" in summary

    def test_store_skips_underscore_fields(self, tmp_path):
        store = self._make_store(tmp_path)
        store.store("company", "acme", "s", {"_internal": "hidden", "visible": "yes"})
        path = tmp_path / "memory" / "company" / "acme.json"
        data = json.loads(path.read_text())
        assert "_internal" not in data["entries"][0]["key_fields"]
        assert data["entries"][0]["key_fields"]["visible"] == "yes"

    def test_store_skips_long_text_in_summary(self, tmp_path):
        store = self._make_store(tmp_path)
        long_text = "x" * 201
        store.store("company", "acme", "s", {"long": long_text, "short": "ok"})
        path = tmp_path / "memory" / "company" / "acme.json"
        data = json.loads(path.read_text())
        summary = data["entries"][0]["summary"]
        assert "short: ok" in summary
        # Long text is in key_fields but NOT in summary
        assert long_text not in summary
        assert data["entries"][0]["key_fields"]["long"] == long_text

    def test_store_includes_short_lists_in_key_fields(self, tmp_path):
        store = self._make_store(tmp_path)
        store.store("company", "acme", "s", {"tags": ["a", "b", "c"]})
        path = tmp_path / "memory" / "company" / "acme.json"
        data = json.loads(path.read_text())
        assert data["entries"][0]["key_fields"]["tags"] == ["a", "b", "c"]

    def test_store_excludes_long_lists(self, tmp_path):
        store = self._make_store(tmp_path)
        store.store("company", "acme", "s", {"big_list": list(range(10))})
        path = tmp_path / "memory" / "company" / "acme.json"
        data = json.loads(path.read_text())
        assert "big_list" not in data["entries"][0]["key_fields"]

    def test_store_prunes_expired(self, tmp_path):
        store = self._make_store(tmp_path)
        # Write an expired entry directly
        path = tmp_path / "memory" / "company" / "acme.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        old_entry = {"skill": "old", "timestamp": 0.0, "summary": "expired", "key_fields": {}, "ttl": 1}
        path.write_text(json.dumps({"entries": [old_entry]}))
        # Store a new entry — should prune the expired one
        store.store("company", "acme", "new-skill", {"x": 1})
        data = json.loads(path.read_text())
        assert len(data["entries"]) == 1
        assert data["entries"][0]["skill"] == "new-skill"

    def test_store_caps_at_max_entries(self, tmp_path):
        store = self._make_store(tmp_path)
        for i in range(MAX_ENTRIES_PER_ENTITY + 5):
            store.store("company", "acme", f"skill-{i}", {"i": i})
        path = tmp_path / "memory" / "company" / "acme.json"
        data = json.loads(path.read_text())
        assert len(data["entries"]) == MAX_ENTRIES_PER_ENTITY

    def test_store_caps_summary_parts(self, tmp_path):
        store = self._make_store(tmp_path)
        # Create result with many fields
        result = {f"field_{i}": f"val_{i}" for i in range(20)}
        store.store("company", "acme", "s", result)
        path = tmp_path / "memory" / "company" / "acme.json"
        data = json.loads(path.read_text())
        summary = data["entries"][0]["summary"]
        # Summary is capped at 10 parts
        assert summary.count(";") <= 9


# ---------------------------------------------------------------------------
# MemoryStore — store_from_data
# ---------------------------------------------------------------------------


class TestStoreFromData:
    def test_auto_extracts_entity(self, tmp_path):
        store = MemoryStore(data_dir=tmp_path)
        store.load()
        store.store_from_data({"domain": "test.com"}, "enrichment", {"x": 1})
        path = tmp_path / "memory" / "company" / "test-com.json"
        assert path.exists()

    def test_no_entity_key_silently_returns(self, tmp_path):
        store = MemoryStore(data_dir=tmp_path)
        store.load()
        store.store_from_data({"random": "data"}, "enrichment", {"x": 1})
        # No files created
        memory_dir = tmp_path / "memory"
        entity_files = list(memory_dir.rglob("*.json"))
        assert len(entity_files) == 0


# ---------------------------------------------------------------------------
# MemoryStore — query / get_entity
# ---------------------------------------------------------------------------


class TestMemoryStoreQuery:
    def _make_store_with_entry(self, tmp_path, entity_type="company", entity_id="acme"):
        store = MemoryStore(data_dir=tmp_path)
        store.load()
        store.store(entity_type, entity_id, "test-skill", {"result": "ok"})
        return store

    def test_query_finds_entity(self, tmp_path):
        store = self._make_store_with_entry(tmp_path)
        entries = store.query({"domain": "acme"})
        assert len(entries) == 1
        assert entries[0].skill == "test-skill"

    def test_query_no_match(self, tmp_path):
        store = self._make_store_with_entry(tmp_path)
        entries = store.query({"domain": "unknown"})
        assert entries == []

    def test_query_no_entity_key(self, tmp_path):
        store = self._make_store_with_entry(tmp_path)
        entries = store.query({"irrelevant": "data"})
        assert entries == []

    def test_get_entity_returns_entries(self, tmp_path):
        store = self._make_store_with_entry(tmp_path)
        entries = store.get_entity("company", "acme")
        assert len(entries) == 1

    def test_get_entity_missing_returns_empty(self, tmp_path):
        store = MemoryStore(data_dir=tmp_path)
        store.load()
        assert store.get_entity("company", "nonexistent") == []

    def test_get_entity_filters_expired(self, tmp_path):
        store = MemoryStore(data_dir=tmp_path)
        store.load()
        path = tmp_path / "memory" / "company" / "acme.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        entries = [
            {"skill": "expired", "timestamp": 0.0, "summary": "", "key_fields": {}, "ttl": 1},
            {"skill": "fresh", "timestamp": time.time(), "summary": "", "key_fields": {}, "ttl": 999999},
        ]
        path.write_text(json.dumps({"entries": entries}))
        result = store.get_entity("company", "acme")
        assert len(result) == 1
        assert result[0].skill == "fresh"

    def test_get_entity_bad_json_returns_empty(self, tmp_path):
        store = MemoryStore(data_dir=tmp_path)
        store.load()
        path = tmp_path / "memory" / "company" / "acme.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("not json")
        assert store.get_entity("company", "acme") == []


# ---------------------------------------------------------------------------
# MemoryStore — prune_expired
# ---------------------------------------------------------------------------


class TestPruneExpired:
    def test_prune_removes_expired(self, tmp_path):
        store = MemoryStore(data_dir=tmp_path)
        store.load()
        path = tmp_path / "memory" / "company" / "acme.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        entries = [
            {"skill": "expired", "timestamp": 0.0, "summary": "", "key_fields": {}, "ttl": 1},
            {"skill": "fresh", "timestamp": time.time(), "summary": "", "key_fields": {}, "ttl": 999999},
        ]
        path.write_text(json.dumps({"entries": entries}))
        removed = store.prune_expired()
        assert removed == 1
        data = json.loads(path.read_text())
        assert len(data["entries"]) == 1
        assert data["entries"][0]["skill"] == "fresh"

    def test_prune_deletes_empty_files(self, tmp_path):
        store = MemoryStore(data_dir=tmp_path)
        store.load()
        path = tmp_path / "memory" / "company" / "acme.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        entries = [{"skill": "old", "timestamp": 0.0, "summary": "", "key_fields": {}, "ttl": 1}]
        path.write_text(json.dumps({"entries": entries}))
        removed = store.prune_expired()
        assert removed == 1
        assert not path.exists()

    def test_prune_returns_zero_when_nothing_expired(self, tmp_path):
        store = MemoryStore(data_dir=tmp_path)
        store.load()
        path = tmp_path / "memory" / "company" / "acme.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        entries = [{"skill": "fresh", "timestamp": time.time(), "summary": "", "key_fields": {}, "ttl": 999999}]
        path.write_text(json.dumps({"entries": entries}))
        assert store.prune_expired() == 0

    def test_prune_empty_store(self, tmp_path):
        store = MemoryStore(data_dir=tmp_path)
        store.load()
        assert store.prune_expired() == 0

    def test_prune_multiple_entities(self, tmp_path):
        store = MemoryStore(data_dir=tmp_path)
        store.load()
        for name in ("a", "b", "c"):
            path = tmp_path / "memory" / "company" / f"{name}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            entries = [{"skill": "old", "timestamp": 0.0, "summary": "", "key_fields": {}, "ttl": 1}]
            path.write_text(json.dumps({"entries": entries}))
        removed = store.prune_expired()
        assert removed == 3


# ---------------------------------------------------------------------------
# MemoryStore — format_for_prompt
# ---------------------------------------------------------------------------


class TestFormatForPrompt:
    def test_empty_entries(self):
        store = MemoryStore(data_dir=Path("/tmp"))
        assert store.format_for_prompt([]) == ""

    def test_header_includes_count(self):
        entries = [MemoryEntry(skill="s", timestamp=time.time(), summary="test")]
        store = MemoryStore(data_dir=Path("/tmp"))
        result = store.format_for_prompt(entries)
        assert "1 entries" in result

    def test_minutes_ago_format(self):
        entries = [MemoryEntry(skill="enrichment", timestamp=time.time() - 300, summary="recent")]
        store = MemoryStore(data_dir=Path("/tmp"))
        result = store.format_for_prompt(entries)
        assert "m ago" in result
        assert "**enrichment**" in result
        assert "recent" in result

    def test_hours_ago_format(self):
        entries = [MemoryEntry(skill="s", timestamp=time.time() - 7200, summary="older")]
        store = MemoryStore(data_dir=Path("/tmp"))
        result = store.format_for_prompt(entries)
        assert "h ago" in result

    def test_days_ago_format(self):
        entries = [MemoryEntry(skill="s", timestamp=time.time() - 86400 * 3, summary="old")]
        store = MemoryStore(data_dir=Path("/tmp"))
        result = store.format_for_prompt(entries)
        assert "d ago" in result

    def test_multiple_entries(self):
        entries = [
            MemoryEntry(skill="a", timestamp=time.time(), summary="first"),
            MemoryEntry(skill="b", timestamp=time.time(), summary="second"),
        ]
        store = MemoryStore(data_dir=Path("/tmp"))
        result = store.format_for_prompt(entries)
        assert "2 entries" in result
        assert "**a**" in result
        assert "**b**" in result
        assert "first" in result
        assert "second" in result


# ---------------------------------------------------------------------------
# MemoryStore — _entity_path
# ---------------------------------------------------------------------------


class TestEntityPath:
    def test_path_structure(self, tmp_path):
        store = MemoryStore(data_dir=tmp_path)
        path = store._entity_path("company", "acme")
        assert path == tmp_path / "memory" / "company" / "acme.json"

    def test_contact_path(self, tmp_path):
        store = MemoryStore(data_dir=tmp_path)
        path = store._entity_path("contact", "bob-test-com")
        assert path == tmp_path / "memory" / "contact" / "bob-test-com.json"
