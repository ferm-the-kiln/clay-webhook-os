import asyncio
import json
import logging
import os
import re
import time

logger = logging.getLogger("clay-webhook-os")


class ClaudeExecutor:
    MODEL_MAP = {
        "opus": "opus",
        "sonnet": "sonnet",
        "haiku": "haiku",
    }

    async def execute(
        self, prompt: str, model: str = "opus", timeout: int = 120
    ) -> dict:
        start = time.monotonic()

        # Clean env: remove CLAUDECODE so nested claude doesn't conflict,
        # and remove ANTHROPIC_API_KEY so it uses Max subscription auth.
        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("CLAUDECODE", "ANTHROPIC_API_KEY")
        }

        resolved_model = self.MODEL_MAP.get(model, model)

        args = [
            "claude",
            "--print",
            "--output-format", "json",
            "--model", resolved_model,
            "--max-turns", "1",
            "-",
        ]

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
            raise TimeoutError(f"claude --print timed out after {timeout}s")

        if proc.returncode != 0:
            err = stderr.decode().strip()
            logger.error("claude stderr: %s", err)
            raise RuntimeError(f"claude exited with code {proc.returncode}: {err}")

        raw = stdout.decode().strip()
        if not raw:
            raise RuntimeError("Empty response from claude")

        duration_ms = int((time.monotonic() - start) * 1000)

        # --output-format json gives us a structured envelope from the CLI.
        # Parse the envelope first, then extract Claude's content.
        envelope = json.loads(raw)
        content = self._extract_content(envelope)
        parsed = self._parse_json(content)

        # Token usage: prefer real data from CLI if available, else return char counts for estimation
        usage = envelope.get("usage") if isinstance(envelope, dict) else None

        return {
            "result": parsed,
            "duration_ms": duration_ms,
            "raw_length": len(raw),
            "prompt_chars": len(prompt),
            "response_chars": len(content),
            "usage": usage,
        }

    @staticmethod
    def _extract_content(envelope: dict | list) -> str:
        """Extract the text content from the CLI JSON envelope."""
        # --print with --output-format json returns a list of content blocks
        if isinstance(envelope, list):
            parts = []
            for block in envelope:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(block.get("text", ""))
            if parts:
                return "\n".join(parts)

        # Single object with a "result" key
        if isinstance(envelope, dict):
            if "result" in envelope:
                return str(envelope["result"])
            if "text" in envelope:
                return str(envelope["text"])
            if "content" in envelope:
                return str(envelope["content"])

        # Fallback: re-serialize and let _parse_json handle it
        return json.dumps(envelope)

    @staticmethod
    def _parse_json(content: str) -> dict:
        # Try direct parse first (ideal case: Claude returned clean JSON)
        try:
            return json.loads(content)
        except (json.JSONDecodeError, TypeError):
            pass

        # Try extracting from markdown fences
        fence_match = re.search(r"```(?:json)?\s*([\s\S]*?)```", content)
        if fence_match:
            try:
                return json.loads(fence_match.group(1).strip())
            except json.JSONDecodeError:
                pass

        # Try finding the first { ... } block
        brace_match = re.search(r"\{[\s\S]*\}", content)
        if brace_match:
            try:
                return json.loads(brace_match.group(0))
            except json.JSONDecodeError:
                pass

        raise ValueError(f"Could not parse JSON from response: {content[:500]}")
