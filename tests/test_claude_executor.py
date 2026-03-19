import asyncio
from unittest.mock import AsyncMock, patch

import pytest

from app.core.claude_executor import ClaudeExecutor, SubscriptionLimitError


class TestOutputFormatText:
    """The executor now uses --output-format text, so stdout is raw text parsed by _parse_json."""

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_text_output_parsed_as_json(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=0, stdout=b'{"answer": 42}',
        )
        executor = ClaudeExecutor()
        result = await executor.execute("prompt")
        assert result["result"] == {"answer": 42}

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_text_with_fences_parsed(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=0,
            stdout=b'Here is the result:\n```json\n{"ok": true}\n```',
        )
        executor = ClaudeExecutor()
        result = await executor.execute("prompt")
        assert result["result"] == {"ok": True}

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_text_with_embedded_json(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=0,
            stdout=b'Some text {"extracted": "yes"} more text',
        )
        executor = ClaudeExecutor()
        result = await executor.execute("prompt")
        assert result["result"] == {"extracted": "yes"}

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_unparseable_text_raises(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=0, stdout=b"No JSON here at all",
        )
        executor = ClaudeExecutor()
        with pytest.raises(ValueError, match="Could not parse JSON"):
            await executor.execute("prompt")


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
        mock_exec.return_value = _mock_proc(
            returncode=0,
            stdout=b'{"answer": 42}',
        )
        executor = ClaudeExecutor()
        result = await executor.execute("What is 6*7?", model="opus", timeout=30)
        assert result["result"] == {"answer": 42}
        assert result["duration_ms"] >= 0
        assert result["prompt_chars"] == len("What is 6*7?")
        assert result["response_chars"] > 0
        assert result["usage"] is None

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_model_map_resolved(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=0, stdout=b'{"ok": true}',
        )
        executor = ClaudeExecutor()
        await executor.execute("prompt", model="haiku")
        call_args = mock_exec.call_args[0]
        assert "--model" in call_args
        idx = list(call_args).index("--model")
        assert call_args[idx + 1] == "haiku"

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_unknown_model_passthrough(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=0, stdout=b'{"ok": true}',
        )
        executor = ClaudeExecutor()
        await executor.execute("prompt", model="custom-model-v2")
        call_args = mock_exec.call_args[0]
        idx = list(call_args).index("--model")
        assert call_args[idx + 1] == "custom-model-v2"

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_env_strips_claudecode_and_api_key(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=0, stdout=b'{"ok": true}',
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
    async def test_raw_length_in_result(self, mock_exec):
        raw = b'{"answer": 1}'
        mock_exec.return_value = _mock_proc(returncode=0, stdout=raw)
        executor = ClaudeExecutor()
        result = await executor.execute("prompt")
        assert result["raw_length"] == len(raw)

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_output_format_text_flag(self, mock_exec):
        """Executor uses --output-format text."""
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b'{"ok": true}')
        executor = ClaudeExecutor()
        await executor.execute("prompt")
        call_args = mock_exec.call_args[0]
        idx = list(call_args).index("--output-format")
        assert call_args[idx + 1] == "text"


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


# ---------------------------------------------------------------------------
# DEEPER TESTS — Coverage gaps
# ---------------------------------------------------------------------------


class TestSubscriptionLimitDeeper:
    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_capacity_keyword(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=1, stdout=b"", stderr=b"No capacity available",
        )
        executor = ClaudeExecutor()
        with pytest.raises(SubscriptionLimitError):
            await executor.execute("prompt")

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_token_limit_keyword(self, mock_exec):
        mock_exec.return_value = _mock_proc(
            returncode=1, stdout=b"", stderr=b"token limit exceeded for today",
        )
        executor = ClaudeExecutor()
        with pytest.raises(SubscriptionLimitError):
            await executor.execute("prompt")

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_case_insensitive_detection(self, mock_exec):
        """Keywords are matched case-insensitively via .lower()."""
        mock_exec.return_value = _mock_proc(
            returncode=1, stdout=b"RATE LIMIT EXCEEDED", stderr=b"",
        )
        executor = ClaudeExecutor()
        with pytest.raises(SubscriptionLimitError):
            await executor.execute("prompt")

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_error_message_includes_exit_code(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=1, stdout=b"", stderr=b"")
        executor = ClaudeExecutor()
        with pytest.raises(SubscriptionLimitError, match="exit code 1"):
            await executor.execute("prompt")

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_exit_code_2_empty_stderr_not_subscription(self, mock_exec):
        """Only exit code 1 + empty stderr triggers subscription limit."""
        mock_exec.return_value = _mock_proc(returncode=2, stdout=b"", stderr=b"")
        executor = ClaudeExecutor()
        with pytest.raises(RuntimeError, match="exited with code 2"):
            await executor.execute("prompt")

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_keyword_in_stdout_only(self, mock_exec):
        """Rate limit keywords in stdout alone trigger subscription limit."""
        mock_exec.return_value = _mock_proc(
            returncode=1, stdout=b"rate limit hit", stderr=b"some error",
        )
        executor = ClaudeExecutor()
        with pytest.raises(SubscriptionLimitError):
            await executor.execute("prompt")

    def test_inherits_from_runtime_error(self):
        err = SubscriptionLimitError("test")
        assert isinstance(err, RuntimeError)

    def test_catchable_as_runtime_error(self):
        with pytest.raises(RuntimeError):
            raise SubscriptionLimitError("limit reached")


class TestParseJsonDeeper:
    def test_empty_json_object(self):
        assert ClaudeExecutor._parse_json("{}") == {}

    def test_json_array_raises(self):
        """Direct parse returns a list, not a dict — but json.loads succeeds."""
        result = ClaudeExecutor._parse_json("[1, 2, 3]")
        assert result == [1, 2, 3]

    def test_unicode_content(self):
        content = '{"name": "café", "emoji": "🎉"}'
        result = ClaudeExecutor._parse_json(content)
        assert result == {"name": "café", "emoji": "🎉"}

    def test_fence_with_invalid_json_raises(self):
        """Invalid JSON in fence + invalid brace extraction = raises ValueError."""
        content = '```json\n{invalid}\n```\nBut here also {broken}'
        with pytest.raises(ValueError, match="Could not parse JSON"):
            ClaudeExecutor._parse_json(content)

    def test_brace_with_invalid_json_raises(self):
        """Invalid JSON in braces with no other match raises ValueError."""
        content = 'text {not: valid json} more text'
        with pytest.raises(ValueError, match="Could not parse JSON"):
            ClaudeExecutor._parse_json(content)

    def test_greedy_brace_match_with_two_objects_raises(self):
        """Greedy brace regex matches from first { to last }, producing invalid JSON."""
        content = 'text {"a": 1} middle {"b": 2}'
        # Greedy match: '{"a": 1} middle {"b": 2}' is not valid JSON → ValueError
        with pytest.raises(ValueError, match="Could not parse JSON"):
            ClaudeExecutor._parse_json(content)

    def test_multiline_json_in_fences(self):
        content = '```json\n{\n  "key": "value",\n  "num": 42\n}\n```'
        result = ClaudeExecutor._parse_json(content)
        assert result == {"key": "value", "num": 42}

    def test_fence_without_json_label(self):
        content = '```\n{"plain": "fence"}\n```'
        result = ClaudeExecutor._parse_json(content)
        assert result == {"plain": "fence"}

    def test_deeply_nested_json(self):
        content = '{"a": {"b": {"c": {"d": [1, {"e": true}]}}}}'
        result = ClaudeExecutor._parse_json(content)
        assert result["a"]["b"]["c"]["d"][1]["e"] is True

    def test_json_with_escaped_quotes(self):
        content = '{"message": "He said \\"hello\\"."}'
        result = ClaudeExecutor._parse_json(content)
        assert result == {"message": 'He said "hello".'}

    def test_truncates_content_in_error_message(self):
        """Error message truncates long content to 500 chars."""
        long_content = "x" * 1000
        with pytest.raises(ValueError) as exc_info:
            ClaudeExecutor._parse_json(long_content)
        assert len(str(exc_info.value)) < 600


class TestExecuteDeeper:
    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_stdin_receives_encoded_prompt(self, mock_exec):
        """Verify the prompt is sent as bytes to stdin."""
        proc = _mock_proc(returncode=0, stdout=b'{"ok": true}')
        mock_exec.return_value = proc
        executor = ClaudeExecutor()
        await executor.execute("Hello world")
        proc.communicate.assert_called_once_with(input=b"Hello world")

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_cli_args_include_required_flags(self, mock_exec):
        """Verify all required CLI flags are present."""
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b'{"ok": true}')
        executor = ClaudeExecutor()
        await executor.execute("prompt")
        args = list(mock_exec.call_args[0])
        assert "claude" in args
        assert "--print" in args
        assert "--max-turns" in args
        assert "1" in args
        assert "--dangerously-skip-permissions" in args
        assert "-" in args

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_default_model_is_opus(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b'{"ok": true}')
        executor = ClaudeExecutor()
        await executor.execute("prompt")
        args = list(mock_exec.call_args[0])
        idx = args.index("--model")
        assert args[idx + 1] == "opus"

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_timeout_passed_to_wait_for(self, mock_exec):
        """Verify the timeout parameter is used in asyncio.wait_for."""
        proc = _mock_proc(returncode=0, stdout=b'{"ok": true}')
        mock_exec.return_value = proc
        executor = ClaudeExecutor()
        with patch("app.core.claude_executor.asyncio.wait_for", new_callable=AsyncMock) as mock_wait:
            mock_wait.return_value = (b'{"ok": true}', b"")
            # Need to also set proc.returncode after wait_for
            await executor.execute("prompt", timeout=60)
            mock_wait.assert_called_once()
            assert mock_wait.call_args[1]["timeout"] == 60

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_response_chars_equals_raw_length(self, mock_exec):
        raw = b'{"result": "some data here"}'
        mock_exec.return_value = _mock_proc(returncode=0, stdout=raw)
        executor = ClaudeExecutor()
        result = await executor.execute("prompt")
        assert result["response_chars"] == result["raw_length"]

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_duration_ms_is_positive(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b'{"ok": true}')
        executor = ClaudeExecutor()
        result = await executor.execute("prompt")
        assert result["duration_ms"] >= 0

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_subprocess_pipes_configured(self, mock_exec):
        """Verify stdin, stdout, stderr are all PIPE."""
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b'{"ok": true}')
        executor = ClaudeExecutor()
        await executor.execute("prompt")
        kwargs = mock_exec.call_args[1]
        assert kwargs["stdin"] == asyncio.subprocess.PIPE
        assert kwargs["stdout"] == asyncio.subprocess.PIPE
        assert kwargs["stderr"] == asyncio.subprocess.PIPE

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_stderr_in_runtime_error(self, mock_exec):
        """Non-zero exit includes stderr text in error message."""
        mock_exec.return_value = _mock_proc(
            returncode=3, stdout=b"", stderr=b"specific error details",
        )
        executor = ClaudeExecutor()
        with pytest.raises(RuntimeError, match="specific error details"):
            await executor.execute("prompt")


class TestModelMap:
    def test_opus_maps_to_opus(self):
        assert ClaudeExecutor.MODEL_MAP["opus"] == "opus"

    def test_sonnet_maps_to_sonnet(self):
        assert ClaudeExecutor.MODEL_MAP["sonnet"] == "sonnet"

    def test_haiku_maps_to_haiku(self):
        assert ClaudeExecutor.MODEL_MAP["haiku"] == "haiku"

    def test_model_map_has_three_entries(self):
        assert len(ClaudeExecutor.MODEL_MAP) == 3

    @patch("app.core.claude_executor.asyncio.create_subprocess_exec")
    async def test_all_mapped_models_resolve(self, mock_exec):
        mock_exec.return_value = _mock_proc(returncode=0, stdout=b'{"ok": true}')
        executor = ClaudeExecutor()
        for model_name in ["opus", "sonnet", "haiku"]:
            await executor.execute("prompt", model=model_name)
            args = list(mock_exec.call_args[0])
            idx = args.index("--model")
            assert args[idx + 1] == model_name
