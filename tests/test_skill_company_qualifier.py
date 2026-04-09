"""Tests for the company-qualifier skill."""

from pathlib import Path

import pytest
import yaml


SKILL_PATH = Path(__file__).resolve().parent.parent / "skills" / "company-qualifier" / "skill.md"
CLIENT_PATH = Path(__file__).resolve().parent.parent / "clients" / "hologram.md"


def _load_frontmatter(path: Path) -> dict:
    """Extract YAML frontmatter from a markdown file."""
    text = path.read_text()
    assert text.startswith("---"), f"{path} must start with YAML frontmatter"
    end = text.index("---", 3)
    return yaml.safe_load(text[3:end])


class TestSkillFileExists:
    def test_skill_md_exists(self):
        assert SKILL_PATH.exists(), "skills/company-qualifier/skill.md must exist"

    def test_client_profile_exists(self):
        assert CLIENT_PATH.exists(), "clients/hologram.md must exist"


class TestSkillFrontmatter:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.fm = _load_frontmatter(SKILL_PATH)

    def test_model_tier(self):
        assert self.fm["model_tier"] == "standard"

    def test_scope(self):
        assert self.fm["scope"] == "company"

    def test_skip_defaults(self):
        assert self.fm["skip_defaults"] is True

    def test_semantic_context_disabled(self):
        assert self.fm["semantic_context"] is False

    def test_context_includes_client(self):
        ctx = self.fm.get("context", [])
        assert any("clients/{{client_slug}}.md" in c for c in ctx)


class TestSkillContent:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.content = SKILL_PATH.read_text()

    def test_has_role_section(self):
        assert "## Role" in self.content

    def test_has_output_format(self):
        assert "## Output Format" in self.content

    def test_has_qualified_field(self):
        assert '"qualified"' in self.content

    def test_has_examples(self):
        assert "## Examples" in self.content

    def test_output_keys_present(self):
        for key in [
            "qualified",
            "archetype",
            "hardware_evidence",
            "connectivity_evidence",
            "deployment_signals",
            "matched_categories",
            "disqualification_reason",
            "reasoning",
            "confidence_score",
        ]:
            assert f'"{key}"' in self.content, f"Output key '{key}' missing from skill.md"


class TestContextFilter:
    def test_skill_in_client_sections(self):
        from app.core.context_filter import SKILL_CLIENT_SECTIONS

        assert "company-qualifier" in SKILL_CLIENT_SECTIONS
        sections = SKILL_CLIENT_SECTIONS["company-qualifier"]
        assert "What They Sell" in sections
        assert "Target ICP" in sections
        assert "Qualification Criteria" in sections
        assert "Competitive Landscape" in sections


class TestSerperConfig:
    def test_serper_settings_exist(self):
        from app.config import Settings

        s = Settings()
        assert hasattr(s, "serper_api_key")
        assert hasattr(s, "serper_base_url")
        assert hasattr(s, "serper_timeout")
        assert s.serper_base_url == "https://google.serper.dev"
        assert s.serper_timeout == 15


class TestClientProfile:
    @pytest.fixture(autouse=True)
    def _load(self):
        self.content = CLIENT_PATH.read_text()

    def test_has_what_they_sell(self):
        assert "## What They Sell" in self.content

    def test_has_target_icp(self):
        assert "## Target ICP" in self.content

    def test_has_qualification_criteria(self):
        assert "## Qualification Criteria" in self.content

    def test_has_competitive_landscape(self):
        assert "## Competitive Landscape" in self.content

    def test_mentions_hologram(self):
        assert "Hologram" in self.content or "hologram" in self.content
