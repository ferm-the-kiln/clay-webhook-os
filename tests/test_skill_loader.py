from unittest.mock import patch

from app.core.skill_loader import (
    _skill_cache,
    list_skills,
    load_context_files,
    load_file,
    load_skill,
    load_skill_config,
    load_skill_variant,
    parse_context_refs,
    parse_frontmatter,
    resolve_template_vars,
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
# context_max_chars truncation
# ---------------------------------------------------------------------------


class TestContextMaxChars:
    def test_truncates_long_context_files(self, tmp_path, mock_settings):
        """When context_max_chars is set in frontmatter, long files get truncated."""
        # Create a skill with context_max_chars
        skill_dir = tmp_path / "skills" / "truncated-skill"
        skill_dir.mkdir(parents=True)
        skill_content = (
            "---\nmodel_tier: sonnet\ncontext:\n"
            "  - knowledge_base/big.md\ncontext_max_chars: 100\n---\n# Skill"
        )
        (skill_dir / "skill.md").write_text(skill_content)

        # Create the context file (bigger than 100 chars)
        kb_dir = tmp_path / "knowledge_base"
        kb_dir.mkdir(parents=True)
        (kb_dir / "big.md").write_text("A" * 500)

        mock_settings.skills_dir = tmp_path / "skills"
        _skill_cache.clear()
        with patch("app.core.skill_loader.settings", mock_settings):
            files = load_context_files(skill_content, {}, skill_name="truncated-skill")

        big_file = [f for f in files if f["path"] == "knowledge_base/big.md"]
        assert len(big_file) == 1
        content = big_file[0]["content"]
        assert len(content) < 500
        assert content.startswith("A" * 100)
        assert "[...truncated]" in content

    def test_no_truncation_when_under_limit(self, tmp_path, mock_settings):
        """Files under the limit are not truncated."""
        skill_dir = tmp_path / "skills" / "short-skill"
        skill_dir.mkdir(parents=True)
        skill_content = (
            "---\nmodel_tier: sonnet\ncontext:\n"
            "  - knowledge_base/short.md\ncontext_max_chars: 1000\n---\n# Skill"
        )
        (skill_dir / "skill.md").write_text(skill_content)

        kb_dir = tmp_path / "knowledge_base"
        kb_dir.mkdir(parents=True)
        (kb_dir / "short.md").write_text("Short content")

        mock_settings.skills_dir = tmp_path / "skills"
        _skill_cache.clear()
        with patch("app.core.skill_loader.settings", mock_settings):
            files = load_context_files(skill_content, {}, skill_name="short-skill")

        short_file = [f for f in files if f["path"] == "knowledge_base/short.md"]
        assert len(short_file) == 1
        assert short_file[0]["content"] == "Short content"

    def test_no_truncation_without_setting(self, tmp_path, mock_settings):
        """Without context_max_chars, no truncation happens."""
        skill_dir = tmp_path / "skills" / "normal-skill"
        skill_dir.mkdir(parents=True)
        skill_content = (
            "---\nmodel_tier: sonnet\ncontext:\n"
            "  - knowledge_base/big.md\n---\n# Skill"
        )
        (skill_dir / "skill.md").write_text(skill_content)

        kb_dir = tmp_path / "knowledge_base"
        kb_dir.mkdir(parents=True)
        (kb_dir / "big.md").write_text("B" * 10000)

        mock_settings.skills_dir = tmp_path / "skills"
        _skill_cache.clear()
        with patch("app.core.skill_loader.settings", mock_settings):
            files = load_context_files(skill_content, {}, skill_name="normal-skill")

        big_file = [f for f in files if f["path"] == "knowledge_base/big.md"]
        assert len(big_file) == 1
        assert big_file[0]["content"] == "B" * 10000
