import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.claude_executor import ClaudeExecutor, SubscriptionLimitError


class TestExtractContent:
    def test_list_envelope_with_text_blocks(self):
        envelope = [
            {"type": "text", "text": "Hello"},
            {"type": "text", "text": "World"},
        ]
        result = ClaudeExecutor._extract_content(envelope)
        assert result == "Hello\nWorld"

    def test_list_envelope_skips_non_text(self):
        envelope = [
            {"type": "tool_use", "name": "foo"},
            {"type": "text", "text": "Only this"},
        ]
        result = ClaudeExecutor._extract_content(envelope)
        assert result == "Only this"

    def test_dict_with_result_key(self):
        envelope = {"result": '{"answer": 42}'}
        result = ClaudeExecutor._extract_content(envelope)
        assert result == '{"answer": 42}'

    def test_dict_with_text_key(self):
        envelope = {"text": "hello"}
        assert ClaudeExecutor._extract_content(envelope) == "hello"

    def test_dict_with_content_key(self):
        envelope = {"content": "body"}
        assert ClaudeExecutor._extract_content(envelope) == "body"

    def test_dict_priority_result_over_text(self):
        envelope = {"result": "winner", "text": "loser"}
        assert ClaudeExecutor._extract_content(envelope) == "winner"

    def test_fallback_reserializes(self):
        envelope = {"unknown_key": "value"}
        result = ClaudeExecutor._extract_content(envelope)
        parsed = json.loads(result)
        assert parsed == {"unknown_key": "value"}

    def test_empty_list_fallback(self):
        envelope = []
        result = ClaudeExecutor._extract_content(envelope)
        assert result == "[]"

    def test_list_with_no_text_blocks(self):
        envelope = [{"type": "image", "data": "..."}]
        result = ClaudeExecutor._extract_content(envelope)
        # No text blocks found -> fallback to JSON serialization
        parsed = json.loads(result)
        assert parsed == [{"type": "image", "data": "..."}]


class TestParseJson:
    def test_clean_json(self):
        content = '{"key": "value", "num": 42}'
        result = ClaudeExecutor._parse_json(content)
        assert result == {"key": "value", "num": 42}

    def test_json_in_markdown_fences(self):
        content = 'Here is the result:\n```json\n{"answer": true}\n```\nDone.'
        result = ClaudeExecutor._parse_json(content)
        assert result == {"answer": True}

    def test_json_in_plain_fences(self):
        content = '```\n{"x": 1}\n```'
        result = ClaudeExecutor._parse_json(content)
        assert result == {"x": 1}

    def test_brace_extraction(self):
        content = 'Some text before {"extracted": "yes"} and after'
        result = ClaudeExecutor._parse_json(content)
        assert result == {"extracted": "yes"}

    def test_unparseable_raises(self):
        with pytest.raises(ValueError, match="Could not parse JSON"):
            ClaudeExecutor._parse_json("This is just text, no JSON here.")

    def test_nested_json(self):
        content = '{"outer": {"inner": [1, 2, 3]}}'
        result = ClaudeExecutor._parse_json(content)
        assert result == {"outer": {"inner": [1, 2, 3]}}

    def test_json_with_leading_whitespace(self):
        content = '   \n  {"key": "val"}'
        result = ClaudeExecutor._parse_json(content)
        assert result == {"key": "val"}

    def test_fence_preferred_over_brace(self):
        content = 'text {"wrong": true}\n```json\n{"right": true}\n```'
        result = ClaudeExecutor._parse_json(content)
        # Direct parse fails (has prefix text), fence match wins
        assert result == {"right": True}


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
# execute — success paths
# ---------------------------------------------------------------------------


class TestExecuteSuccess:
    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_basic_success(self, mock_exec):
        envelope = [{"type": "text", "text": '{"answer": 42}'}]
        mock_exec.return_value = _mock_proc(
            returncode=0,
            stdout=json.dumps(envelope).encode(),
        )
        executor = ClaudeExecutor()
        result = await executor.execute("What is 6*7?", model="opus", timeout=30)
        assert result["result"] == {"answer": 42}
        assert result["duration_ms"] >= 0
        assert result["prompt_chars"] == len("What is 6*7?")
        assert result["response_chars"] > 0

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_model_map_resolved(self, mock_exec):
        envelope = [{"type": "text", "text": '{"ok": true}'}]
        mock_exec.return_value = _mock_proc(
            returncode=0,
            stdout=json.dumps(envelope).encode(),
        )
        executor = ClaudeExecutor()
        await executor.execute("prompt", model="haiku")
        call_args = mock_exec.call_args[0]
        assert "--model" in call_args
        idx = list(call_args).index("--model")
        assert call_args[idx + 1] == "haiku"

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_unknown_model_passthrough(self, mock_exec):
        envelope = [{"type": "text", "text": '{"ok": true}'}]
        mock_exec.return_value = _mock_proc(
            returncode=0,
            stdout=json.dumps(envelope).encode(),
        )
        executor = ClaudeExecutor()
        await executor.execute("prompt", model="custom-model-v2")
        call_args = mock_exec.call_args[0]
        idx = list(call_args).index("--model")
        assert call_args[idx + 1] == "custom-model-v2"

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_env_strips_claudecode_and_api_key(self, mock_exec):
        envelope = [{"type": "text", "text": '{"ok": true}'}]
        mock_exec.return_value = _mock_proc(
            returncode=0,
            stdout=json.dumps(envelope).encode(),
        )
        executor = ClaudeExecutor()
        with patch.dict("os.environ", {"CLAUDECODE": "1", "ANTHROPIC_API_KEY": "sk-xxx", "HOME": "/home/test"}):
            await executor.execute("prompt")
        call_kwargs = mock_exec.call_args[1]
        env = call_kwargs["env"]
        assert "CLAUDECODE" not in env
        assert "ANTHROPIC_API_KEY" not in env
        assert "HOME" in env

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_usage_extracted_from_envelope(self, mock_exec):
        envelope = {
            "result": '{"answer": 1}',
            "usage": {"input_tokens": 500, "output_tokens": 200},
        }
        mock_exec.return_value = _mock_proc(
            returncode=0,
            stdout=json.dumps(envelope).encode(),
        )
        executor = ClaudeExecutor()
        result = await executor.execute("prompt")
        assert result["usage"] == {"input_tokens": 500, "output_tokens": 200}

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_usage_none_for_list_envelope(self, mock_exec):
        envelope = [{"type": "text", "text": '{"answer": 1}'}]
        mock_exec.return_value = _mock_proc(
            returncode=0,
            stdout=json.dumps(envelope).encode(),
        )
        executor = ClaudeExecutor()
        result = await executor.execute("prompt")
        assert result["usage"] is None


# ---------------------------------------------------------------------------
# execute — error paths
# ---------------------------------------------------------------------------


class TestExecuteErrors:
    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_timeout_kills_process(self, mock_exec):
        proc = _mock_proc()
        proc.communicate = AsyncMock(side_effect=asyncio.TimeoutError())
        mock_exec.return_value = proc
        executor = ClaudeExecutor()
        with pytest.raises(TimeoutError, match="timed out after 30s"):
            await executor.execute("prompt", timeout=30)
        proc.kill.assert_called_once()
        proc.wait.assert_called_once()

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_nonzero_exit_raises_runtime_error(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=2,
            stdout=b"",
            stderr=b"Something went wrong",
        )
        executor = ClaudeExecutor()
        with pytest.raises(RuntimeError, match="exited with code 2"):
            await executor.execute("prompt")

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_empty_response_raises(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b"")
        executor = ClaudeExecutor()
        with pytest.raises(RuntimeError, match="Empty response"):
            await executor.execute("prompt")

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_whitespace_only_response_raises(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b"   \n  ")
        executor = ClaudeExecutor()
        with pytest.raises(RuntimeError, match="Empty response"):
            await executor.execute("prompt")


# ---------------------------------------------------------------------------
# execute — subscription limit detection
# ---------------------------------------------------------------------------


class TestSubscriptionLimit:
    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_exit_1_empty_stderr_is_subscription(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=1, stdout=b"", stderr=b"")
        executor = ClaudeExecutor()
        with pytest.raises(SubscriptionLimitError, match="subscription limit"):
            await executor.execute("prompt")

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_rate_limit_keyword_in_stderr(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=1,
            stdout=b"",
            stderr=b"Error: rate limit exceeded",
        )
        executor = ClaudeExecutor()
        with pytest.raises(SubscriptionLimitError):
            await executor.execute("prompt")

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_quota_keyword_in_stdout(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=1,
            stdout=b"quota exceeded",
            stderr=b"error occurred",
        )
        executor = ClaudeExecutor()
        with pytest.raises(SubscriptionLimitError):
            await executor.execute("prompt")

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_usage_limit_keyword(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=1,
            stdout=b"",
            stderr=b"usage limit reached",
        )
        executor = ClaudeExecutor()
        with pytest.raises(SubscriptionLimitError):
            await executor.execute("prompt")

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_non_subscription_error_not_misclassified(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=1,
            stdout=b"",
            stderr=b"Invalid model specified",
        )
        executor = ClaudeExecutor()
        with pytest.raises(RuntimeError, match="exited with code 1"):
            await executor.execute("prompt")
