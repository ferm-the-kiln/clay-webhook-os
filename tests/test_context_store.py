import textwrap
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.core.context_store import ContextStore
from app.models.context import (
    CompanyInfo,
    CreateClientRequest,
    TonePreferences,
    UpdateClientRequest,
)


SAMPLE_CLIENT_MD = textwrap.dedent("""\
    # Acme Corp

    ## Company
    - **Domain:** acme.com
    - **Industry:** SaaS
    - **Size:** 50-200
    - **Stage:** Series B

    ## What They Sell

    AI-powered widgets for enterprise.

    ## Target ICP

    VP Engineering at mid-market companies.

    ## Tone Preferences
    - **Formality:** Professional
    - **Approach:** Consultative
    - **Things to avoid:** Hype words
""")


@pytest.fixture
def store(tmp_path: Path) -> ContextStore:
    clients = tmp_path / "clients"
    kb = tmp_path / "knowledge_base"
    skills = tmp_path / "skills"
    clients.mkdir()
    kb.mkdir()
    skills.mkdir()
    return ContextStore(clients_dir=clients, knowledge_dir=kb, skills_dir=skills)


@pytest.fixture
def store_with_client(store: ContextStore, tmp_path: Path) -> ContextStore:
    client_dir = tmp_path / "clients" / "acme"
    client_dir.mkdir(parents=True)
    (client_dir / "profile.md").write_text(SAMPLE_CLIENT_MD)
    return store


# ---------------------------------------------------------------------------
# Client CRUD
# ---------------------------------------------------------------------------


class TestListClients:
    def test_empty(self, store):
        assert store.list_clients() == []

    def test_list_structured_clients(self, store_with_client):
        clients = store_with_client.list_clients()
        assert len(clients) == 1
        assert clients[0].slug == "acme"
        assert clients[0].name == "Acme Corp"
        assert clients[0].industry == "SaaS"

    def test_list_flat_file_clients(self, store, tmp_path):
        (tmp_path / "clients" / "beta.md").write_text("# Beta Inc\n\n## Company\n- **Industry:** Fintech\n")
        clients = store.list_clients()
        assert len(clients) == 1
        assert clients[0].slug == "beta"

    def test_skips_underscore_dirs(self, store, tmp_path):
        (tmp_path / "clients" / "_templates").mkdir()
        assert store.list_clients() == []

    def test_nonexistent_dir(self, tmp_path):
        s = ContextStore(
            clients_dir=tmp_path / "nope",
            knowledge_dir=tmp_path / "kb",
            skills_dir=tmp_path / "sk",
        )
        assert s.list_clients() == []


class TestGetClient:
    def test_get_structured(self, store_with_client):
        client = store_with_client.get_client("acme")
        assert client is not None
        assert client.name == "Acme Corp"
        assert client.company.domain == "acme.com"
        assert client.company.industry == "SaaS"
        assert client.company.stage == "Series B"
        assert "AI-powered widgets" in client.what_they_sell
        assert "VP Engineering" in client.icp

    def test_get_flat_file(self, store, tmp_path):
        (tmp_path / "clients" / "flat.md").write_text("# Flat Co\n")
        client = store.get_client("flat")
        assert client is not None
        assert client.name == "Flat Co"

    def test_get_nonexistent(self, store):
        assert store.get_client("nope") is None


class TestCreateClient:
    def test_create_writes_file(self, store, tmp_path):
        req = CreateClientRequest(
            slug="newco",
            name="New Company",
            company=CompanyInfo(domain="new.co", industry="AI"),
            what_they_sell="Cool stuff",
        )
        profile = store.create_client(req)
        assert profile.slug == "newco"
        assert profile.name == "New Company"
        # File should exist
        f = tmp_path / "clients" / "newco" / "profile.md"
        assert f.exists()
        assert "# New Company" in f.read_text()

    def test_create_roundtrip(self, store):
        req = CreateClientRequest(
            slug="rt",
            name="Roundtrip Inc",
            company=CompanyInfo(domain="rt.com", industry="SaaS", size="100"),
            tone=TonePreferences(formality="Casual", approach="Direct"),
            what_they_sell="Things",
            icp="CTOs",
        )
        store.create_client(req)
        loaded = store.get_client("rt")
        assert loaded is not None
        assert loaded.name == "Roundtrip Inc"
        assert loaded.company.domain == "rt.com"
        assert loaded.tone.formality == "Casual"


class TestUpdateClient:
    def test_update_existing(self, store_with_client):
        updated = store_with_client.update_client("acme", UpdateClientRequest(name="Acme 2.0"))
        assert updated is not None
        assert updated.name == "Acme 2.0"
        # Verify persisted
        reloaded = store_with_client.get_client("acme")
        assert reloaded.name == "Acme 2.0"

    def test_update_nonexistent(self, store):
        assert store.update_client("nope", UpdateClientRequest(name="X")) is None


class TestDeleteClient:
    def test_delete_structured(self, store_with_client, tmp_path):
        assert store_with_client.delete_client("acme") is True
        assert not (tmp_path / "clients" / "acme").exists()

    def test_delete_flat(self, store, tmp_path):
        (tmp_path / "clients" / "flat.md").write_text("# Flat\n")
        assert store.delete_client("flat") is True
        assert not (tmp_path / "clients" / "flat.md").exists()

    def test_delete_nonexistent(self, store):
        assert store.delete_client("nope") is False


# ---------------------------------------------------------------------------
# Knowledge Base CRUD
# ---------------------------------------------------------------------------


class TestKnowledgeBase:
    def test_list_empty(self, store):
        assert store.list_knowledge_base() == []

    def test_list_files(self, store, tmp_path):
        fw = tmp_path / "knowledge_base" / "frameworks"
        fw.mkdir()
        (fw / "sales.md").write_text("# Sales Framework")
        files = store.list_knowledge_base()
        assert len(files) == 1
        assert files[0].category == "frameworks"
        assert files[0].name == "sales"

    def test_get_knowledge_file(self, store, tmp_path):
        fw = tmp_path / "knowledge_base" / "voice"
        fw.mkdir()
        (fw / "default.md").write_text("Be direct.")
        f = store.get_knowledge_file("voice", "default.md")
        assert f is not None
        assert f.content == "Be direct."

    def test_get_nonexistent(self, store):
        assert store.get_knowledge_file("nope", "nope.md") is None

    def test_update_knowledge_file(self, store, tmp_path):
        fw = tmp_path / "knowledge_base" / "voice"
        fw.mkdir()
        (fw / "default.md").write_text("Old content")
        result = store.update_knowledge_file("voice", "default.md", "New content")
        assert result is not None
        assert result.content == "New content"
        assert (fw / "default.md").read_text() == "New content"

    def test_update_nonexistent(self, store):
        assert store.update_knowledge_file("nope", "nope.md", "X") is None


class TestCreateKnowledgeFile:
    def test_create_new(self, store, tmp_path):
        f = store.create_knowledge_file("frameworks", "new-framework.md", "# New")
        assert f.category == "frameworks"
        assert (tmp_path / "knowledge_base" / "frameworks" / "new-framework.md").exists()

    def test_create_adds_md_extension(self, store):
        f = store.create_knowledge_file("voice", "style", "Content")
        assert f.path == "voice/style.md"

    def test_create_slugifies_category(self, store):
        f = store.create_knowledge_file("My Category!", "file.md", "X")
        assert f.category == "my-category"

    def test_create_existing_raises(self, store, tmp_path):
        fw = tmp_path / "knowledge_base" / "voice"
        fw.mkdir()
        (fw / "exists.md").write_text("X")
        with pytest.raises(ValueError, match="already exists"):
            store.create_knowledge_file("voice", "exists.md", "Y")

    def test_path_traversal_blocked(self, store):
        with pytest.raises(ValueError, match="Invalid path"):
            store.create_knowledge_file("..", "evil.md", "X")
        with pytest.raises(ValueError, match="Invalid path"):
            store.create_knowledge_file("ok", "../evil.md", "X")
        with pytest.raises(ValueError, match="Invalid path"):
            store.create_knowledge_file("ok/sub", "file.md", "X")


class TestDeleteKnowledgeFile:
    def test_delete_existing(self, store, tmp_path):
        fw = tmp_path / "knowledge_base" / "frameworks"
        fw.mkdir()
        (fw / "del.md").write_text("X")
        assert store.delete_knowledge_file("frameworks", "del.md") is True
        assert not (fw / "del.md").exists()

    def test_delete_removes_empty_dir(self, store, tmp_path):
        fw = tmp_path / "knowledge_base" / "empty-cat"
        fw.mkdir()
        (fw / "only.md").write_text("X")
        store.delete_knowledge_file("empty-cat", "only.md")
        assert not fw.exists()

    def test_delete_nonexistent(self, store):
        assert store.delete_knowledge_file("nope", "nope.md") is False

    def test_delete_path_traversal_blocked(self, store):
        with pytest.raises(ValueError, match="Invalid path"):
            store.delete_knowledge_file("..", "file.md")


class TestListCategories:
    def test_list_categories(self, store, tmp_path):
        (tmp_path / "knowledge_base" / "frameworks").mkdir()
        (tmp_path / "knowledge_base" / "voice").mkdir()
        cats = store.list_categories()
        assert cats == ["frameworks", "voice"]

    def test_empty(self, store):
        assert store.list_categories() == []


# ---------------------------------------------------------------------------
# Markdown parsing internals
# ---------------------------------------------------------------------------


class TestMarkdownParsing:
    def test_split_sections(self, store):
        content = "# Title\n\n## Section A\nContent A\n\n## Section B\nContent B"
        sections = store._split_sections(content)
        assert "Section A" in sections
        assert "Content A" in sections["Section A"]
        assert "Section B" in sections

    def test_extract_bullet(self, store):
        text = "- **Domain:** acme.com\n- **Industry:** SaaS"
        assert store._extract_bullet(text, "Domain") == "acme.com"
        assert store._extract_bullet(text, "Industry") == "SaaS"
        assert store._extract_bullet(text, "Missing") == ""

    def test_extract_bullet_dash_value(self, store):
        text = "- **Size:** —"
        assert store._extract_bullet(text, "Size") == ""

    def test_parse_tone_preferences(self, store_with_client):
        client = store_with_client.get_client("acme")
        assert client.tone.formality == "Professional"
        assert client.tone.approach == "Consultative"
        assert client.tone.avoid == "Hype words"

    def test_name_from_h1(self, store):
        profile = store._parse_client_markdown("test", "# My Custom Name\n\nBody")
        assert profile.name == "My Custom Name"

    def test_name_fallback_to_slug(self, store):
        profile = store._parse_client_markdown("my-company", "No heading here")
        assert profile.name == "My Company"

    def test_render_all_optional_sections(self, store):
        """Render and re-parse a profile with every optional section populated."""
        req = CreateClientRequest(
            slug="full",
            name="Full Profile",
            company=CompanyInfo(domain="full.co", industry="SaaS", size="100", stage="A", hq="NYC", founded="2020"),
            what_they_sell="Everything",
            icp="CTOs",
            competitive_landscape="Lots of competition",
            recent_news="Won an award",
            value_proposition="Best in class",
            tone=TonePreferences(formality="Formal", approach="Consultative", avoid="Jargon"),
            campaign_angles="Angle 1",
            notes="Some notes",
            personas="CTO persona",
            battle_cards="Vs Competitor A",
            signal_playbook="Hiring signals",
            proven_responses="Template X works",
            active_campaigns="Spring 2026",
        )
        profile = store.create_client(req)
        reloaded = store.get_client("full")
        assert reloaded.what_they_sell == "Everything"
        assert reloaded.competitive_landscape == "Lots of competition"
        assert reloaded.recent_news == "Won an award"
        assert reloaded.value_proposition == "Best in class"
        assert reloaded.personas == "CTO persona"
        assert reloaded.battle_cards == "Vs Competitor A"
        assert reloaded.signal_playbook == "Hiring signals"
        assert reloaded.proven_responses == "Template X works"
        assert reloaded.active_campaigns == "Spring 2026"
        assert reloaded.company.hq == "NYC"
        assert reloaded.company.founded == "2020"

    def test_alternative_section_headers(self, store):
        """Parsing handles variant section names from real client files."""
        md = textwrap.dedent("""\
            # Test Co

            ## Target ICP — Who Twelve Labs Sells To

            Engineers at large companies.

            ## Recent News & Signals (good for personalization)

            Raised Series C.

            ## Value Proposition (for outbound on their behalf)

            10x faster video understanding.

            ## Campaign Angles Worth Testing

            Angle A, Angle B.
        """)
        profile = store._parse_client_markdown("test", md)
        assert "Engineers" in profile.icp
        assert "Series C" in profile.recent_news
        assert "10x faster" in profile.value_proposition
        assert "Angle A" in profile.campaign_angles


# ---------------------------------------------------------------------------
# Knowledge Base — additional edge cases
# ---------------------------------------------------------------------------


class TestKnowledgeBaseEdgeCases:
    def test_list_general_category_for_root_files(self, store, tmp_path):
        """Files at the root of knowledge_base get category 'general'."""
        (tmp_path / "knowledge_base" / "guide.md").write_text("# Guide")
        files = store.list_knowledge_base()
        assert len(files) == 1
        assert files[0].category == "general"
        assert files[0].name == "guide"

    def test_list_nonexistent_dir(self, tmp_path):
        s = ContextStore(
            clients_dir=tmp_path / "c",
            knowledge_dir=tmp_path / "nope",
            skills_dir=tmp_path / "s",
        )
        assert s.list_knowledge_base() == []

    def test_list_categories_nonexistent_dir(self, tmp_path):
        s = ContextStore(
            clients_dir=tmp_path / "c",
            knowledge_dir=tmp_path / "nope",
            skills_dir=tmp_path / "s",
        )
        assert s.list_categories() == []

    def test_create_kb_backslash_blocked(self, store):
        with pytest.raises(ValueError, match="Invalid path"):
            store.create_knowledge_file("ok\\sub", "file.md", "X")

    def test_delete_kb_backslash_blocked(self, store):
        with pytest.raises(ValueError, match="Invalid path"):
            store.delete_knowledge_file("ok\\sub", "file.md")

    def test_delete_preserves_nonempty_dir(self, store, tmp_path):
        fw = tmp_path / "knowledge_base" / "keep"
        fw.mkdir()
        (fw / "a.md").write_text("A")
        (fw / "b.md").write_text("B")
        store.delete_knowledge_file("keep", "a.md")
        assert fw.exists()  # Still has b.md


class TestListClientsEdgeCases:
    def test_skips_dir_without_profile(self, store, tmp_path):
        """Directories without profile.md are skipped."""
        (tmp_path / "clients" / "empty-client").mkdir()
        assert store.list_clients() == []

    def test_skips_non_md_files(self, store, tmp_path):
        """Non-.md files in clients dir are ignored."""
        (tmp_path / "clients" / "notes.txt").write_text("random notes")
        assert store.list_clients() == []


# ---------------------------------------------------------------------------
# get_context_usage_map
# ---------------------------------------------------------------------------


class TestGetContextUsageMap:
    @patch("app.core.context_store.parse_context_refs", return_value=["knowledge_base/voice/default.md"])
    @patch("app.core.context_store.load_skill", return_value="# Skill with refs")
    @patch("app.core.context_store.load_skill_config", return_value={"context": []})
    @patch("app.core.context_store.list_skills", return_value=["email-gen"])
    def test_usage_from_skill_content(self, mock_ls, mock_cfg, mock_load, mock_refs, store):
        usage = store.get_context_usage_map()
        assert "knowledge_base/voice/default.md" in usage
        assert "email-gen" in usage["knowledge_base/voice/default.md"]

    @patch("app.core.context_store.load_skill_config", return_value={"context": ["knowledge_base/frameworks/sales.md"]})
    @patch("app.core.context_store.list_skills", return_value=["icp-scorer"])
    def test_usage_from_skill_config(self, mock_ls, mock_cfg, store):
        usage = store.get_context_usage_map()
        assert "knowledge_base/frameworks/sales.md" in usage
        assert "icp-scorer" in usage["knowledge_base/frameworks/sales.md"]

    @patch("app.core.context_store.load_skill_config", return_value={"context": []})
    @patch("app.core.context_store.load_skill", return_value=None)
    @patch("app.core.context_store.list_skills", return_value=["broken"])
    def test_skill_not_found_skipped(self, mock_ls, mock_load, mock_cfg, store):
        usage = store.get_context_usage_map()
        assert usage == {}

    @patch("app.core.context_store.list_skills", return_value=["email-gen"])
    @patch("app.core.context_store.load_skill_config", return_value={"context": []})
    @patch("app.core.context_store.load_skill", return_value="# Skill")
    @patch("app.core.context_store.parse_context_refs", return_value=[])
    def test_defaults_dir_included(self, mock_refs, mock_load, mock_cfg, mock_ls, store, tmp_path):
        defaults = tmp_path / "knowledge_base" / "_defaults"
        defaults.mkdir()
        (defaults / "system.md").write_text("System defaults")
        usage = store.get_context_usage_map()
        assert "knowledge_base/_defaults/system.md" in usage
        assert "email-gen" in usage["knowledge_base/_defaults/system.md"]


# ---------------------------------------------------------------------------
# preview_prompt
# ---------------------------------------------------------------------------


class TestPreviewPrompt:
    @patch("app.core.context_store.build_prompt", return_value="Full assembled prompt here")
    @patch("app.core.context_store.load_context_files", return_value=[{"path": "kb/voice.md"}])
    @patch("app.core.context_store.load_skill", return_value="# Email Gen Skill")
    def test_preview_success(self, mock_load, mock_ctx, mock_build):
        store = ContextStore(
            clients_dir=Path("/tmp/c"),
            knowledge_dir=Path("/tmp/kb"),
            skills_dir=Path("/tmp/sk"),
        )
        result = store.preview_prompt("email-gen", "acme", {"name": "Alice"})
        assert result is not None
        assert result.assembled_prompt == "Full assembled prompt here"
        assert result.context_files_loaded == ["kb/voice.md"]
        assert result.estimated_tokens > 0
        # Verify data passed to build_prompt includes client_slug
        call_data = mock_build.call_args[0][2]
        assert call_data["client_slug"] == "acme"
        assert call_data["name"] == "Alice"

    @patch("app.core.context_store.load_skill", return_value=None)
    def test_preview_skill_not_found(self, mock_load):
        store = ContextStore(
            clients_dir=Path("/tmp/c"),
            knowledge_dir=Path("/tmp/kb"),
            skills_dir=Path("/tmp/sk"),
        )
        assert store.preview_prompt("nope", "acme") is None

    @patch("app.core.context_store.build_prompt", return_value="Prompt")
    @patch("app.core.context_store.load_context_files", return_value=[])
    @patch("app.core.context_store.load_skill", return_value="# Skill")
    def test_preview_no_sample_data(self, mock_load, mock_ctx, mock_build):
        store = ContextStore(
            clients_dir=Path("/tmp/c"),
            knowledge_dir=Path("/tmp/kb"),
            skills_dir=Path("/tmp/sk"),
        )
        result = store.preview_prompt("email-gen", "acme")
        assert result is not None
        call_data = mock_build.call_args[0][2]
        assert call_data == {"client_slug": "acme"}
