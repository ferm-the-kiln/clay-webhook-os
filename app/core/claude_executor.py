import asyncio
import json
import logging
import os
import re
import time

logger = logging.getLogger("clay-webhook-os")


class SubscriptionLimitError(RuntimeError):
    """Raised when Claude CLI fails due to subscription quota exhaustion."""
    pass


class ClaudeExecutor:
    MODEL_MAP = {
        "opus": "opus",
        "sonnet": "sonnet",
        "haiku": "haiku",
    }

    async def execute(
        self, prompt: str, model: str = "opus", timeout: int = 120,
        raw_mode: bool = False,
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
            "--output-format", "text",
            "--model", resolved_model,
            "--max-turns", "1",
            "--dangerously-skip-permissions",
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
            out = stdout.decode().strip()
            logger.error("claude stderr: %s", err)

            # Only flag subscription issues when rate limit keywords are present
            rate_limit_keywords = ["rate limit", "quota", "capacity", "usage limit", "token limit"]
            combined = (err + " " + out).lower()
            if any(kw in combined for kw in rate_limit_keywords):
                raise SubscriptionLimitError(
                    f"Claude subscription limit likely reached (exit code {proc.returncode}). "
                    "Check your Claude Code Max usage."
                )

            # Include stdout in error when stderr is empty (CLI often reports errors there)
            detail = err or out[:500] or "no output"
            raise RuntimeError(f"claude exited with code {proc.returncode}: {detail}")

        raw = stdout.decode().strip()
        if not raw:
            raise RuntimeError("Empty response from claude")

        duration_ms = int((time.monotonic() - start) * 1000)

        if raw_mode:
            return {
                "result": raw,
                "raw_output": raw,
                "duration_ms": duration_ms,
                "raw_length": len(raw),
                "prompt_chars": len(prompt),
                "response_chars": len(raw),
                "usage": None,
            }

        parsed = self._parse_json(raw)

        return {
            "result": parsed,
            "duration_ms": duration_ms,
            "raw_length": len(raw),
            "prompt_chars": len(prompt),
            "response_chars": len(raw),
            "usage": None,
        }

    async def stream_execute(
        self, prompt: str, model: str = "opus", timeout: int = 120,
    ):
        """Yield chunks from claude stdout as they arrive."""
        start = time.monotonic()

        env = {
            k: v
            for k, v in os.environ.items()
            if k not in ("CLAUDECODE", "ANTHROPIC_API_KEY")
        }

        resolved_model = self.MODEL_MAP.get(model, model)
        args = [
            "claude", "--print", "--output-format", "text",
            "--model", resolved_model, "--max-turns", "1",
            "--dangerously-skip-permissions", "-",
        ]

        proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
        )

        # Write prompt and close stdin
        proc.stdin.write(prompt.encode())
        await proc.stdin.drain()
        proc.stdin.close()

        # Stream stdout chunks
        full_output = []
        try:
            while True:
                chunk = await asyncio.wait_for(proc.stdout.read(1024), timeout=timeout)
                if not chunk:
                    break
                text = chunk.decode()
                full_output.append(text)
                yield {"chunk": text, "done": False}
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            yield {"error": f"Timed out after {timeout}s", "done": True}
            return

        await proc.wait()
        duration_ms = int((time.monotonic() - start) * 1000)
        raw = "".join(full_output).strip()

        if proc.returncode != 0:
            stderr = (await proc.stderr.read()).decode().strip()
            yield {"error": f"Exit code {proc.returncode}: {stderr}", "done": True}
            return

        # Final result with parsed JSON
        try:
            parsed = self._parse_json(raw)
            yield {"result": parsed, "duration_ms": duration_ms, "done": True}
        except ValueError:
            yield {"result": raw, "duration_ms": duration_ms, "done": True}

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
