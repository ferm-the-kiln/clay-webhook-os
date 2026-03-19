import textwrap
from pathlib import Path

import pytest

from app.config import Settings


@pytest.fixture
def tmp_skills_dir(tmp_path: Path) -> Path:
    """Create a temporary skills directory with a sample skill."""
    skills = tmp_path / "skills"
    skills.mkdir()
    return skills


@pytest.fixture
def sample_skill_content() -> str:
    return textwrap.dedent("""\
        ---
        model_tier: sonnet
        context:
          - knowledge_base/frameworks/sales.md
          - clients/{{client_slug}}.md
        ---
        # Test Skill

        You are a test assistant.

        ## Context Files to Load
        - knowledge_base/frameworks/sales.md
        - clients/{{client_slug}}.md

        ## Output Format
        Return JSON with keys: result, confidence_score
    """)


@pytest.fixture
def sample_skill_no_frontmatter() -> str:
    return textwrap.dedent("""\
        # Simple Skill

        Do the thing.

        ## Context Files to Load
        - knowledge_base/voice/default.md
    """)


@pytest.fixture
def mock_settings(tmp_path: Path) -> Settings:
    """Settings object pointing at tmp directories."""
    return Settings(
        base_dir=tmp_path,
        skills_dir=tmp_path / "skills",
        knowledge_dir=tmp_path / "knowledge_base",
        clients_dir=tmp_path / "clients",
        data_dir=tmp_path / "data",
        webhook_api_key="test-key",
        enable_smart_routing=False,
    )


@pytest.fixture
def sample_data() -> dict:
    return {
        "company_name": "Acme Corp",
        "person_name": "Jane Doe",
        "title": "VP of Sales",
        "client_slug": "acme",
        "industry": "saas",
    }
