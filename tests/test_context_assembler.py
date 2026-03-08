import json
from unittest.mock import patch

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


class TestBuildAgentPrompts:
    @patch("app.core.context_assembler.settings")
    def test_default_researcher_role(self, mock_settings):
        """Without prefetched_context, uses autonomous researcher role."""
        mock_settings.prompt_size_warn_tokens = 50000
        prompt = build_agent_prompts(
            skill_content="Skill body",
            context_files=[],
            data={"company_name": "Acme"},
        )
        assert "autonomous research agent" in prompt
        assert "signal analyst" not in prompt
        assert "Research the target" in prompt

    @patch("app.core.context_assembler.settings")
    def test_analyst_role_with_prefetched_context(self, mock_settings):
        """With prefetched_context, switches to analyst role."""
        mock_settings.prompt_size_warn_tokens = 50000
        prefetched = "# Pre-Fetched Intelligence for Acme\n## News\nSome news here."
        prompt = build_agent_prompts(
            skill_content="Skill body",
            context_files=[],
            data={"company_name": "Acme"},
            prefetched_context=prefetched,
        )
        assert "signal analyst" in prompt
        assert "autonomous research agent" not in prompt
        assert "Analyze the pre-fetched intelligence" in prompt
        assert prefetched in prompt

    @patch("app.core.context_assembler.settings")
    def test_prefetched_context_injected_before_data(self, mock_settings):
        """Pre-fetched context appears before the data section."""
        mock_settings.prompt_size_warn_tokens = 50000
        prefetched = "# Pre-Fetched Intelligence\nIMPORTANT_MARKER"
        prompt = build_agent_prompts(
            skill_content="Skill body",
            context_files=[],
            data={"key": "DATA_MARKER"},
            prefetched_context=prefetched,
        )
        prefetch_pos = prompt.index("IMPORTANT_MARKER")
        data_pos = prompt.index("DATA_MARKER")
        assert prefetch_pos < data_pos

    @patch("app.core.context_assembler.settings")
    def test_none_prefetched_context_is_backward_compatible(self, mock_settings):
        """Passing prefetched_context=None produces same result as not passing it."""
        mock_settings.prompt_size_warn_tokens = 50000
        prompt_default = build_agent_prompts(
            skill_content="Skill",
            context_files=[],
            data={"x": 1},
        )
        prompt_none = build_agent_prompts(
            skill_content="Skill",
            context_files=[],
            data={"x": 1},
            prefetched_context=None,
        )
        assert prompt_default == prompt_none
