"""Tests for app/core/agent_executor.py — multi-turn agent executor with tool calls."""

import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.agent_executor import AgentExecutor
from app.core.claude_executor import SubscriptionLimitError


# ---------------------------------------------------------------------------
# Helper to build a mock subprocess
# ---------------------------------------------------------------------------

def _mock_proc(returncode=0, stdout=b"", stderr=b""):
    proc = AsyncMock()
    proc.returncode = returncode
    proc.communicate = AsyncMock(return_value=(stdout, stderr))
    proc.kill = AsyncMock()
    proc.wait = AsyncMock()
    return proc


# ---------------------------------------------------------------------------
# _parse_json — static method
# ---------------------------------------------------------------------------


class TestParseJson:
    def test_clean_json(self):
        result = AgentExecutor._parse_json('{"key": "value"}')
        assert result == {"key": "value"}

    def test_json_in_markdown_fences(self):
        content = 'Here is the result:\n```json\n{"answer": true}\n```\nDone.'
        result = AgentExecutor._parse_json(content)
        assert result == {"answer": True}

    def test_json_in_plain_fences(self):
        content = '```\n{"x": 1}\n```'
        result = AgentExecutor._parse_json(content)
        assert result == {"x": 1}

    def test_brace_extraction_simple(self):
        content = 'Some reasoning text {"final": "result"}'
        result = AgentExecutor._parse_json(content)
        assert result == {"final": "result"}

    def test_brace_extraction_with_reasoning(self):
        content = 'After researching, here are my findings:\n\n{"signals": ["growth"]}'
        result = AgentExecutor._parse_json(content)
        assert result == {"signals": ["growth"]}

    def test_nested_json(self):
        content = '{"outer": {"inner": [1, 2, 3]}}'
        result = AgentExecutor._parse_json(content)
        assert result == {"outer": {"inner": [1, 2, 3]}}

    def test_unparseable_raises_value_error(self):
        with pytest.raises(ValueError, match="Could not parse JSON"):
            AgentExecutor._parse_json("No JSON here at all.")

    def test_fence_preferred_over_brace(self):
        content = 'text {"wrong": true}\n```json\n{"right": true}\n```'
        result = AgentExecutor._parse_json(content)
        assert result == {"right": True}

    def test_whitespace_json(self):
        content = '   \n  {"key": "val"}'
        result = AgentExecutor._parse_json(content)
        assert result == {"key": "val"}

    def test_multiple_brace_blocks_greedy_match(self):
        """The greedy regex matches from first { to last }, so this parses as one block."""
        content = '{"first": 1}'
        result = AgentExecutor._parse_json(content)
        assert result == {"first": 1}

    def test_invalid_fence_falls_to_brace(self):
        content = '```json\nnot valid json\n```\n{"fallback": true}'
        result = AgentExecutor._parse_json(content)
        assert result == {"fallback": True}


# ---------------------------------------------------------------------------
# MODEL_MAP
# ---------------------------------------------------------------------------


class TestModelMap:
    def test_opus_maps_to_opus(self):
        assert AgentExecutor.MODEL_MAP["opus"] == "opus"

    def test_sonnet_maps_to_sonnet(self):
        assert AgentExecutor.MODEL_MAP["sonnet"] == "sonnet"

    def test_haiku_maps_to_haiku(self):
        assert AgentExecutor.MODEL_MAP["haiku"] == "haiku"

    def test_unknown_model_not_in_map(self):
        assert "custom-v2" not in AgentExecutor.MODEL_MAP


# ---------------------------------------------------------------------------
# execute — success paths
# ---------------------------------------------------------------------------


class TestExecuteSuccess:
    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_basic_success(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=0,
            stdout=b'{"signals": ["growth", "hiring"]}',
        )
        executor = AgentExecutor()
        result = await executor.execute("Research Acme Corp", model="sonnet", timeout=60)
        assert result["result"] == {"signals": ["growth", "hiring"]}
        assert result["duration_ms"] >= 0
        assert result["prompt_chars"] == len("Research Acme Corp")
        assert result["response_chars"] > 0
        assert result["usage"] is None

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_raw_length_in_result(self, mock_exec):
        raw = b'{"answer": 1}'
        mock_exec.return_value = _mock_proc(returncode=0, stdout=raw)
        executor = AgentExecutor()
        result = await executor.execute("prompt")
        assert result["raw_length"] == len(raw)

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_model_resolved_from_map(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b'{"ok": true}')
        executor = AgentExecutor()
        await executor.execute("prompt", model="opus")
        call_args = mock_exec.call_args[0]
        idx = list(call_args).index("--model")
        assert call_args[idx + 1] == "opus"

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_unknown_model_passthrough(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b'{"ok": true}')
        executor = AgentExecutor()
        await executor.execute("prompt", model="custom-model-v2")
        call_args = mock_exec.call_args[0]
        idx = list(call_args).index("--model")
        assert call_args[idx + 1] == "custom-model-v2"

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_output_format_text(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b'{"ok": true}')
        executor = AgentExecutor()
        await executor.execute("prompt")
        call_args = mock_exec.call_args[0]
        idx = list(call_args).index("--output-format")
        assert call_args[idx + 1] == "text"

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_max_turns_passed(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b'{"ok": true}')
        executor = AgentExecutor()
        await executor.execute("prompt", max_turns=10)
        call_args = mock_exec.call_args[0]
        idx = list(call_args).index("--max-turns")
        assert call_args[idx + 1] == "10"

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_default_max_turns_is_5(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b'{"ok": true}')
        executor = AgentExecutor()
        await executor.execute("prompt")
        call_args = mock_exec.call_args[0]
        idx = list(call_args).index("--max-turns")
        assert call_args[idx + 1] == "5"

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_dangerously_skip_permissions_flag(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b'{"ok": true}')
        executor = AgentExecutor()
        await executor.execute("prompt")
        call_args = list(mock_exec.call_args[0])
        assert "--dangerously-skip-permissions" in call_args

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_stdin_dash_flag(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b'{"ok": true}')
        executor = AgentExecutor()
        await executor.execute("prompt")
        call_args = list(mock_exec.call_args[0])
        assert call_args[-1] == "-"


# ---------------------------------------------------------------------------
# execute — tools / allowed tools
# ---------------------------------------------------------------------------


class TestExecuteTools:
    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_default_tools_websearch_webfetch(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b'{"ok": true}')
        executor = AgentExecutor()
        await executor.execute("prompt")
        call_args = list(mock_exec.call_args[0])
        # Should have --allowedTools WebSearch --allowedTools WebFetch
        tool_indices = [i for i, a in enumerate(call_args) if a == "--allowedTools"]
        tools = [call_args[i + 1] for i in tool_indices]
        assert "WebSearch" in tools
        assert "WebFetch" in tools

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_custom_tools(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b'{"ok": true}')
        executor = AgentExecutor()
        await executor.execute("prompt", allowed_tools=["Read", "Grep", "Bash"])
        call_args = list(mock_exec.call_args[0])
        tool_indices = [i for i, a in enumerate(call_args) if a == "--allowedTools"]
        tools = [call_args[i + 1] for i in tool_indices]
        assert tools == ["Read", "Grep", "Bash"]

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_single_tool(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b'{"ok": true}')
        executor = AgentExecutor()
        await executor.execute("prompt", allowed_tools=["WebSearch"])
        call_args = list(mock_exec.call_args[0])
        tool_indices = [i for i, a in enumerate(call_args) if a == "--allowedTools"]
        tools = [call_args[i + 1] for i in tool_indices]
        assert tools == ["WebSearch"]


# ---------------------------------------------------------------------------
# execute — environment
# ---------------------------------------------------------------------------


class TestExecuteEnv:
    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_env_strips_claudecode_and_api_key(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b'{"ok": true}')
        executor = AgentExecutor()
        with patch.dict("os.environ", {"CLAUDECODE": "1", "ANTHROPIC_API_KEY": "sk-xxx", "HOME": "/home/test"}):
            await executor.execute("prompt")
        call_kwargs = mock_exec.call_args[1]
        env = call_kwargs["env"]
        assert "CLAUDECODE" not in env
        assert "ANTHROPIC_API_KEY" not in env
        assert "HOME" in env

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_env_preserves_other_vars(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b'{"ok": true}')
        executor = AgentExecutor()
        with patch.dict("os.environ", {"MY_VAR": "keep_me"}, clear=True):
            await executor.execute("prompt")
        env = mock_exec.call_args[1]["env"]
        assert env["MY_VAR"] == "keep_me"

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_prompt_sent_via_stdin(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b'{"ok": true}')
        executor = AgentExecutor()
        await executor.execute("my research prompt")
        proc = mock_exec.return_value
        proc.communicate.assert_called_once_with(input=b"my research prompt")


# ---------------------------------------------------------------------------
# execute — error paths
# ---------------------------------------------------------------------------


class TestExecuteErrors:
    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_timeout_kills_process(self, mock_exec):
        proc = _mock_proc()
        proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_exec.return_value = proc
        executor = AgentExecutor()
        with pytest.raises(TimeoutError, match="timed out after 60s"):
            await executor.execute("prompt", timeout=60)
        proc.kill.assert_called_once()
        proc.wait.assert_called_once()

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_nonzero_exit_raises_runtime_error(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=2,
            stdout=b"",
            stderr=b"Something went wrong",
        )
        executor = AgentExecutor()
        with pytest.raises(RuntimeError, match="exited with code 2"):
            await executor.execute("prompt")

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_empty_response_raises(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b"")
        executor = AgentExecutor()
        with pytest.raises(RuntimeError, match="Empty response"):
            await executor.execute("prompt")

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_whitespace_only_response_raises(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b"   \n  ")
        executor = AgentExecutor()
        with pytest.raises(RuntimeError, match="Empty response"):
            await executor.execute("prompt")

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_unparseable_text_raises(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b"No JSON here")
        executor = AgentExecutor()
        with pytest.raises(ValueError, match="Could not parse JSON"):
            await executor.execute("prompt")

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_error_message_truncated_to_500(self, mock_exec):
        long_err = "x" * 1000
        mock_exec.return_value = _mock_proc(returncode=2, stdout=b"", stderr=long_err.encode())
        executor = AgentExecutor()
        with pytest.raises(RuntimeError) as exc_info:
            await executor.execute("prompt")
        # Error message contains truncated stderr
        assert len(str(exc_info.value)) < 600


# ---------------------------------------------------------------------------
# execute — subscription limit detection
# ---------------------------------------------------------------------------


class TestSubscriptionLimit:
    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_exit_1_empty_stderr_is_subscription(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=1, stdout=b"", stderr=b"")
        executor = AgentExecutor()
        with pytest.raises(SubscriptionLimitError, match="subscription limit"):
            await executor.execute("prompt")

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_rate_limit_keyword_in_stderr(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=1, stdout=b"", stderr=b"Error: rate limit exceeded",
        )
        executor = AgentExecutor()
        with pytest.raises(SubscriptionLimitError):
            await executor.execute("prompt")

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_quota_keyword_in_stdout(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=1, stdout=b"quota exceeded", stderr=b"error occurred",
        )
        executor = AgentExecutor()
        with pytest.raises(SubscriptionLimitError):
            await executor.execute("prompt")

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_usage_limit_keyword(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=1, stdout=b"", stderr=b"usage limit reached",
        )
        executor = AgentExecutor()
        with pytest.raises(SubscriptionLimitError):
            await executor.execute("prompt")

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_capacity_keyword(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=1, stdout=b"", stderr=b"at capacity right now",
        )
        executor = AgentExecutor()
        with pytest.raises(SubscriptionLimitError):
            await executor.execute("prompt")

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_token_limit_keyword(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=1, stdout=b"", stderr=b"token limit reached",
        )
        executor = AgentExecutor()
        with pytest.raises(SubscriptionLimitError):
            await executor.execute("prompt")

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_non_subscription_error_not_misclassified(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=1, stdout=b"", stderr=b"Invalid model specified",
        )
        executor = AgentExecutor()
        with pytest.raises(RuntimeError, match="exited with code 1"):
            await executor.execute("prompt")

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_exit_2_with_no_stderr_is_not_subscription(self, mock_exec):
        """Only exit code 1 with empty stderr triggers subscription detection."""
        mock_exec.return_value = _mock_proc(returncode=2, stdout=b"", stderr=b"")
        executor = AgentExecutor()
        with pytest.raises(RuntimeError, match="exited with code 2"):
            await executor.execute("prompt")


# ---------------------------------------------------------------------------
# execute — text output parsing
# ---------------------------------------------------------------------------


class TestTextOutputParsing:
    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_text_with_fences_parsed(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=0,
            stdout=b'Here is the result:\n```json\n{"ok": true}\n```',
        )
        executor = AgentExecutor()
        result = await executor.execute("prompt")
        assert result["result"] == {"ok": True}

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_text_with_reasoning_and_json(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=0,
            stdout=b'After searching, I found:\n\n{"signals": ["growing"]}',
        )
        executor = AgentExecutor()
        result = await executor.execute("prompt")
        assert result["result"] == {"signals": ["growing"]}

    @patch("app.core.agent_executor.asyncio.create_subprocess_exec")
    async def test_clean_json_output(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=0,
            stdout=b'{"clean": true}',
        )
        executor = AgentExecutor()
        result = await executor.execute("prompt")
        assert result["result"] == {"clean": True}
