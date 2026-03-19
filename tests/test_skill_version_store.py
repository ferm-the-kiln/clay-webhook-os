from pathlib import Path

import pytest

from app.core.skill_version_store import SkillVersionStore


@pytest.fixture
def dirs(tmp_path: Path) -> tuple[Path, Path]:
    data_dir = tmp_path / "data"
    skills_dir = tmp_path / "skills"
    data_dir.mkdir()
    skills_dir.mkdir()
    return data_dir, skills_dir


@pytest.fixture
def store(dirs) -> SkillVersionStore:
    data_dir, skills_dir = dirs
    s = SkillVersionStore(data_dir=data_dir, skills_dir=skills_dir)
    s.load()
    return s


def _create_skill(skills_dir: Path, name: str, content: str = "# Test Skill") -> Path:
    """Helper to create a skill directory with skill.md."""
    skill_dir = skills_dir / name
    skill_dir.mkdir(parents=True, exist_ok=True)
    skill_file = skill_dir / "skill.md"
    skill_file.write_text(content)
    return skill_file


# ---------------------------------------------------------------------------
# Load
# ---------------------------------------------------------------------------


class TestLoad:
    def test_load_creates_directory(self, tmp_path):
        data_dir = tmp_path / "fresh_data"
        skills_dir = tmp_path / "skills"
        s = SkillVersionStore(data_dir=data_dir, skills_dir=skills_dir)
        s.load()
        assert (data_dir / "skill_versions").is_dir()

    def test_load_empty(self, store):
        assert store.get_latest_version("nonexistent") == 0


# ---------------------------------------------------------------------------
# Save version
# ---------------------------------------------------------------------------


class TestSaveVersion:
    def test_save_first_version(self, store):
        v = store.save_version("email-gen", "# Email Gen v1")
        assert v == 1

    def test_save_increments_version(self, store):
        store.save_version("email-gen", "v1 content")
        store.save_version("email-gen", "v2 content")
        v3 = store.save_version("email-gen", "v3 content")
        assert v3 == 3

    def test_save_creates_file(self, store, dirs):
        data_dir, _ = dirs
        store.save_version("email-gen", "# Content")
        version_file = data_dir / "skill_versions" / "email-gen" / "v1.md"
        assert version_file.exists()
        assert version_file.read_text() == "# Content"

    def test_save_auto_creates_directories(self, store, dirs):
        data_dir, _ = dirs
        store.save_version("brand-new-skill", "# New")
        assert (data_dir / "skill_versions" / "brand-new-skill").is_dir()

    def test_save_multiple_skills_independent(self, store):
        store.save_version("skill-a", "a content")
        store.save_version("skill-b", "b content")
        store.save_version("skill-a", "a v2")
        assert store.get_latest_version("skill-a") == 2
        assert store.get_latest_version("skill-b") == 1


# ---------------------------------------------------------------------------
# Get versions (list)
# ---------------------------------------------------------------------------


class TestGetVersions:
    def test_list_empty(self, store):
        assert store.get_versions("nonexistent") == []

    def test_list_returns_metadata(self, store):
        store.save_version("email-gen", "short")
        versions = store.get_versions("email-gen")
        assert len(versions) == 1
        assert versions[0]["version"] == 1
        assert "timestamp" in versions[0]
        assert versions[0]["size_bytes"] == len("short")

    def test_list_multiple_versions_ordered(self, store):
        store.save_version("email-gen", "v1")
        store.save_version("email-gen", "version two content")
        store.save_version("email-gen", "v3")
        versions = store.get_versions("email-gen")
        assert len(versions) == 3
        assert versions[0]["version"] == 1
        assert versions[1]["version"] == 2
        assert versions[2]["version"] == 3

    def test_list_size_bytes_accurate(self, store):
        content = "x" * 500
        store.save_version("email-gen", content)
        versions = store.get_versions("email-gen")
        assert versions[0]["size_bytes"] == 500

    def test_list_timestamp_is_iso_format(self, store):
        store.save_version("email-gen", "content")
        versions = store.get_versions("email-gen")
        ts = versions[0]["timestamp"]
        # ISO format should contain 'T' and timezone info
        assert "T" in ts


# ---------------------------------------------------------------------------
# Get specific version
# ---------------------------------------------------------------------------


class TestGetVersion:
    def test_get_existing_version(self, store):
        store.save_version("email-gen", "version one")
        store.save_version("email-gen", "version two")
        assert store.get_version("email-gen", 1) == "version one"
        assert store.get_version("email-gen", 2) == "version two"

    def test_get_nonexistent_version(self, store):
        store.save_version("email-gen", "v1")
        assert store.get_version("email-gen", 99) is None

    def test_get_nonexistent_skill(self, store):
        assert store.get_version("nonexistent", 1) is None


# ---------------------------------------------------------------------------
# Get latest version
# ---------------------------------------------------------------------------


class TestGetLatestVersion:
    def test_latest_no_versions(self, store):
        assert store.get_latest_version("nonexistent") == 0

    def test_latest_after_saves(self, store):
        store.save_version("email-gen", "v1")
        assert store.get_latest_version("email-gen") == 1
        store.save_version("email-gen", "v2")
        assert store.get_latest_version("email-gen") == 2


# ---------------------------------------------------------------------------
# Rollback
# ---------------------------------------------------------------------------


class TestRollback:
    def test_rollback_restores_content(self, store, dirs):
        _, skills_dir = dirs
        _create_skill(skills_dir, "email-gen", "current content")
        store.save_version("email-gen", "old version 1")
        store.save_version("email-gen", "current content")

        result = store.rollback("email-gen", 1)
        assert result is True
        assert (skills_dir / "email-gen" / "skill.md").read_text() == "old version 1"

    def test_rollback_nonexistent_version(self, store, dirs):
        _, skills_dir = dirs
        _create_skill(skills_dir, "email-gen")
        assert store.rollback("email-gen", 99) is False

    def test_rollback_nonexistent_skill_dir(self, store):
        store.save_version("ghost-skill", "content")
        # Skill directory does not exist in skills_dir
        assert store.rollback("ghost-skill", 1) is False

    def test_rollback_no_versions_saved(self, store, dirs):
        _, skills_dir = dirs
        _create_skill(skills_dir, "email-gen")
        assert store.rollback("email-gen", 1) is False

    def test_rollback_preserves_version_history(self, store, dirs):
        _, skills_dir = dirs
        _create_skill(skills_dir, "email-gen")
        store.save_version("email-gen", "v1 content")
        store.save_version("email-gen", "v2 content")

        store.rollback("email-gen", 1)
        # Version history should still have both versions
        versions = store.get_versions("email-gen")
        assert len(versions) == 2


# ---------------------------------------------------------------------------
# Roundtrip
# ---------------------------------------------------------------------------


class TestRoundtrip:
    def test_save_get_roundtrip(self, store):
        original = "---\nmodel_tier: sonnet\n---\n\n# Email Generator\n\nGenerate emails."
        store.save_version("email-gen", original)
        retrieved = store.get_version("email-gen", 1)
        assert retrieved == original

    def test_full_workflow(self, store, dirs):
        _, skills_dir = dirs
        _create_skill(skills_dir, "email-gen", "initial")

        # Save v1
        store.save_version("email-gen", "initial")
        # Update skill and save v2
        store.save_version("email-gen", "updated content")
        # Verify versions
        assert store.get_latest_version("email-gen") == 2
        versions = store.get_versions("email-gen")
        assert len(versions) == 2
        # Rollback to v1
        store.rollback("email-gen", 1)
        assert (skills_dir / "email-gen" / "skill.md").read_text() == "initial"
