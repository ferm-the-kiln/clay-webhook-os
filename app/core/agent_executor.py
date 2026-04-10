import asyncio
import json
import logging
import os
import re
import time

from app.core.claude_executor import SubscriptionLimitError
from app.core.telemetry import record_llm_error, record_llm_response, skill_span

logger = logging.getLogger("clay-webhook-os")


class AgentExecutor:
    """Executor for agentic skills that use multi-turn tool calls (WebSearch, WebFetch).

    Uses claude --print with --max-turns > 1 to enable autonomous web research.
    Uses text output (not JSON) to avoid multi-turn envelope bloat, then extracts
    the JSON from Claude's final text response.
    """

    MODEL_MAP = {
        "opus": "opus",
        "sonnet": "sonnet",
        "haiku": "haiku",
    }

    async def execute(
        self,
        prompt: str,
        model: str = "sonnet",
        timeout: int = 300,
        max_turns: int = 5,
        allowed_tools: list[str] | None = None,
        skill_name: str | None = None,
    ) -> dict:
        start = time.monotonic()

        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("CLAUDECODE", "ANTHROPIC_API_KEY")
        }

        resolved_model = self.MODEL_MAP.get(model, model)
        tools = allowed_tools or ["WebSearch", "WebFetch"]
        _span_ctx = skill_span(
            skill=skill_name,
            model=resolved_model,
            prompt=prompt,
            executor="agent",
            extra={"llm.max_turns": max_turns, "llm.tools": ",".join(tools)},
        )
        span = _span_ctx.__enter__()

        # Build args: text output (not json) for agent mode — avoids massive
        # multi-turn JSON envelopes. We parse the JSON from Claude's final text.
        args = [
            "claude",
            "--print",
            "--output-format", "text",
            "--model", resolved_model,
            "--max-turns", str(max_turns),
            "--dangerously-skip-permissions",
        ]

        # Add each tool as a separate --allowedTools arg
        for tool in tools:
            args.extend(["--allowedTools", tool])

        # Read from stdin
        args.append("-")

        logger.info(
            "[agent] Spawning: model=%s, max_turns=%d, tools=%s, timeout=%ds",
            resolved_model, max_turns, tools, timeout,
        )

        try:
            proc = await asyncio.create_subprocess_exec(
                *args,
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )

            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(input=prompt.encode()),
                    timeout=timeout,
                )
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
                elapsed = int((time.monotonic() - start) * 1000)
                logger.error("[agent] Timed out after %ds (elapsed=%dms)", timeout, elapsed)
                exc = TimeoutError(f"Agent timed out after {timeout}s")
                record_llm_error(span, exc)
                raise exc

            duration_ms = int((time.monotonic() - start) * 1000)

            if proc.returncode != 0:
                err = stderr.decode().strip()
                out = stdout.decode().strip()
                logger.error("[agent] Exit code %d, stderr: %s", proc.returncode, err[:500])
                if out:
                    logger.error("[agent] stdout (first 500): %s", out[:500])

                rate_limit_keywords = ["rate limit", "quota", "capacity", "usage limit", "token limit"]
                combined = (err + " " + out).lower()
                is_subscription_issue = (
                    (proc.returncode == 1 and not err)
                    or any(kw in combined for kw in rate_limit_keywords)
                )
                if is_subscription_issue:
                    exc = SubscriptionLimitError(
                        f"Claude subscription limit likely reached (exit code {proc.returncode}). "
                        "Check your Claude Code Max usage."
                    )
                    record_llm_error(span, exc)
                    raise exc

                exc = RuntimeError(f"Agent exited with code {proc.returncode}: {err[:500]}")
                record_llm_error(span, exc)
                raise exc

            raw = stdout.decode().strip()
            if not raw:
                err = stderr.decode().strip()
                logger.error("[agent] Empty stdout. stderr: %s", err[:500])
                exc = RuntimeError("Empty response from agent")
                record_llm_error(span, exc)
                raise exc

            logger.info(
                "[agent] Completed in %dms (model=%s, raw_length=%d)",
                duration_ms, resolved_model, len(raw),
            )

            record_llm_response(span, raw, duration_ms=duration_ms)

            # Text output mode: raw is Claude's final text response containing JSON
            parsed = self._parse_json(raw)

            return {
                "result": parsed,
                "duration_ms": duration_ms,
                "raw_length": len(raw),
                "prompt_chars": len(prompt),
                "response_chars": len(raw),
                "usage": None,  # not available in text output mode
            }
        except Exception:
            raise
        finally:
            _span_ctx.__exit__(None, None, None)

    @staticmethod
    def _parse_json(content: str) -> dict:
        """Extract JSON from agent text response. Tries multiple strategies."""
        # Direct parse (ideal: Claude returned clean JSON)
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            pass

        # Markdown fences
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if fence_match:
            try:
                return json.loads(fence_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Last { ... } block (agent may have reasoning text before the JSON)
        brace_matches = list(re.finditer(r"\{[\s\S]*\}", content))
        if brace_matches:
            # Try the last match first (most likely the final output)
            for match in reversed(brace_matches):
                try:
                    return json.loads(match.group(0))
                except json.JSONDecodeError:
                    continue

        raise ValueError(f"Could not parse JSON from agent response: {content[:500]}")
