import textwrap
from pathlib import Path
from unittest.mock import patch

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
        store.create_client(req)
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


# ---------------------------------------------------------------------------
# _split_sections edge cases
# ---------------------------------------------------------------------------


class TestSplitSectionsEdges:
    def test_empty_content(self, store):
        assert store._split_sections("") == {}

    def test_only_h1_no_h2(self, store):
        assert store._split_sections("# Title\nSome body text") == {}

    def test_consecutive_h2_no_content(self, store):
        sections = store._split_sections("## A\n## B\nContent B")
        assert sections["A"] == ""
        assert "Content B" in sections["B"]

    def test_h3_inside_h2(self, store):
        content = "## Section\n### Subsection\nSub content"
        sections = store._split_sections(content)
        assert "### Subsection" in sections["Section"]
        assert "Sub content" in sections["Section"]

    def test_preserves_multiline_content(self, store):
        content = "## Notes\nLine 1\nLine 2\nLine 3"
        sections = store._split_sections(content)
        assert sections["Notes"] == "Line 1\nLine 2\nLine 3"


# ---------------------------------------------------------------------------
# _extract_bullet edge cases
# ---------------------------------------------------------------------------


class TestExtractBulletEdges:
    def test_asterisk_bullet(self, store):
        text = "* **Domain:** example.com"
        assert store._extract_bullet(text, "Domain") == "example.com"

    def test_case_insensitive(self, store):
        text = "- **domain:** example.com"
        assert store._extract_bullet(text, "Domain") == "example.com"

    def test_multiple_matches_returns_first(self, store):
        text = "- **Domain:** first.com\n- **Domain:** second.com"
        assert store._extract_bullet(text, "Domain") == "first.com"

    def test_extra_whitespace(self, store):
        text = "- **Domain:**   spaced.com  "
        assert store._extract_bullet(text, "Domain") == "spaced.com"


# ---------------------------------------------------------------------------
# _parse_client_markdown edge cases
# ---------------------------------------------------------------------------


class TestParseClientEdges:
    def test_empty_content(self, store):
        profile = store._parse_client_markdown("empty", "")
        assert profile.slug == "empty"
        assert profile.name == "Empty"  # slug fallback
        assert profile.company.domain == ""

    def test_no_sections_just_text(self, store):
        profile = store._parse_client_markdown("test", "Just some plain text")
        assert profile.slug == "test"
        assert profile.what_they_sell == ""

    def test_raw_markdown_set(self, store):
        md = "# Test\n\n## Company\n- **Domain:** test.com"
        profile = store._parse_client_markdown("test", md)
        assert profile.raw_markdown == md

    def test_notes_fallback_to_campaign_notes(self, store):
        md = "# Test\n\n## Campaign Notes\nSome notes here"
        profile = store._parse_client_markdown("test", md)
        assert "Some notes here" in profile.notes


# ---------------------------------------------------------------------------
# _render_client_markdown edge cases
# ---------------------------------------------------------------------------


class TestRenderClientEdges:
    def test_missing_optional_fields_omitted(self, store, tmp_path):
        """Optional sections not rendered when empty."""
        req = CreateClientRequest(
            slug="minimal",
            name="Minimal Co",
            company=CompanyInfo(domain="min.co"),
        )
        profile = store.create_client(req)
        md = profile.raw_markdown
        assert "# Minimal Co" in md
        assert "## Company" in md
        assert "## What They Sell" not in md
        assert "## Target ICP" not in md
        assert "## Competitive Landscape" not in md

    def test_hq_and_founded_conditional(self, store, tmp_path):
        """HQ and Founded only rendered when present."""
        req = CreateClientRequest(
            slug="nohq",
            name="No HQ Co",
            company=CompanyInfo(domain="nohq.co"),
        )
        profile = store.create_client(req)
        assert "**HQ:**" not in profile.raw_markdown
        assert "**Founded:**" not in profile.raw_markdown

        req2 = CreateClientRequest(
            slug="withhq",
            name="With HQ",
            company=CompanyInfo(domain="hq.co", hq="NYC", founded="2020"),
        )
        profile2 = store.create_client(req2)
        assert "**HQ:** NYC" in profile2.raw_markdown
        assert "**Founded:** 2020" in profile2.raw_markdown

    def test_tone_dash_fallback(self, store, tmp_path):
        """Tone fields render as '—' when empty, then parse back as empty string."""
        req = CreateClientRequest(
            slug="notone",
            name="No Tone",
            company=CompanyInfo(),
            tone=TonePreferences(),  # all None
        )
        profile = store.create_client(req)
        assert "**Formality:** —" in profile.raw_markdown
        # Re-parse: '—' should come back as empty string
        reloaded = store.get_client("notone")
        assert reloaded.tone.formality == ""


# ---------------------------------------------------------------------------
# update_client — field preservation
# ---------------------------------------------------------------------------


class TestUpdateClientPreservation:
    def test_partial_update_preserves_other_fields(self, store_with_client):
        """Updating name should not wipe other fields."""
        updated = store_with_client.update_client("acme", UpdateClientRequest(name="Acme v2"))
        assert updated.name == "Acme v2"
        assert updated.company.domain == "acme.com"
        assert updated.company.industry == "SaaS"
        assert "AI-powered widgets" in updated.what_they_sell

    def test_update_string_fields(self, store_with_client):
        """Updating simple string fields works correctly."""
        updated = store_with_client.update_client(
            "acme", UpdateClientRequest(what_they_sell="New products")
        )
        assert "New products" in updated.what_they_sell
        assert updated.company.domain == "acme.com"  # preserved

    def test_update_sets_raw_markdown(self, store_with_client):
        updated = store_with_client.update_client("acme", UpdateClientRequest(notes="New notes"))
        assert updated.raw_markdown is not None
        assert "## Notes" in updated.raw_markdown
        assert "New notes" in updated.raw_markdown

    def test_update_nested_model_bug(self, store_with_client):
        """Known issue: model_dump converts nested Pydantic models to dicts,
        causing _render_client_markdown to fail with AttributeError."""
        new_company = CompanyInfo(domain="newacme.com", industry="AI")
        with pytest.raises(AttributeError, match="domain"):
            store_with_client.update_client("acme", UpdateClientRequest(company=new_company))


# ---------------------------------------------------------------------------
# create_client — raw_markdown and idempotency
# ---------------------------------------------------------------------------


class TestCreateClientEdges:
    def test_create_sets_raw_markdown(self, store):
        req = CreateClientRequest(
            slug="rawtest",
            name="Raw Test",
            company=CompanyInfo(domain="raw.co"),
        )
        profile = store.create_client(req)
        assert profile.raw_markdown is not None
        assert "# Raw Test" in profile.raw_markdown

    def test_create_overwrites_existing(self, store_with_client):
        """Creating a client with same slug overwrites the profile."""
        req = CreateClientRequest(
            slug="acme",
            name="Acme Replaced",
            company=CompanyInfo(domain="replaced.com"),
        )
        profile = store_with_client.create_client(req)
        assert profile.name == "Acme Replaced"
        reloaded = store_with_client.get_client("acme")
        assert reloaded.name == "Acme Replaced"


# ---------------------------------------------------------------------------
# delete_client — structured preferred over flat
# ---------------------------------------------------------------------------


class TestDeleteClientEdges:
    def test_structured_preferred_over_flat(self, store, tmp_path):
        """If both structured dir and flat file exist, delete removes the dir."""
        client_dir = tmp_path / "clients" / "both"
        client_dir.mkdir()
        (client_dir / "profile.md").write_text("# Both\n")
        (tmp_path / "clients" / "both.md").write_text("# Both Flat\n")

        assert store.delete_client("both") is True
        assert not client_dir.exists()
        # Flat file still exists because structured was deleted first
        assert (tmp_path / "clients" / "both.md").exists()


# ---------------------------------------------------------------------------
# list_clients — sorting and mixed types
# ---------------------------------------------------------------------------


class TestListClientsSorting:
    def test_sorted_alphabetically(self, store, tmp_path):
        for name in ("zebra", "alpha", "mid"):
            d = tmp_path / "clients" / name
            d.mkdir()
            (d / "profile.md").write_text(f"# {name.title()}\n\n## Company\n")
        clients = store.list_clients()
        slugs = [c.slug for c in clients]
        assert slugs == ["alpha", "mid", "zebra"]

    def test_mixed_structured_and_flat(self, store, tmp_path):
        d = tmp_path / "clients" / "structured"
        d.mkdir()
        (d / "profile.md").write_text("# Structured\n\n## Company\n")
        (tmp_path / "clients" / "flat.md").write_text("# Flat\n\n## Company\n")
        clients = store.list_clients()
        slugs = [c.slug for c in clients]
        assert "flat" in slugs
        assert "structured" in slugs
        assert len(slugs) == 2


# ---------------------------------------------------------------------------
# get_context_usage_map — edges
# ---------------------------------------------------------------------------


class TestContextUsageMapEdges:
    @patch("app.core.context_store.load_skill_config", return_value={"context": ["kb/shared.md"]})
    @patch("app.core.context_store.list_skills", return_value=["skill-a", "skill-b"])
    def test_multiple_skills_same_ref(self, mock_ls, mock_cfg, store):
        usage = store.get_context_usage_map()
        assert "kb/shared.md" in usage
        assert set(usage["kb/shared.md"]) == {"skill-a", "skill-b"}

    @patch("app.core.context_store.load_skill_config", return_value={"context": None})
    @patch("app.core.context_store.load_skill", return_value="# Skill")
    @patch("app.core.context_store.parse_context_refs", return_value=[])
    @patch("app.core.context_store.list_skills", return_value=["lonely"])
    def test_none_context_falls_through(self, mock_ls, mock_refs, mock_load, mock_cfg, store):
        """context: None in config should fall through to parse_context_refs."""
        store.get_context_usage_map()
        mock_refs.assert_called_once()

    @patch("app.core.context_store.load_skill_config", return_value={"context": []})
    @patch("app.core.context_store.load_skill", return_value="# No refs")
    @patch("app.core.context_store.parse_context_refs", return_value=[])
    @patch("app.core.context_store.list_skills", return_value=["skill-a"])
    def test_no_defaults_dir(self, mock_ls, mock_refs, mock_load, mock_cfg, store):
        """When _defaults dir doesn't exist, no default refs are added."""
        usage = store.get_context_usage_map()
        assert all("_defaults" not in k for k in usage)


# ---------------------------------------------------------------------------
# preview_prompt — estimated tokens
# ---------------------------------------------------------------------------


class TestPreviewPromptEdges:
    @patch("app.core.context_store.build_prompt", return_value="a" * 400)
    @patch("app.core.context_store.load_context_files", return_value=[])
    @patch("app.core.context_store.load_skill", return_value="# Skill")
    def test_estimated_tokens_calculation(self, mock_load, mock_ctx, mock_build):
        store = ContextStore(
            clients_dir=Path("/tmp/c"),
            knowledge_dir=Path("/tmp/kb"),
            skills_dir=Path("/tmp/sk"),
        )
        result = store.preview_prompt("test", "client")
        assert result.estimated_tokens == 100  # 400 // 4

    @patch("app.core.context_store.build_prompt", return_value="short")
    @patch("app.core.context_store.load_context_files", return_value=[
        {"path": "a.md"}, {"path": "b.md"}, {"path": "c.md"},
    ])
    @patch("app.core.context_store.load_skill", return_value="# Skill")
    def test_multiple_context_files_listed(self, mock_load, mock_ctx, mock_build):
        store = ContextStore(
            clients_dir=Path("/tmp/c"),
            knowledge_dir=Path("/tmp/kb"),
            skills_dir=Path("/tmp/sk"),
        )
        result = store.preview_prompt("test", "client")
        assert result.context_files_loaded == ["a.md", "b.md", "c.md"]


# ---------------------------------------------------------------------------
# Knowledge base — create edge cases
# ---------------------------------------------------------------------------


class TestCreateKnowledgeEdges:
    def test_create_filename_with_dots(self, store, tmp_path):
        f = store.create_knowledge_file("voice", "my.special.file.md", "Content")
        assert f.name == "my.special.file"
        assert (tmp_path / "knowledge_base" / "voice" / "my.special.file.md").exists()

    def test_create_category_leading_trailing_special(self, store):
        f = store.create_knowledge_file("---My Cat---", "file.md", "X")
        assert f.category == "my-cat"

    def test_create_category_all_special_chars(self, store):
        f = store.create_knowledge_file("!@#$", "file.md", "X")
        assert f.category == ""  # all stripped

    def test_delete_filename_slash_blocked(self, store):
        with pytest.raises(ValueError, match="Invalid path"):
            store.delete_knowledge_file("cat", "sub/file.md")

    def test_create_filename_slash_blocked(self, store):
        with pytest.raises(ValueError, match="Invalid path"):
            store.create_knowledge_file("cat", "sub/file.md", "X")


# ---------------------------------------------------------------------------
# Deeper: list_knowledge_base — nested, multi-category, content
# ---------------------------------------------------------------------------


class TestListKnowledgeBaseDeeper:
    def test_deeply_nested_files(self, store, tmp_path):
        """Files in subdirectories use the first directory as category."""
        nested = tmp_path / "knowledge_base" / "frameworks" / "sub"
        nested.mkdir(parents=True)
        (nested / "deep.md").write_text("# Deep")
        files = store.list_knowledge_base()
        assert len(files) == 1
        assert files[0].category == "frameworks"
        assert files[0].path == "frameworks/sub/deep.md"

    def test_multiple_categories_sorted(self, store, tmp_path):
        """Files from multiple categories returned sorted by path."""
        for cat in ("voice", "frameworks", "industries"):
            d = tmp_path / "knowledge_base" / cat
            d.mkdir()
            (d / "file.md").write_text(f"# {cat}")
        files = store.list_knowledge_base()
        assert len(files) == 3
        cats = [f.category for f in files]
        assert cats == ["frameworks", "industries", "voice"]

    def test_content_preserved(self, store, tmp_path):
        """File content is fully readable from listing."""
        d = tmp_path / "knowledge_base" / "voice"
        d.mkdir()
        (d / "style.md").write_text("Be concise.\nNo fluff.")
        files = store.list_knowledge_base()
        assert files[0].content == "Be concise.\nNo fluff."

    def test_non_md_files_ignored(self, store, tmp_path):
        """Only .md files appear in listing."""
        d = tmp_path / "knowledge_base" / "misc"
        d.mkdir()
        (d / "notes.md").write_text("# Notes")
        (d / "data.json").write_text("{}")
        (d / "readme.txt").write_text("hi")
        files = store.list_knowledge_base()
        assert len(files) == 1
        assert files[0].name == "notes"


# ---------------------------------------------------------------------------
# Deeper: get_knowledge_file — return fields
# ---------------------------------------------------------------------------


class TestGetKnowledgeFileDeeper:
    def test_returned_fields(self, store, tmp_path):
        """All fields of KnowledgeBaseFile are correctly set."""
        d = tmp_path / "knowledge_base" / "frameworks"
        d.mkdir()
        (d / "bant.md").write_text("# BANT Framework")
        f = store.get_knowledge_file("frameworks", "bant.md")
        assert f.path == "frameworks/bant.md"
        assert f.category == "frameworks"
        assert f.name == "bant"
        assert f.content == "# BANT Framework"

    def test_dotted_filename_stem(self, store, tmp_path):
        """Stem handles filenames with dots correctly."""
        d = tmp_path / "knowledge_base" / "voice"
        d.mkdir()
        (d / "v2.0.md").write_text("Version 2")
        f = store.get_knowledge_file("voice", "v2.0.md")
        assert f.name == "v2.0"


# ---------------------------------------------------------------------------
# Deeper: update_knowledge_file — return fields
# ---------------------------------------------------------------------------


class TestUpdateKnowledgeFileDeeper:
    def test_returned_fields(self, store, tmp_path):
        """update returns a complete KnowledgeBaseFile."""
        d = tmp_path / "knowledge_base" / "voice"
        d.mkdir()
        (d / "style.md").write_text("Old")
        result = store.update_knowledge_file("voice", "style.md", "New content here")
        assert result.path == "voice/style.md"
        assert result.category == "voice"
        assert result.name == "style"
        assert result.content == "New content here"


# ---------------------------------------------------------------------------
# Deeper: list_categories — only dirs, not files
# ---------------------------------------------------------------------------


class TestListCategoriesDeeper:
    def test_ignores_files(self, store, tmp_path):
        """Root files in knowledge_base are not listed as categories."""
        (tmp_path / "knowledge_base" / "root.md").write_text("# Root")
        (tmp_path / "knowledge_base" / "frameworks").mkdir()
        cats = store.list_categories()
        assert cats == ["frameworks"]

    def test_multiple_sorted(self, store, tmp_path):
        """Categories are sorted alphabetically."""
        for name in ("voice", "frameworks", "industries"):
            (tmp_path / "knowledge_base" / name).mkdir()
        cats = store.list_categories()
        assert cats == ["frameworks", "industries", "voice"]


# ---------------------------------------------------------------------------
# Deeper: get_client — preference and raw_markdown
# ---------------------------------------------------------------------------


class TestGetClientDeeper:
    def test_structured_preferred_over_flat(self, store, tmp_path):
        """When both structured dir and flat file exist, structured wins."""
        d = tmp_path / "clients" / "both"
        d.mkdir()
        (d / "profile.md").write_text("# Structured Version\n")
        (tmp_path / "clients" / "both.md").write_text("# Flat Version\n")
        client = store.get_client("both")
        assert client.name == "Structured Version"

    def test_raw_markdown_set_on_get(self, store_with_client):
        """raw_markdown field is populated from loaded content."""
        client = store_with_client.get_client("acme")
        assert client.raw_markdown is not None
        assert "# Acme Corp" in client.raw_markdown

    def test_company_size_parsed(self, store_with_client):
        """Company size is extracted from bullet."""
        client = store_with_client.get_client("acme")
        assert client.company.size == "50-200"


# ---------------------------------------------------------------------------
# Deeper: create_client — directory creation, field persistence
# ---------------------------------------------------------------------------


class TestCreateClientDeeper:
    def test_creates_parent_dir(self, store, tmp_path):
        """create_client creates the client directory if not exists."""
        req = CreateClientRequest(
            slug="brand-new",
            name="Brand New Co",
            company=CompanyInfo(domain="new.co"),
        )
        store.create_client(req)
        assert (tmp_path / "clients" / "brand-new" / "profile.md").exists()

    def test_all_optional_fields_in_file(self, store, tmp_path):
        """All optional sections appear in the written markdown."""
        req = CreateClientRequest(
            slug="full",
            name="Full Co",
            company=CompanyInfo(domain="full.co", industry="AI", hq="NYC", founded="2020"),
            what_they_sell="Products",
            icp="CTOs",
            competitive_landscape="Crowded",
            recent_news="IPO",
            value_proposition="Best",
            tone=TonePreferences(formality="Formal", approach="Direct", avoid="Jargon"),
            campaign_angles="Angle 1",
            notes="Note 1",
            personas="CTO",
            battle_cards="Card 1",
            signal_playbook="Play 1",
            proven_responses="Response 1",
            active_campaigns="Campaign 1",
        )
        store.create_client(req)
        md = (tmp_path / "clients" / "full" / "profile.md").read_text()
        for section in [
            "## What They Sell", "## Target ICP", "## Competitive Landscape",
            "## Recent News", "## Value Proposition", "## Tone Preferences",
            "## Campaign Angles", "## Notes", "## Personas", "## Battle Cards",
            "## Signal Playbook", "## Proven Responses", "## Active Campaigns",
        ]:
            assert section in md

    def test_minimal_client_file(self, store, tmp_path):
        """Minimal client only has Company and Tone sections."""
        req = CreateClientRequest(
            slug="minimal",
            name="Minimal",
            company=CompanyInfo(),
        )
        store.create_client(req)
        md = (tmp_path / "clients" / "minimal" / "profile.md").read_text()
        assert "## Company" in md
        assert "## Tone Preferences" in md
        assert "## What They Sell" not in md


# ---------------------------------------------------------------------------
# Deeper: update_client — field-level updates
# ---------------------------------------------------------------------------


class TestUpdateClientDeeper:
    def test_update_icp(self, store_with_client):
        """Updating icp preserves other fields."""
        updated = store_with_client.update_client(
            "acme", UpdateClientRequest(icp="New ICP target")
        )
        assert "New ICP target" in updated.icp
        assert updated.company.domain == "acme.com"

    def test_update_persists_to_file(self, store_with_client, tmp_path):
        """Updated content is written to disk."""
        store_with_client.update_client(
            "acme", UpdateClientRequest(notes="Important note")
        )
        content = (tmp_path / "clients" / "acme" / "profile.md").read_text()
        assert "Important note" in content

    def test_update_creates_structured_dir(self, store, tmp_path):
        """Updating a flat-file client creates a structured directory."""
        (tmp_path / "clients" / "flat.md").write_text("# Flat Co\n\n## Company\n")
        updated = store.update_client("flat", UpdateClientRequest(notes="Upgraded"))
        assert updated is not None
        assert (tmp_path / "clients" / "flat" / "profile.md").exists()


# ---------------------------------------------------------------------------
# Deeper: _parse_client_markdown — slug formats
# ---------------------------------------------------------------------------


class TestParseClientSlugFormats:
    def test_multi_hyphen_slug(self, store):
        """Multi-hyphen slug converts to title case properly."""
        profile = store._parse_client_markdown("my-big-company", "No h1")
        assert profile.name == "My Big Company"

    def test_single_word_slug(self, store):
        """Single word slug gets title-cased."""
        profile = store._parse_client_markdown("acme", "No heading")
        assert profile.name == "Acme"

    def test_h1_with_extra_spaces(self, store):
        """H1 with extra whitespace gets stripped."""
        profile = store._parse_client_markdown("test", "#   Spaced Name   \n")
        assert profile.name == "Spaced Name"

    def test_empty_sections_default_to_empty_string(self, store):
        """All optional text fields default to empty string when missing."""
        profile = store._parse_client_markdown("x", "# X\n")
        assert profile.what_they_sell == ""
        assert profile.icp == ""
        assert profile.competitive_landscape == ""
        assert profile.recent_news == ""
        assert profile.value_proposition == ""
        assert profile.campaign_angles == ""
        assert profile.notes == ""
        assert profile.personas == ""
        assert profile.battle_cards == ""
        assert profile.signal_playbook == ""
        assert profile.proven_responses == ""
        assert profile.active_campaigns == ""


# ---------------------------------------------------------------------------
# Deeper: get_context_usage_map — multiple refs, defaults non-md
# ---------------------------------------------------------------------------


class TestContextUsageMapDeeper:
    @patch("app.core.context_store.load_skill_config", return_value={
        "context": ["kb/a.md", "kb/b.md", "kb/c.md"]
    })
    @patch("app.core.context_store.list_skills", return_value=["multi-ref"])
    def test_multiple_refs_per_skill(self, mock_ls, mock_cfg, store):
        """A skill with multiple context refs creates entries for each."""
        usage = store.get_context_usage_map()
        assert len(usage) == 3
        for key in ["kb/a.md", "kb/b.md", "kb/c.md"]:
            assert "multi-ref" in usage[key]

    @patch("app.core.context_store.load_skill_config", return_value={"context": []})
    @patch("app.core.context_store.load_skill", return_value="# Skill")
    @patch("app.core.context_store.parse_context_refs", return_value=[])
    @patch("app.core.context_store.list_skills", return_value=["s1"])
    def test_defaults_ignores_non_md(self, mock_ls, mock_refs, mock_load, mock_cfg, store, tmp_path):
        """Non-.md files in _defaults are not included."""
        defaults = tmp_path / "knowledge_base" / "_defaults"
        defaults.mkdir()
        (defaults / "system.md").write_text("System")
        (defaults / "data.json").write_text("{}")
        usage = store.get_context_usage_map()
        assert "knowledge_base/_defaults/system.md" in usage
        assert all("data.json" not in k for k in usage)

    @patch("app.core.context_store.load_skill_config", return_value={"context": []})
    @patch("app.core.context_store.load_skill", return_value="# Skill")
    @patch("app.core.context_store.parse_context_refs", return_value=[])
    @patch("app.core.context_store.list_skills", return_value=["s1", "s2", "s3"])
    def test_defaults_assigned_to_all_skills(self, mock_ls, mock_refs, mock_load, mock_cfg, store, tmp_path):
        """Default files are assigned to every skill."""
        defaults = tmp_path / "knowledge_base" / "_defaults"
        defaults.mkdir()
        (defaults / "base.md").write_text("Base")
        usage = store.get_context_usage_map()
        assert set(usage["knowledge_base/_defaults/base.md"]) == {"s1", "s2", "s3"}


# ---------------------------------------------------------------------------
# Deeper: preview_prompt — args verification
# ---------------------------------------------------------------------------


class TestPreviewPromptDeeper:
    @patch("app.core.context_store.build_prompt", return_value="Prompt")
    @patch("app.core.context_store.load_context_files", return_value=[])
    @patch("app.core.context_store.load_skill", return_value="# Email Skill")
    def test_load_context_files_receives_skill_name(self, mock_load, mock_ctx, mock_build):
        """load_context_files is called with skill_name kwarg."""
        store = ContextStore(
            clients_dir=Path("/tmp/c"),
            knowledge_dir=Path("/tmp/kb"),
            skills_dir=Path("/tmp/sk"),
        )
        store.preview_prompt("email-gen", "acme")
        _, kwargs = mock_ctx.call_args
        assert kwargs.get("skill_name") == "email-gen"

    @patch("app.core.context_store.build_prompt", return_value="")
    @patch("app.core.context_store.load_context_files", return_value=[])
    @patch("app.core.context_store.load_skill", return_value="# Skill")
    def test_empty_prompt_zero_tokens(self, mock_load, mock_ctx, mock_build):
        """Empty prompt gives 0 estimated tokens."""
        store = ContextStore(
            clients_dir=Path("/tmp/c"),
            knowledge_dir=Path("/tmp/kb"),
            skills_dir=Path("/tmp/sk"),
        )
        result = store.preview_prompt("test", "client")
        assert result.estimated_tokens == 0

    @patch("app.core.context_store.build_prompt", return_value="x" * 7)
    @patch("app.core.context_store.load_context_files", return_value=[])
    @patch("app.core.context_store.load_skill", return_value="# Skill")
    def test_token_estimate_integer_division(self, mock_load, mock_ctx, mock_build):
        """Token estimate is integer division by 4 (floor)."""
        store = ContextStore(
            clients_dir=Path("/tmp/c"),
            knowledge_dir=Path("/tmp/kb"),
            skills_dir=Path("/tmp/sk"),
        )
        result = store.preview_prompt("test", "client")
        assert result.estimated_tokens == 1  # 7 // 4 = 1
