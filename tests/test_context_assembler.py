import json
from unittest.mock import MagicMock, patch

from app.core.context_assembler import (
    _CATEGORY_ROLES,
    _PRIORITY_ORDER,
    _context_priority,
    _get_role,
    build_agent_prompts,
    build_prompt,
)


class TestContextPriority:
    def test_frameworks_first(self):
        ctx = {"path": "knowledge_base/frameworks/sales.md"}
        assert _context_priority(ctx) == 0

    def test_clients_last_in_order(self):
        ctx = {"path": "clients/acme.md"}
        assert _context_priority(ctx) == len(_PRIORITY_ORDER) - 1

    def test_unknown_path_gets_max_priority(self):
        ctx = {"path": "random/unknown.md"}
        assert _context_priority(ctx) == len(_PRIORITY_ORDER)

    def test_industries_before_clients(self):
        ind = _context_priority({"path": "knowledge_base/industries/saas.md"})
        cli = _context_priority({"path": "clients/acme.md"})
        assert ind < cli

    def test_voice_before_industries(self):
        voice = _context_priority({"path": "knowledge_base/voice/default.md"})
        ind = _context_priority({"path": "knowledge_base/industries/saas.md"})
        assert voice < ind


class TestGetRole:
    def test_known_categories(self):
        assert _get_role("knowledge_base/frameworks/sales.md") == "Methodology & frameworks"
        assert _get_role("knowledge_base/voice/default.md") == "Writing style & tone"
        assert _get_role("clients/acme.md") == "Client profile"
        assert _get_role("knowledge_base/industries/saas.md") == "Industry context"

    def test_unknown_category_returns_reference(self):
        assert _get_role("knowledge_base/custom/thing.md") == "Reference"
        assert _get_role("other/path.md") == "Reference"

    def test_all_category_roles_mapped(self):
        expected = {
            "frameworks", "voice", "objections", "competitive",
            "sequences", "signals", "personas", "industries", "clients",
        }
        assert set(_CATEGORY_ROLES.keys()) == expected


class TestBuildPrompt:
    @patch("app.core.context_assembler.settings")
    def test_basic_prompt_structure(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        prompt = build_prompt(
            skill_content="Do the thing.",
            context_files=[],
            data={"name": "Jane"},
        )
        assert "JSON generation engine" in prompt
        assert "# Skill Instructions" in prompt
        assert "Do the thing." in prompt
        assert '"name": "Jane"' in prompt
        assert "Return ONLY the JSON object" in prompt

    @patch("app.core.context_assembler.settings")
    def test_no_context_section_when_empty(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        prompt = build_prompt(
            skill_content="Skill body",
            context_files=[],
            data={},
        )
        assert "Loaded Context" not in prompt

    @patch("app.core.context_assembler.settings")
    def test_context_files_included_and_sorted(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        context_files = [
            {"path": "clients/acme.md", "content": "Acme profile"},
            {"path": "knowledge_base/frameworks/sales.md", "content": "Sales framework"},
        ]
        prompt = build_prompt(
            skill_content="Skill",
            context_files=context_files,
            data={},
        )
        assert "Loaded Context (2 files)" in prompt
        # Frameworks should appear before clients in manifest
        fw_pos = prompt.index("knowledge_base/frameworks/sales.md")
        cli_pos = prompt.index("clients/acme.md")
        assert fw_pos < cli_pos

    @patch("app.core.context_assembler.settings")
    def test_context_manifest_has_roles(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        context_files = [
            {"path": "knowledge_base/voice/default.md", "content": "Voice guide"},
        ]
        prompt = build_prompt(
            skill_content="Skill",
            context_files=context_files,
            data={},
        )
        assert "Writing style & tone" in prompt

    @patch("app.core.context_assembler.settings")
    def test_context_content_included(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        context_files = [
            {"path": "knowledge_base/frameworks/x.md", "content": "Framework body here"},
        ]
        prompt = build_prompt(
            skill_content="Skill",
            context_files=context_files,
            data={},
        )
        assert "Framework body here" in prompt

    @patch("app.core.context_assembler.settings")
    def test_instructions_included(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        prompt = build_prompt(
            skill_content="Skill",
            context_files=[],
            data={},
            instructions="Be concise and formal.",
        )
        assert "Campaign Instructions" in prompt
        assert "Be concise and formal." in prompt

    @patch("app.core.context_assembler.settings")
    def test_no_instructions_section_when_none(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        prompt = build_prompt(
            skill_content="Skill",
            context_files=[],
            data={},
            instructions=None,
        )
        assert "Campaign Instructions" not in prompt

    @patch("app.core.context_assembler.settings")
    def test_data_serialized_as_json(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        data = {"company": "Acme", "revenue": 1000000}
        prompt = build_prompt(
            skill_content="Skill",
            context_files=[],
            data=data,
        )
        assert json.dumps(data) in prompt

    @patch("app.core.context_assembler.settings")
    def test_layer_order(self, mock_settings):
        """Verify the 6 layers appear in order: system, skill, context, data, instructions, reminder."""
        mock_settings.prompt_size_warn_tokens = 50000
        prompt = build_prompt(
            skill_content="SKILL_MARKER",
            context_files=[{"path": "knowledge_base/frameworks/x.md", "content": "CTX_MARKER"}],
            data={"key": "DATA_MARKER"},
            instructions="INSTR_MARKER",
        )
        positions = [
            prompt.index("JSON generation engine"),
            prompt.index("SKILL_MARKER"),
            prompt.index("CTX_MARKER"),
            prompt.index("DATA_MARKER"),
            prompt.index("INSTR_MARKER"),
            prompt.rindex("Return ONLY the JSON object"),
        ]
        assert positions == sorted(positions)

    @patch("app.core.context_assembler.settings")
    def test_large_prompt_does_not_raise(self, mock_settings):
        """Large prompts trigger a warning log but still return."""
        mock_settings.prompt_size_warn_tokens = 10  # very low threshold
        prompt = build_prompt(
            skill_content="x" * 1000,
            context_files=[],
            data={},
        )
        assert len(prompt) > 1000

    @patch("app.core.context_assembler.settings")
    def test_empty_data(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        prompt = build_prompt(
            skill_content="Skill",
            context_files=[],
            data={},
        )
        assert json.dumps({}) in prompt

    @patch("app.core.context_assembler.settings")
    def test_empty_instructions_string_not_included(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        prompt = build_prompt(
            skill_content="Skill",
            context_files=[],
            data={},
            instructions="",
        )
        assert "Campaign Instructions" not in prompt

    @patch("app.core.context_assembler.settings")
    def test_multiple_context_files_all_content_present(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        context_files = [
            {"path": "knowledge_base/voice/tone.md", "content": "VOICE_CONTENT"},
            {"path": "knowledge_base/industries/saas.md", "content": "INDUSTRY_CONTENT"},
            {"path": "clients/acme.md", "content": "CLIENT_CONTENT"},
        ]
        prompt = build_prompt(
            skill_content="Skill", context_files=context_files, data={},
        )
        assert "Loaded Context (3 files)" in prompt
        assert "VOICE_CONTENT" in prompt
        assert "INDUSTRY_CONTENT" in prompt
        assert "CLIENT_CONTENT" in prompt

    @patch("app.core.context_assembler.settings")
    def test_context_sorting_full_order(self, mock_settings):
        """All priority categories sort correctly."""
        mock_settings.prompt_size_warn_tokens = 50000
        context_files = [
            {"path": "clients/x.md", "content": "c"},
            {"path": "knowledge_base/industries/x.md", "content": "i"},
            {"path": "knowledge_base/frameworks/x.md", "content": "f"},
            {"path": "knowledge_base/voice/x.md", "content": "v"},
        ]
        prompt = build_prompt(
            skill_content="Skill", context_files=context_files, data={},
        )
        fw = prompt.index("knowledge_base/frameworks/x.md")
        vo = prompt.index("knowledge_base/voice/x.md")
        ind = prompt.index("knowledge_base/industries/x.md")
        cli = prompt.index("clients/x.md")
        assert fw < vo < ind < cli


# ---------------------------------------------------------------------------
# build_prompt — memory injection
# ---------------------------------------------------------------------------


class TestBuildPromptMemory:
    @patch("app.core.context_assembler.settings")
    def test_memory_injected_when_entries_found(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        memory_store = MagicMock()
        memory_store.query.return_value = ["entry1", "entry2"]
        memory_store.format_for_prompt.return_value = "# Prior Knowledge\n- skill1: data"

        prompt = build_prompt(
            skill_content="Skill",
            context_files=[],
            data={"company": "Acme"},
            memory_store=memory_store,
        )
        assert "Prior Knowledge" in prompt
        assert "skill1: data" in prompt
        memory_store.query.assert_called_once_with({"company": "Acme"})

    @patch("app.core.context_assembler.settings")
    def test_memory_not_injected_when_no_entries(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        memory_store = MagicMock()
        memory_store.query.return_value = []

        prompt = build_prompt(
            skill_content="Skill",
            context_files=[],
            data={},
            memory_store=memory_store,
        )
        assert "Prior Knowledge" not in prompt
        memory_store.format_for_prompt.assert_not_called()

    @patch("app.core.context_assembler.settings")
    def test_memory_none_no_error(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        prompt = build_prompt(
            skill_content="Skill",
            context_files=[],
            data={},
            memory_store=None,
        )
        assert "JSON generation engine" in prompt

    @patch("app.core.context_assembler.settings")
    def test_memory_before_context_in_order(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        memory_store = MagicMock()
        memory_store.query.return_value = ["e"]
        memory_store.format_for_prompt.return_value = "MEMORY_MARKER"

        prompt = build_prompt(
            skill_content="Skill",
            context_files=[{"path": "clients/x.md", "content": "CTX_MARKER"}],
            data={},
            memory_store=memory_store,
        )
        assert prompt.index("MEMORY_MARKER") < prompt.index("CTX_MARKER")


# ---------------------------------------------------------------------------
# build_prompt — semantic context
# ---------------------------------------------------------------------------


class TestBuildPromptSemanticContext:
    @patch("app.core.skill_loader.load_file")
    @patch("app.core.context_assembler.settings")
    def test_semantic_context_added(self, mock_settings, mock_load_file):
        mock_settings.prompt_size_warn_tokens = 50000
        mock_load_file.return_value = "Semantic file content"

        context_index = MagicMock()
        context_index.search_by_data.return_value = [
            ("knowledge_base/industries/saas.md", 0.9),
        ]

        prompt = build_prompt(
            skill_content="Skill",
            context_files=[],
            data={"industry": "SaaS"},
            context_index=context_index,
        )
        assert "Semantic file content" in prompt
        assert "knowledge_base/industries/saas.md" in prompt

    @patch("app.core.skill_loader.load_file")
    @patch("app.core.context_assembler.settings")
    def test_semantic_context_deduplicates(self, mock_settings, mock_load_file):
        mock_settings.prompt_size_warn_tokens = 50000
        mock_load_file.return_value = "Should not appear"

        context_index = MagicMock()
        context_index.search_by_data.return_value = [
            ("clients/acme.md", 0.8),
        ]

        prompt = build_prompt(
            skill_content="Skill",
            context_files=[{"path": "clients/acme.md", "content": "Already loaded"}],
            data={},
            context_index=context_index,
        )
        # load_file should NOT be called since path is already in context_files
        mock_load_file.assert_not_called()
        # Should only appear once
        assert prompt.count("clients/acme.md") == 2  # manifest + header

    @patch("app.core.skill_loader.load_file")
    @patch("app.core.context_assembler.settings")
    def test_semantic_context_skips_empty_files(self, mock_settings, mock_load_file):
        mock_settings.prompt_size_warn_tokens = 50000
        mock_load_file.return_value = None  # File not found

        context_index = MagicMock()
        context_index.search_by_data.return_value = [
            ("knowledge_base/missing.md", 0.7),
        ]

        prompt = build_prompt(
            skill_content="Skill",
            context_files=[],
            data={},
            context_index=context_index,
        )
        assert "missing.md" not in prompt

    @patch("app.core.context_assembler.settings")
    def test_no_context_index_no_error(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        prompt = build_prompt(
            skill_content="Skill",
            context_files=[],
            data={},
            context_index=None,
        )
        assert "JSON generation engine" in prompt


# ---------------------------------------------------------------------------
# build_agent_prompts
# ---------------------------------------------------------------------------


class TestBuildAgentPrompts:
    @patch("app.core.context_assembler.settings")
    def test_agent_prompt_structure(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        prompt = build_agent_prompts(
            skill_content="Research the target.",
            context_files=[],
            data={"company": "Acme"},
        )
        assert "autonomous research agent" in prompt
        assert "Skill Instructions" in prompt
        assert "Research the target." in prompt
        assert "Data to Research" in prompt
        assert '"company": "Acme"' in prompt
        assert "raw JSON" in prompt

    @patch("app.core.context_assembler.settings")
    def test_agent_prompt_no_json_only_header(self, mock_settings):
        """Agent prompts should NOT have the rigid 'JSON generation engine' prefix."""
        mock_settings.prompt_size_warn_tokens = 50000
        prompt = build_agent_prompts(
            skill_content="Skill",
            context_files=[],
            data={},
        )
        assert "JSON generation engine" not in prompt
        assert "autonomous research agent" in prompt

    @patch("app.core.context_assembler.settings")
    def test_agent_prompt_with_instructions(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        prompt = build_agent_prompts(
            skill_content="Skill",
            context_files=[],
            data={},
            instructions="Focus on hiring signals.",
        )
        assert "Campaign Instructions" in prompt
        assert "Focus on hiring signals." in prompt

    @patch("app.core.context_assembler.settings")
    def test_agent_prompt_no_instructions(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        prompt = build_agent_prompts(
            skill_content="Skill",
            context_files=[],
            data={},
            instructions=None,
        )
        assert "Campaign Instructions" not in prompt

    @patch("app.core.context_assembler.settings")
    def test_agent_prompt_with_context_files(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        context_files = [
            {"path": "knowledge_base/signals/patterns.md", "content": "Signal patterns content"},
            {"path": "clients/target.md", "content": "Target profile content"},
        ]
        prompt = build_agent_prompts(
            skill_content="Skill",
            context_files=context_files,
            data={},
        )
        assert "Loaded Context (2 files)" in prompt
        assert "Signal patterns content" in prompt
        assert "Target profile content" in prompt

    @patch("app.core.context_assembler.settings")
    def test_agent_prompt_context_sorted(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        context_files = [
            {"path": "clients/x.md", "content": "client"},
            {"path": "knowledge_base/frameworks/x.md", "content": "framework"},
        ]
        prompt = build_agent_prompts(
            skill_content="Skill",
            context_files=context_files,
            data={},
        )
        fw = prompt.index("knowledge_base/frameworks/x.md")
        cli = prompt.index("clients/x.md")
        assert fw < cli

    @patch("app.core.context_assembler.settings")
    def test_agent_prompt_memory_injection(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        memory_store = MagicMock()
        memory_store.query.return_value = ["entry"]
        memory_store.format_for_prompt.return_value = "AGENT_MEMORY_CONTENT"

        prompt = build_agent_prompts(
            skill_content="Skill",
            context_files=[],
            data={"domain": "test.com"},
            memory_store=memory_store,
        )
        assert "AGENT_MEMORY_CONTENT" in prompt

    @patch("app.core.context_assembler.settings")
    def test_agent_prompt_no_memory_when_empty(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        memory_store = MagicMock()
        memory_store.query.return_value = []

        build_agent_prompts(
            skill_content="Skill",
            context_files=[],
            data={},
            memory_store=memory_store,
        )
        memory_store.format_for_prompt.assert_not_called()

    @patch("app.core.skill_loader.load_file")
    @patch("app.core.context_assembler.settings")
    def test_agent_prompt_semantic_context(self, mock_settings, mock_load_file):
        mock_settings.prompt_size_warn_tokens = 50000
        mock_load_file.return_value = "Semantic content here"

        context_index = MagicMock()
        context_index.search_by_data.return_value = [
            ("knowledge_base/industries/tech.md", 0.8),
        ]

        prompt = build_agent_prompts(
            skill_content="Skill",
            context_files=[],
            data={"industry": "tech"},
            context_index=context_index,
        )
        assert "Semantic content here" in prompt

    @patch("app.core.context_assembler.settings")
    def test_agent_prompt_layer_order(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 50000
        prompt = build_agent_prompts(
            skill_content="SKILL_MARKER",
            context_files=[{"path": "knowledge_base/frameworks/x.md", "content": "CTX_MARKER"}],
            data={"key": "DATA_MARKER"},
            instructions="INSTR_MARKER",
        )
        positions = [
            prompt.index("autonomous research agent"),
            prompt.index("SKILL_MARKER"),
            prompt.index("CTX_MARKER"),
            prompt.index("DATA_MARKER"),
            prompt.index("INSTR_MARKER"),
            prompt.rindex("raw JSON"),
        ]
        assert positions == sorted(positions)

    @patch("app.core.context_assembler.settings")
    def test_agent_prompt_large_warning_no_raise(self, mock_settings):
        mock_settings.prompt_size_warn_tokens = 10
        prompt = build_agent_prompts(
            skill_content="x" * 1000,
            context_files=[],
            data={},
        )
        assert len(prompt) > 1000


# ---------------------------------------------------------------------------
# _context_priority — additional edge cases
# ---------------------------------------------------------------------------


class TestContextPriorityEdges:
    def test_all_priority_prefixes(self):
        for i, prefix in enumerate(_PRIORITY_ORDER):
            ctx = {"path": f"{prefix}test.md"}
            assert _context_priority(ctx) == i

    def test_objections_before_competitive(self):
        obj = _context_priority({"path": "knowledge_base/objections/x.md"})
        comp = _context_priority({"path": "knowledge_base/competitive/x.md"})
        assert obj < comp

    def test_sequences_before_signals(self):
        seq = _context_priority({"path": "knowledge_base/sequences/x.md"})
        sig = _context_priority({"path": "knowledge_base/signals/x.md"})
        assert seq < sig

    def test_personas_before_industries(self):
        per = _context_priority({"path": "knowledge_base/personas/x.md"})
        ind = _context_priority({"path": "knowledge_base/industries/x.md"})
        assert per < ind


# ---------------------------------------------------------------------------
# _get_role — additional edge cases
# ---------------------------------------------------------------------------


class TestGetRoleEdges:
    def test_objections_role(self):
        assert _get_role("knowledge_base/objections/common.md") == "Objection handling"

    def test_competitive_role(self):
        assert _get_role("knowledge_base/competitive/rival.md") == "Competitive intelligence"

    def test_sequences_role(self):
        assert _get_role("knowledge_base/sequences/drip.md") == "Sequence templates"

    def test_signals_role(self):
        assert _get_role("knowledge_base/signals/patterns.md") == "Signal patterns"

    def test_personas_role(self):
        assert _get_role("knowledge_base/personas/cto.md") == "Persona profiles"

    def test_deep_nested_path(self):
        assert _get_role("knowledge_base/frameworks/sub/deep/file.md") == "Methodology & frameworks"


class TestBuildAgentPromptsExtended:
    @patch("app.core.context_assembler.settings")
    def test_default_researcher_role(self, mock_settings):
        """Uses autonomous researcher role."""
        mock_settings.prompt_size_warn_tokens = 50000
        prompt = build_agent_prompts(
            skill_content="Skill body",
            context_files=[],
            data={"company_name": "Acme"},
        )
        assert "autonomous research agent" in prompt
        assert "Research the target" in prompt
