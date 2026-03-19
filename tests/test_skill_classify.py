"""Tests for the classify skill.

Verifies skill structure, frontmatter, output schema, and integration
with skill_loader and model_router.
"""

from pathlib import Path

from app.core.model_router import resolve_model
from app.core.skill_loader import list_skills, parse_frontmatter

# Resolve the real skill file relative to the test directory
SKILL_FILE = Path(__file__).parent.parent / "skills" / "classify" / "skill.md"


class TestClassifySkill:
    """Verify the classify skill structure and contract."""

    # -- Existence --

    def test_skill_file_exists(self):
        """skills/classify/skill.md must exist on disk."""
        assert SKILL_FILE.exists(), f"Expected skill file at {SKILL_FILE}"

    # -- Frontmatter --

    def test_frontmatter_parses(self):
        """Frontmatter is valid YAML with expected keys."""
        content = SKILL_FILE.read_text()
        fm, body = parse_frontmatter(content)
        assert isinstance(fm, dict)
        assert len(fm) > 0, "Frontmatter should not be empty"
        assert "model_tier" in fm

    def test_model_tier_is_light(self):
        """Frontmatter model_tier equals 'light'."""
        content = SKILL_FILE.read_text()
        fm, _ = parse_frontmatter(content)
        assert fm["model_tier"] == "light"

    def test_skip_defaults_is_true(self):
        """Frontmatter skip_defaults equals True."""
        content = SKILL_FILE.read_text()
        fm, _ = parse_frontmatter(content)
        assert fm.get("skip_defaults") is True

    def test_semantic_context_is_false(self):
        """Frontmatter semantic_context equals False."""
        content = SKILL_FILE.read_text()
        fm, _ = parse_frontmatter(content)
        assert fm.get("semantic_context") is False

    def test_no_context_refs(self):
        """Frontmatter has no 'context' key -- classify does not load client profiles."""
        content = SKILL_FILE.read_text()
        fm, _ = parse_frontmatter(content)
        assert "context" not in fm, "classify should not have a context key in frontmatter"

    # -- Output Schema --

    def test_output_schema_has_title_fields(self):
        """Body contains title_original, title_normalized, and title_confidence."""
        content = SKILL_FILE.read_text()
        _, body = parse_frontmatter(content)
        assert "title_original" in body
        assert "title_normalized" in body
        assert "title_confidence" in body

    def test_output_schema_has_industry_fields(self):
        """Body contains industry_original, industry_normalized, and industry_confidence."""
        content = SKILL_FILE.read_text()
        _, body = parse_frontmatter(content)
        assert "industry_original" in body
        assert "industry_normalized" in body
        assert "industry_confidence" in body

    def test_output_schema_has_overall_confidence(self):
        """Body contains confidence_score."""
        content = SKILL_FILE.read_text()
        _, body = parse_frontmatter(content)
        assert "confidence_score" in body

    # -- Seniority Taxonomy --

    def test_seniority_levels_defined(self):
        """Body contains all exact seniority enum values."""
        content = SKILL_FILE.read_text()
        _, body = parse_frontmatter(content)
        for level in ("IC", "Manager", "Director", "VP", "C-Suite", "Unknown"):
            assert level in body, f"Missing seniority level: {level}"

    # -- Integration --

    def test_model_router_resolves_light_to_haiku(self):
        """resolve_model with skill_config model_tier: light returns 'haiku'."""
        result = resolve_model(skill_config={"model_tier": "light"})
        assert result == "haiku"

    def test_skill_in_list(self):
        """classify appears in list_skills() output (auto-discovery)."""
        skills = list_skills()
        assert "classify" in skills, f"classify not found in skills: {skills}"
