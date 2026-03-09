from pathlib import Path
from unittest.mock import patch

from app.core.skill_loader import (
    _skill_cache,
    create_skill,
    delete_skill,
    get_skill_raw,
    list_skills,
    load_context_files,
    load_file,
    load_skill,
    load_skill_config,
    load_skill_variant,
    parse_context_refs,
    parse_frontmatter,
    resolve_template_vars,
    save_skill,
)


class TestParseFrontmatter:
    def test_valid_frontmatter(self, sample_skill_content):
        fm, body = parse_frontmatter(sample_skill_content)
        assert fm["model_tier"] == "sonnet"
        assert "context" in fm
        assert body.startswith("# Test Skill")

    def test_no_frontmatter(self, sample_skill_no_frontmatter):
        fm, body = parse_frontmatter(sample_skill_no_frontmatter)
        assert fm == {}
        assert body == sample_skill_no_frontmatter

    def test_malformed_yaml(self):
        content = "---\n: [invalid yaml\n---\nBody"
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_unclosed_frontmatter(self):
        content = "---\nkey: value\nBody without closing"
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == content

    def test_empty_frontmatter(self):
        content = "---\n---\nBody here"
        fm, body = parse_frontmatter(content)
        assert fm == {}
        assert body == "Body here"

    def test_frontmatter_with_multiple_fields(self):
        content = "---\nmodel: opus\nmodel_tier: heavy\ntags:\n  - sales\n  - outbound\n---\nBody"
        fm, body = parse_frontmatter(content)
        assert fm["model"] == "opus"
        assert fm["model_tier"] == "heavy"
        assert fm["tags"] == ["sales", "outbound"]
        assert body == "Body"


class TestParseContextRefs:
    def test_extracts_knowledge_base_refs(self):
        content = "- knowledge_base/frameworks/sales.md\n- knowledge_base/voice/default.md"
        refs = parse_context_refs(content)
        assert refs == ["knowledge_base/frameworks/sales.md", "knowledge_base/voice/default.md"]

    def test_extracts_client_refs(self):
        content = "- clients/{{client_slug}}.md"
        refs = parse_context_refs(content)
        assert refs == ["clients/{{client_slug}}.md"]

    def test_star_bullet_works(self):
        content = "* knowledge_base/industries/saas.md"
        refs = parse_context_refs(content)
        assert refs == ["knowledge_base/industries/saas.md"]

    def test_ignores_non_matching_lines(self):
        content = "- some/other/path.md\n- knowledge_base/real.md\nPlain text"
        refs = parse_context_refs(content)
        assert refs == ["knowledge_base/real.md"]

    def test_empty_content(self):
        assert parse_context_refs("") == []


class TestResolveTemplateVars:
    def test_client_slug_substitution(self, mock_settings):
        with patch("app.core.skill_loader.settings", mock_settings):
            result = resolve_template_vars("clients/{{client_slug}}.md", {"client_slug": "acme"})
        assert result == "clients/acme.md"

    def test_persona_slug_substitution(self, mock_settings):
        with patch("app.core.skill_loader.settings", mock_settings):
            result = resolve_template_vars("knowledge_base/{{persona_slug}}/voice.md", {"persona_slug": "dan"})
        assert result == "knowledge_base/dan/voice.md"

    def test_missing_var_keeps_placeholder(self, mock_settings):
        with patch("app.core.skill_loader.settings", mock_settings):
            result = resolve_template_vars("clients/{{client_slug}}.md", {})
        assert "{{client_slug}}" in result

    def test_no_placeholders_passthrough(self, mock_settings):
        with patch("app.core.skill_loader.settings", mock_settings):
            result = resolve_template_vars("knowledge_base/frameworks/sales.md", {})
        assert result == "knowledge_base/frameworks/sales.md"


class TestLoadSkill:
    def test_load_existing_skill(self, tmp_skills_dir, sample_skill_content, mock_settings):
        skill_dir = tmp_skills_dir / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "skill.md").write_text(sample_skill_content)
        mock_settings.skills_dir = tmp_skills_dir

        _skill_cache.clear()
        with patch("app.core.skill_loader.settings", mock_settings):
            body = load_skill("test-skill")
        assert body is not None
        assert "# Test Skill" in body

    def test_load_nonexistent_skill(self, mock_settings):
        with patch("app.core.skill_loader.settings", mock_settings):
            assert load_skill("nope") is None

    def test_load_skill_caches_on_mtime(self, tmp_skills_dir, sample_skill_content, mock_settings):
        skill_dir = tmp_skills_dir / "cached"
        skill_dir.mkdir()
        (skill_dir / "skill.md").write_text(sample_skill_content)
        mock_settings.skills_dir = tmp_skills_dir

        _skill_cache.clear()
        with patch("app.core.skill_loader.settings", mock_settings):
            body1 = load_skill("cached")
            body2 = load_skill("cached")
        assert body1 == body2


class TestLoadSkillConfig:
    def test_returns_frontmatter_dict(self, tmp_skills_dir, sample_skill_content, mock_settings):
        skill_dir = tmp_skills_dir / "configured"
        skill_dir.mkdir()
        (skill_dir / "skill.md").write_text(sample_skill_content)
        mock_settings.skills_dir = tmp_skills_dir

        _skill_cache.clear()
        with patch("app.core.skill_loader.settings", mock_settings):
            config = load_skill_config("configured")
        assert config["model_tier"] == "sonnet"

    def test_nonexistent_returns_empty(self, mock_settings):
        with patch("app.core.skill_loader.settings", mock_settings):
            assert load_skill_config("missing") == {}


class TestListSkills:
    def test_lists_skill_directories(self, tmp_skills_dir, mock_settings):
        for name in ["alpha", "beta", "gamma"]:
            d = tmp_skills_dir / name
            d.mkdir()
            (d / "skill.md").write_text("# " + name)
        mock_settings.skills_dir = tmp_skills_dir

        with patch("app.core.skill_loader.settings", mock_settings):
            skills = list_skills()
        assert skills == ["alpha", "beta", "gamma"]

    def test_ignores_dirs_without_skill_md(self, tmp_skills_dir, mock_settings):
        (tmp_skills_dir / "has-skill").mkdir()
        (tmp_skills_dir / "has-skill" / "skill.md").write_text("# ok")
        (tmp_skills_dir / "no-skill").mkdir()
        mock_settings.skills_dir = tmp_skills_dir

        with patch("app.core.skill_loader.settings", mock_settings):
            skills = list_skills()
        assert skills == ["has-skill"]

    def test_empty_dir(self, tmp_skills_dir, mock_settings):
        mock_settings.skills_dir = tmp_skills_dir
        with patch("app.core.skill_loader.settings", mock_settings):
            assert list_skills() == []

    def test_nonexistent_dir(self, mock_settings, tmp_path):
        mock_settings.skills_dir = tmp_path / "nonexistent"
        with patch("app.core.skill_loader.settings", mock_settings):
            assert list_skills() == []


# ---------------------------------------------------------------------------
# load_skill_variant
# ---------------------------------------------------------------------------


class TestLoadSkillVariant:
    def test_default_variant_delegates_to_load_skill(self, tmp_skills_dir, sample_skill_content, mock_settings):
        skill_dir = tmp_skills_dir / "email-gen"
        skill_dir.mkdir()
        (skill_dir / "skill.md").write_text(sample_skill_content)
        mock_settings.skills_dir = tmp_skills_dir

        _skill_cache.clear()
        with patch("app.core.skill_loader.settings", mock_settings):
            body = load_skill_variant("email-gen", "default")
        assert body is not None
        assert "# Test Skill" in body

    def test_custom_variant(self, tmp_skills_dir, mock_settings):
        skill_dir = tmp_skills_dir / "email-gen"
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir(parents=True)
        (variants_dir / "v_abc123.md").write_text("# Short CTA variant")
        mock_settings.skills_dir = tmp_skills_dir

        with patch("app.core.skill_loader.settings", mock_settings):
            body = load_skill_variant("email-gen", "v_abc123")
        assert body == "# Short CTA variant"

    def test_missing_variant_returns_none(self, tmp_skills_dir, mock_settings):
        skill_dir = tmp_skills_dir / "email-gen"
        skill_dir.mkdir(parents=True)
        mock_settings.skills_dir = tmp_skills_dir

        with patch("app.core.skill_loader.settings", mock_settings):
            assert load_skill_variant("email-gen", "v_nonexistent") is None


# ---------------------------------------------------------------------------
# load_file
# ---------------------------------------------------------------------------


class TestLoadFile:
    def test_existing_file(self, tmp_path, mock_settings):
        kb_dir = tmp_path / "knowledge_base" / "voice"
        kb_dir.mkdir(parents=True)
        (kb_dir / "default.md").write_text("# Default Voice")

        with patch("app.core.skill_loader.settings", mock_settings):
            content = load_file("knowledge_base/voice/default.md")
        assert content == "# Default Voice"

    def test_missing_file(self, mock_settings):
        with patch("app.core.skill_loader.settings", mock_settings):
            assert load_file("knowledge_base/nonexistent.md") is None


# ---------------------------------------------------------------------------
# resolve_template_vars — profile.md redirect
# ---------------------------------------------------------------------------


class TestResolveTemplateVarsProfileRedirect:
    def test_profile_path_redirect(self, tmp_path, mock_settings):
        """clients/acme.md -> clients/acme/profile.md when profile.md exists."""
        profile_dir = tmp_path / "clients" / "acme"
        profile_dir.mkdir(parents=True)
        (profile_dir / "profile.md").write_text("# Acme Profile")

        with patch("app.core.skill_loader.settings", mock_settings):
            result = resolve_template_vars("clients/acme.md", {})
        assert result == "clients/acme/profile.md"

    def test_no_redirect_when_profile_missing(self, tmp_path, mock_settings):
        """clients/acme.md stays as-is when no profile.md directory exists."""
        with patch("app.core.skill_loader.settings", mock_settings):
            result = resolve_template_vars("clients/acme.md", {})
        assert result == "clients/acme.md"

    def test_no_redirect_for_already_profile_path(self, tmp_path, mock_settings):
        """clients/acme/profile.md doesn't get double-redirected."""
        with patch("app.core.skill_loader.settings", mock_settings):
            result = resolve_template_vars("clients/acme/profile.md", {})
        assert result == "clients/acme/profile.md"

    def test_no_redirect_for_non_client_paths(self, mock_settings):
        with patch("app.core.skill_loader.settings", mock_settings):
            result = resolve_template_vars("knowledge_base/voice.md", {})
        assert result == "knowledge_base/voice.md"


# ---------------------------------------------------------------------------
# load_context_files
# ---------------------------------------------------------------------------


class TestLoadContextFiles:
    def test_defaults_layer_autoloads(self, tmp_path, mock_settings):
        defaults_dir = tmp_path / "knowledge_base" / "_defaults"
        defaults_dir.mkdir(parents=True)
        (defaults_dir / "rules.md").write_text("# Rules")
        (defaults_dir / "format.md").write_text("# Format")

        with patch("app.core.skill_loader.settings", mock_settings):
            files = load_context_files("# Skill body", {})
        paths = [f["path"] for f in files]
        assert "knowledge_base/_defaults/format.md" in paths
        assert "knowledge_base/_defaults/rules.md" in paths

    def test_defaults_sorted_alphabetically(self, tmp_path, mock_settings):
        defaults_dir = tmp_path / "knowledge_base" / "_defaults"
        defaults_dir.mkdir(parents=True)
        (defaults_dir / "z_last.md").write_text("Z")
        (defaults_dir / "a_first.md").write_text("A")

        with patch("app.core.skill_loader.settings", mock_settings):
            files = load_context_files("# Body", {})
        paths = [f["path"] for f in files]
        assert paths.index("knowledge_base/_defaults/a_first.md") < paths.index("knowledge_base/_defaults/z_last.md")

    def test_context_refs_from_frontmatter(self, tmp_path, mock_settings, sample_skill_content):
        # Create the KB file referenced in frontmatter
        frameworks_dir = tmp_path / "knowledge_base" / "frameworks"
        frameworks_dir.mkdir(parents=True)
        (frameworks_dir / "sales.md").write_text("# Sales Framework")

        # Create skill so load_skill_config works
        skill_dir = tmp_path / "skills" / "test-skill"
        skill_dir.mkdir(parents=True)
        (skill_dir / "skill.md").write_text(sample_skill_content)

        _skill_cache.clear()
        with patch("app.core.skill_loader.settings", mock_settings):
            files = load_context_files(
                sample_skill_content, {"client_slug": "acme"}, skill_name="test-skill"
            )
        paths = [f["path"] for f in files]
        assert "knowledge_base/frameworks/sales.md" in paths

    def test_context_refs_regex_fallback_no_skill_name(self, tmp_path, mock_settings):
        # When skill_name is None, should use regex parsing
        kb_dir = tmp_path / "knowledge_base" / "voice"
        kb_dir.mkdir(parents=True)
        (kb_dir / "default.md").write_text("# Voice")

        content = "- knowledge_base/voice/default.md"
        with patch("app.core.skill_loader.settings", mock_settings):
            files = load_context_files(content, {})
        paths = [f["path"] for f in files]
        assert "knowledge_base/voice/default.md" in paths

    def test_unresolved_template_vars_skipped(self, tmp_path, mock_settings):
        content = "- clients/{{client_slug}}.md"
        with patch("app.core.skill_loader.settings", mock_settings):
            files = load_context_files(content, {})  # no client_slug in data
        # The ref has unresolved {{client_slug}} so should be skipped
        paths = [f["path"] for f in files]
        assert not any("client_slug" in p for p in paths)

    def test_industry_autoload(self, tmp_path, mock_settings):
        industries_dir = tmp_path / "knowledge_base" / "industries"
        industries_dir.mkdir(parents=True)
        (industries_dir / "saas.md").write_text("# SaaS Industry")

        with patch("app.core.skill_loader.settings", mock_settings):
            files = load_context_files("# Body", {"industry": "SaaS"})
        paths = [f["path"] for f in files]
        assert "knowledge_base/industries/saas.md" in paths

    def test_industry_slug_normalization(self, tmp_path, mock_settings):
        industries_dir = tmp_path / "knowledge_base" / "industries"
        industries_dir.mkdir(parents=True)
        (industries_dir / "health-tech.md").write_text("# HealthTech")

        with patch("app.core.skill_loader.settings", mock_settings):
            files = load_context_files("# Body", {"industry": "Health Tech"})
        paths = [f["path"] for f in files]
        assert "knowledge_base/industries/health-tech.md" in paths

    def test_no_industry_key(self, tmp_path, mock_settings):
        with patch("app.core.skill_loader.settings", mock_settings):
            files = load_context_files("# Body", {})
        # No industry auto-load
        paths = [f["path"] for f in files]
        assert not any("industries" in p for p in paths)

    def test_deduplication(self, tmp_path, mock_settings):
        """Same file referenced in defaults and refs should only appear once."""
        defaults_dir = tmp_path / "knowledge_base" / "_defaults"
        defaults_dir.mkdir(parents=True)
        (defaults_dir / "rules.md").write_text("# Rules")

        content = "- knowledge_base/_defaults/rules.md"  # same as default
        with patch("app.core.skill_loader.settings", mock_settings):
            files = load_context_files(content, {})
        paths = [f["path"] for f in files]
        assert paths.count("knowledge_base/_defaults/rules.md") == 1

    def test_missing_ref_file_skipped(self, tmp_path, mock_settings):
        content = "- knowledge_base/voice/nonexistent.md"
        with patch("app.core.skill_loader.settings", mock_settings):
            files = load_context_files(content, {})
        assert len(files) == 0

    def test_defaults_ignores_non_md_files(self, tmp_path, mock_settings):
        defaults_dir = tmp_path / "knowledge_base" / "_defaults"
        defaults_dir.mkdir(parents=True)
        (defaults_dir / "rules.md").write_text("# Rules")
        (defaults_dir / "notes.txt").write_text("Not markdown")

        with patch("app.core.skill_loader.settings", mock_settings):
            files = load_context_files("# Body", {})
        paths = [f["path"] for f in files]
        assert "knowledge_base/_defaults/rules.md" in paths
        assert not any(".txt" in p for p in paths)

    def test_industry_dedup_with_refs(self, tmp_path, mock_settings):
        """Industry file already in refs shouldn't duplicate."""
        industries_dir = tmp_path / "knowledge_base" / "industries"
        industries_dir.mkdir(parents=True)
        (industries_dir / "saas.md").write_text("# SaaS")

        content = "- knowledge_base/industries/saas.md"
        with patch("app.core.skill_loader.settings", mock_settings):
            files = load_context_files(content, {"industry": "SaaS"})
        paths = [f["path"] for f in files]
        assert paths.count("knowledge_base/industries/saas.md") == 1


# ---------------------------------------------------------------------------
# DEEPER TESTS — CRUD helpers
# ---------------------------------------------------------------------------


class TestGetSkillRaw:
    def test_returns_full_content_with_frontmatter(self, tmp_skills_dir, sample_skill_content, mock_settings):
        skill_dir = tmp_skills_dir / "email-gen"
        skill_dir.mkdir()
        (skill_dir / "skill.md").write_text(sample_skill_content)
        mock_settings.skills_dir = tmp_skills_dir

        with patch("app.core.skill_loader.settings", mock_settings):
            raw = get_skill_raw("email-gen")
        assert raw is not None
        assert raw.startswith("---")
        assert "model_tier: sonnet" in raw
        assert "# Test Skill" in raw

    def test_returns_none_for_missing_skill(self, mock_settings):
        with patch("app.core.skill_loader.settings", mock_settings):
            assert get_skill_raw("nonexistent") is None

    def test_returns_content_without_frontmatter(self, tmp_skills_dir, mock_settings):
        skill_dir = tmp_skills_dir / "plain"
        skill_dir.mkdir()
        (skill_dir / "skill.md").write_text("# Just body, no frontmatter")
        mock_settings.skills_dir = tmp_skills_dir

        with patch("app.core.skill_loader.settings", mock_settings):
            raw = get_skill_raw("plain")
        assert raw == "# Just body, no frontmatter"


class TestSaveSkill:
    def test_saves_content_to_existing_skill(self, tmp_skills_dir, mock_settings):
        skill_dir = tmp_skills_dir / "email-gen"
        skill_dir.mkdir()
        skill_file = skill_dir / "skill.md"
        skill_file.write_text("# Original")
        mock_settings.skills_dir = tmp_skills_dir

        with patch("app.core.skill_loader.settings", mock_settings):
            result = save_skill("email-gen", "# Updated content")
        assert result is True
        assert skill_file.read_text() == "# Updated content"

    def test_returns_false_for_missing_skill(self, mock_settings):
        with patch("app.core.skill_loader.settings", mock_settings):
            assert save_skill("nonexistent", "# Content") is False

    def test_invalidates_cache(self, tmp_skills_dir, sample_skill_content, mock_settings):
        skill_dir = tmp_skills_dir / "cached-skill"
        skill_dir.mkdir()
        (skill_dir / "skill.md").write_text(sample_skill_content)
        mock_settings.skills_dir = tmp_skills_dir

        _skill_cache.clear()
        with patch("app.core.skill_loader.settings", mock_settings):
            load_skill("cached-skill")
            assert "cached-skill" in _skill_cache
            save_skill("cached-skill", "# New content")
            assert "cached-skill" not in _skill_cache


class TestCreateSkill:
    def test_creates_skill_directory_and_file(self, tmp_skills_dir, mock_settings):
        mock_settings.skills_dir = tmp_skills_dir

        with patch("app.core.skill_loader.settings", mock_settings):
            result = create_skill("new-skill", "# New Skill\nBody here")
        assert result is True
        assert (tmp_skills_dir / "new-skill" / "skill.md").exists()
        assert (tmp_skills_dir / "new-skill" / "skill.md").read_text() == "# New Skill\nBody here"

    def test_returns_false_if_already_exists(self, tmp_skills_dir, mock_settings):
        (tmp_skills_dir / "existing").mkdir()
        mock_settings.skills_dir = tmp_skills_dir

        with patch("app.core.skill_loader.settings", mock_settings):
            result = create_skill("existing", "# Content")
        assert result is False

    def test_creates_parent_dirs(self, tmp_path, mock_settings):
        skills_dir = tmp_path / "deep" / "skills"
        mock_settings.skills_dir = skills_dir

        with patch("app.core.skill_loader.settings", mock_settings):
            result = create_skill("nested-skill", "# Content")
        assert result is True
        assert (skills_dir / "nested-skill" / "skill.md").exists()


class TestDeleteSkill:
    def test_deletes_skill_directory(self, tmp_skills_dir, mock_settings):
        skill_dir = tmp_skills_dir / "to-delete"
        skill_dir.mkdir()
        (skill_dir / "skill.md").write_text("# Delete me")
        mock_settings.skills_dir = tmp_skills_dir

        with patch("app.core.skill_loader.settings", mock_settings):
            result = delete_skill("to-delete")
        assert result is True
        assert not skill_dir.exists()

    def test_returns_false_for_missing_skill(self, mock_settings):
        with patch("app.core.skill_loader.settings", mock_settings):
            assert delete_skill("nonexistent") is False

    def test_invalidates_cache(self, tmp_skills_dir, sample_skill_content, mock_settings):
        skill_dir = tmp_skills_dir / "cached-del"
        skill_dir.mkdir()
        (skill_dir / "skill.md").write_text(sample_skill_content)
        mock_settings.skills_dir = tmp_skills_dir

        _skill_cache.clear()
        with patch("app.core.skill_loader.settings", mock_settings):
            load_skill("cached-del")
            assert "cached-del" in _skill_cache
            delete_skill("cached-del")
            assert "cached-del" not in _skill_cache

    def test_deletes_directory_with_variants(self, tmp_skills_dir, mock_settings):
        skill_dir = tmp_skills_dir / "with-variants"
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir(parents=True)
        (skill_dir / "skill.md").write_text("# Main")
        (variants_dir / "v1.md").write_text("# Variant 1")
        (variants_dir / "v2.md").write_text("# Variant 2")
        mock_settings.skills_dir = tmp_skills_dir

        with patch("app.core.skill_loader.settings", mock_settings):
            result = delete_skill("with-variants")
        assert result is True
        assert not skill_dir.exists()


# ---------------------------------------------------------------------------
# DEEPER TESTS — Cache behavior
# ---------------------------------------------------------------------------


class TestCacheBehaviorDeeper:
    def test_load_skill_cache_invalidates_on_mtime_change(self, tmp_skills_dir, mock_settings):
        import time
        skill_dir = tmp_skills_dir / "mtime-test"
        skill_dir.mkdir()
        skill_file = skill_dir / "skill.md"
        skill_file.write_text("---\nmodel_tier: sonnet\n---\n# Version 1")
        mock_settings.skills_dir = tmp_skills_dir

        _skill_cache.clear()
        with patch("app.core.skill_loader.settings", mock_settings):
            body1 = load_skill("mtime-test")
            assert body1 == "# Version 1"

            # Simulate file modification with different mtime
            time.sleep(0.05)
            skill_file.write_text("---\nmodel_tier: opus\n---\n# Version 2")

            body2 = load_skill("mtime-test")
            assert body2 == "# Version 2"

    def test_load_skill_config_cache_hit(self, tmp_skills_dir, sample_skill_content, mock_settings):
        skill_dir = tmp_skills_dir / "cfg-cache"
        skill_dir.mkdir()
        (skill_dir / "skill.md").write_text(sample_skill_content)
        mock_settings.skills_dir = tmp_skills_dir

        _skill_cache.clear()
        with patch("app.core.skill_loader.settings", mock_settings):
            config1 = load_skill_config("cfg-cache")
            config2 = load_skill_config("cfg-cache")
        assert config1 == config2
        assert config1["model_tier"] == "sonnet"

    def test_load_skill_config_cache_invalidates_on_mtime(self, tmp_skills_dir, mock_settings):
        import time
        skill_dir = tmp_skills_dir / "cfg-mtime"
        skill_dir.mkdir()
        skill_file = skill_dir / "skill.md"
        skill_file.write_text("---\nmodel_tier: sonnet\n---\n# Body")
        mock_settings.skills_dir = tmp_skills_dir

        _skill_cache.clear()
        with patch("app.core.skill_loader.settings", mock_settings):
            config1 = load_skill_config("cfg-mtime")
            assert config1["model_tier"] == "sonnet"

            time.sleep(0.05)
            skill_file.write_text("---\nmodel_tier: opus\n---\n# Body v2")

            config2 = load_skill_config("cfg-mtime")
            assert config2["model_tier"] == "opus"

    def test_load_skill_populates_cache_entry(self, tmp_skills_dir, sample_skill_content, mock_settings):
        skill_dir = tmp_skills_dir / "cache-entry"
        skill_dir.mkdir()
        (skill_dir / "skill.md").write_text(sample_skill_content)
        mock_settings.skills_dir = tmp_skills_dir

        _skill_cache.clear()
        with patch("app.core.skill_loader.settings", mock_settings):
            load_skill("cache-entry")
        assert "cache-entry" in _skill_cache
        mtime, fm, body = _skill_cache["cache-entry"]
        assert isinstance(mtime, float)
        assert isinstance(fm, dict)
        assert "# Test Skill" in body

    def test_load_skill_and_config_share_cache(self, tmp_skills_dir, sample_skill_content, mock_settings):
        """load_skill and load_skill_config use the same _skill_cache."""
        skill_dir = tmp_skills_dir / "shared-cache"
        skill_dir.mkdir()
        (skill_dir / "skill.md").write_text(sample_skill_content)
        mock_settings.skills_dir = tmp_skills_dir

        _skill_cache.clear()
        with patch("app.core.skill_loader.settings", mock_settings):
            body = load_skill("shared-cache")
            config = load_skill_config("shared-cache")
        assert body is not None
        assert config["model_tier"] == "sonnet"
        # Only one cache entry for both calls
        assert "shared-cache" in _skill_cache


# ---------------------------------------------------------------------------
# DEEPER TESTS — parse_context_refs edge cases
# ---------------------------------------------------------------------------


class TestParseContextRefsDeeper:
    def test_00_foundation_prefix(self):
        content = "- 00_foundation/base.md"
        refs = parse_context_refs(content)
        assert refs == ["00_foundation/base.md"]

    def test_mixed_bullet_types(self):
        content = "- knowledge_base/a.md\n* knowledge_base/b.md\n- clients/c.md"
        refs = parse_context_refs(content)
        assert refs == ["knowledge_base/a.md", "knowledge_base/b.md", "clients/c.md"]

    def test_indented_lines_not_matched(self):
        content = "  - knowledge_base/indented.md"
        refs = parse_context_refs(content)
        assert refs == []

    def test_inline_text_after_ref(self):
        """Only the path part is captured, not trailing text."""
        content = "- knowledge_base/file.md some extra text"
        refs = parse_context_refs(content)
        # \S+ captures up to the first whitespace
        assert refs == ["knowledge_base/file.md"]

    def test_no_space_after_bullet_not_matched(self):
        content = "-knowledge_base/no-space.md"
        refs = parse_context_refs(content)
        assert refs == []

    def test_multiple_refs_with_other_lines(self):
        content = """# Context Files
- knowledge_base/voice/default.md
- clients/{{client_slug}}.md

## Rules
Some text here.
- knowledge_base/frameworks/sales.md
"""
        refs = parse_context_refs(content)
        assert len(refs) == 3
        assert "knowledge_base/voice/default.md" in refs
        assert "clients/{{client_slug}}.md" in refs
        assert "knowledge_base/frameworks/sales.md" in refs


# ---------------------------------------------------------------------------
# DEEPER TESTS — resolve_template_vars edge cases
# ---------------------------------------------------------------------------


class TestResolveTemplateVarsDeeper:
    def test_both_slugs_in_same_path(self, mock_settings):
        with patch("app.core.skill_loader.settings", mock_settings):
            result = resolve_template_vars(
                "knowledge_base/{{client_slug}}/{{persona_slug}}.md",
                {"client_slug": "acme", "persona_slug": "dan"},
            )
        assert result == "knowledge_base/acme/dan.md"

    def test_empty_string_value_keeps_placeholder(self, mock_settings):
        """Empty string value for a var means the var isn't resolved."""
        with patch("app.core.skill_loader.settings", mock_settings):
            result = resolve_template_vars("clients/{{client_slug}}.md", {"client_slug": ""})
        assert "{{client_slug}}" in result

    def test_non_client_path_no_profile_redirect(self, mock_settings):
        with patch("app.core.skill_loader.settings", mock_settings):
            result = resolve_template_vars("knowledge_base/test.md", {})
        assert result == "knowledge_base/test.md"

    def test_unknown_var_ignored(self, mock_settings):
        """Only client_slug and persona_slug are resolved."""
        with patch("app.core.skill_loader.settings", mock_settings):
            result = resolve_template_vars("path/{{unknown_var}}.md", {})
        assert result == "path/{{unknown_var}}.md"


# ---------------------------------------------------------------------------
# DEEPER TESTS — load_context_files edge cases
# ---------------------------------------------------------------------------


class TestLoadContextFilesDeeper:
    def test_no_defaults_dir(self, tmp_path, mock_settings):
        """No _defaults directory — should not fail."""
        with patch("app.core.skill_loader.settings", mock_settings):
            files = load_context_files("# Body", {})
        assert isinstance(files, list)

    def test_empty_frontmatter_context_falls_back_to_regex(self, tmp_path, mock_settings):
        """When frontmatter context is empty list, falls back to regex."""
        kb_dir = tmp_path / "knowledge_base" / "voice"
        kb_dir.mkdir(parents=True)
        (kb_dir / "default.md").write_text("# Voice")

        skill_content = "---\ncontext: []\n---\n- knowledge_base/voice/default.md"
        skill_dir = tmp_path / "skills" / "regex-fallback"
        skill_dir.mkdir(parents=True)
        (skill_dir / "skill.md").write_text(skill_content)

        _skill_cache.clear()
        with patch("app.core.skill_loader.settings", mock_settings):
            files = load_context_files(skill_content, {}, skill_name="regex-fallback")
        paths = [f["path"] for f in files]
        assert "knowledge_base/voice/default.md" in paths

    def test_industry_special_chars_normalized(self, tmp_path, mock_settings):
        industries_dir = tmp_path / "knowledge_base" / "industries"
        industries_dir.mkdir(parents=True)
        (industries_dir / "e-commerce.md").write_text("# E-Commerce")

        with patch("app.core.skill_loader.settings", mock_settings):
            files = load_context_files("# Body", {"industry": "E-Commerce"})
        paths = [f["path"] for f in files]
        assert "knowledge_base/industries/e-commerce.md" in paths

    def test_empty_industry_string_no_autoload(self, tmp_path, mock_settings):
        """Empty string industry should not trigger autoload."""
        industries_dir = tmp_path / "knowledge_base" / "industries"
        industries_dir.mkdir(parents=True)
        (industries_dir / ".md").write_text("# Bad")

        with patch("app.core.skill_loader.settings", mock_settings):
            files = load_context_files("# Body", {"industry": ""})
        paths = [f["path"] for f in files]
        assert not any("industries" in p for p in paths)

    def test_industry_dir_missing_no_error(self, tmp_path, mock_settings):
        """No industries directory — should not fail."""
        with patch("app.core.skill_loader.settings", mock_settings):
            files = load_context_files("# Body", {"industry": "SaaS"})
        assert isinstance(files, list)

    def test_context_files_include_content(self, tmp_path, mock_settings):
        """Each returned file dict should have both path and content."""
        kb_dir = tmp_path / "knowledge_base" / "voice"
        kb_dir.mkdir(parents=True)
        (kb_dir / "default.md").write_text("Voice content here")

        content = "- knowledge_base/voice/default.md"
        with patch("app.core.skill_loader.settings", mock_settings):
            files = load_context_files(content, {})
        assert len(files) == 1
        assert files[0]["path"] == "knowledge_base/voice/default.md"
        assert files[0]["content"] == "Voice content here"


# ---------------------------------------------------------------------------
# DEEPER TESTS — list_skills edge cases
# ---------------------------------------------------------------------------


class TestListSkillsDeeper:
    def test_ignores_files_in_skills_dir(self, tmp_skills_dir, mock_settings):
        """Files (not dirs) in skills_dir are ignored."""
        (tmp_skills_dir / "readme.md").write_text("# README")
        (tmp_skills_dir / "valid-skill").mkdir()
        (tmp_skills_dir / "valid-skill" / "skill.md").write_text("# Skill")
        mock_settings.skills_dir = tmp_skills_dir

        with patch("app.core.skill_loader.settings", mock_settings):
            skills = list_skills()
        assert skills == ["valid-skill"]

    def test_sorted_alphabetically(self, tmp_skills_dir, mock_settings):
        for name in ["zebra", "alpha", "middle"]:
            d = tmp_skills_dir / name
            d.mkdir()
            (d / "skill.md").write_text(f"# {name}")
        mock_settings.skills_dir = tmp_skills_dir

        with patch("app.core.skill_loader.settings", mock_settings):
            skills = list_skills()
        assert skills == ["alpha", "middle", "zebra"]


# ---------------------------------------------------------------------------
# DEEPER TESTS — load_skill_variant edge cases
# ---------------------------------------------------------------------------


class TestLoadSkillVariantDeeper:
    def test_variant_returns_raw_content(self, tmp_skills_dir, mock_settings):
        """Variant files are returned as-is, not frontmatter-stripped."""
        skill_dir = tmp_skills_dir / "my-skill"
        variants_dir = skill_dir / "variants"
        variants_dir.mkdir(parents=True)
        (variants_dir / "v1.md").write_text("---\nmodel_tier: opus\n---\n# Variant Body")
        mock_settings.skills_dir = tmp_skills_dir

        with patch("app.core.skill_loader.settings", mock_settings):
            body = load_skill_variant("my-skill", "v1")
        # Variant is read raw, not parsed
        assert body.startswith("---")
        assert "model_tier: opus" in body

    def test_missing_skill_dir_returns_none(self, tmp_skills_dir, mock_settings):
        mock_settings.skills_dir = tmp_skills_dir

        with patch("app.core.skill_loader.settings", mock_settings):
            assert load_skill_variant("no-such-skill", "v1") is None
