"""Free chat proxy — dual-path: Channel server or claude --print fallback.

Primary path: Proxies to the Clay Chat Channel server (localhost:8789)
which runs a persistent Claude Code session via the Channels API.
Claude remembers all prior conversation naturally.

Fallback path: If the channel server isn't running, uses claude --print
with --resume for conversation continuity. Each chat session maps to
a Claude CLI session ID.
"""

import asyncio
import json
import logging
import os
import time
import uuid
from typing import AsyncGenerator

import httpx

from app.config import settings

logger = logging.getLogger("clay-webhook-os")


class ChannelProxy:
    """Dual-path free chat: channel server (preferred) or claude --print (fallback)."""

    SYSTEM_PROMPT = (
        "You are the Clay Webhook OS assistant. You have READ-ONLY access to all project files "
        "including skills, knowledge base, client profiles, functions, and configuration. "
        "Answer questions accurately by reading the relevant files. "
        "Be concise and helpful. Use markdown formatting for readability. "
        "You CANNOT modify any files — only read and search."
    )

    ALLOWED_TOOLS = ["Read", "Grep", "Glob"]

    def __init__(self, base_url: str | None = None):
        self._base_url = base_url or settings.channel_server_url
        self._client = httpx.AsyncClient(base_url=self._base_url, timeout=120.0)
        self._channel_available: bool | None = None  # None = unknown, check on first call

    # ── Health check ──────────────────────────────────────────────

    async def health_check(self) -> dict:
        """Check channel server, fall back to claude --version."""
        # Try channel server first
        channel_status = await self._check_channel_server()
        if channel_status.get("status") == "ok":
            self._channel_available = True
            return {**channel_status, "mode": "channel"}

        # Fall back to claude --print availability
        self._channel_available = False
        cli_status = await self._check_claude_cli()
        return {**cli_status, "mode": "cli_fallback"}

    async def _check_channel_server(self) -> dict:
        try:
            resp = await self._client.get("/health", timeout=5.0)
            resp.raise_for_status()
            return resp.json()
        except Exception:
            return {"status": "unavailable"}

    async def _check_claude_cli(self) -> dict:
        try:
            env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "ANTHROPIC_API_KEY")}
            proc = await asyncio.create_subprocess_exec(
                "claude", "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                env=env,
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            version = stdout.decode().strip()
            return {"status": "ok", "claude_version": version}
        except Exception as e:
            return {"status": "unavailable", "error": str(e)}

    # ── Send message (auto-routes) ────────────────────────────────

    async def send_message(self, chat_id: str, content: str) -> dict:
        """Push a user message — tries channel server, queues for fallback if down."""
        if self._channel_available is None:
            await self.health_check()

        if self._channel_available:
            try:
                resp = await self._client.post(
                    "/message",
                    json={"chat_id": chat_id, "content": content},
                )
                resp.raise_for_status()
                return resp.json()
            except Exception:
                # Channel server went down — switch to fallback
                self._channel_available = False
                logger.warning("[channel-proxy] Channel server down, switching to CLI fallback")

        # Fallback: message will be handled by send_and_get_reply
        return {"ok": True, "chat_id": chat_id, "mode": "cli_fallback"}

    # ── Stream replies (auto-routes) ──────────────────────────────

    async def stream_replies(self, chat_id: str) -> AsyncGenerator[tuple[str, str], None]:
        """Yield (event_type, data_json) — from channel server or empty if using fallback."""
        if self._channel_available:
            try:
                async with self._client.stream("GET", f"/events/{chat_id}") as resp:
                    resp.raise_for_status()
                    current_event = ""
                    async for line in resp.aiter_lines():
                        if line.startswith("event: "):
                            current_event = line[7:].strip()
                        elif line.startswith("data: ") and current_event:
                            yield (current_event, line[6:])
                            current_event = ""
                return
            except Exception as e:
                logger.warning("[channel-proxy] Channel stream failed: %s", e)
                self._channel_available = False

        # Fallback: nothing to stream — caller should use send_cli_fallback instead
        return

    # ── CLI Fallback: claude --print with --resume ────────────────

    async def send_cli_fallback(
        self,
        chat_id: str,
        content: str,
        claude_session_id: str | None = None,
        model: str = "sonnet",
        timeout: int = 120,
    ) -> tuple[str, str]:
        """Fallback: run claude --print with --resume for persistent memory.

        Returns (response_text, claude_session_id).
        """
        start = time.monotonic()
        is_resume = claude_session_id is not None

        env = {k: v for k, v in os.environ.items() if k not in ("CLAUDECODE", "ANTHROPIC_API_KEY")}

        args = [
            "claude",
            "--print",
            "--output-format", "json",
            "--model", model,
            "--max-turns", "5",
            "--dangerously-skip-permissions",
        ]

        if is_resume:
            args.extend(["--resume", claude_session_id])
        else:
            claude_session_id = str(uuid.uuid4())
            args.extend(["--session-id", claude_session_id])
            args.extend(["--system-prompt", self.SYSTEM_PROMPT])

        for tool in self.ALLOWED_TOOLS:
            args.extend(["--allowedTools", tool])

        args.append("-")

        logger.info(
            "[free-chat-cli] Spawning: model=%s, resume=%s, session=%s, timeout=%ds",
            model, is_resume, claude_session_id[:12] if claude_session_id else "new", timeout,
        )

        proc = await asyncio.create_subprocess_exec(
            *args,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=env,
            cwd=str(settings.base_dir),
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=content.encode()),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            logger.error("[free-chat-cli] Timed out after %ds", timeout)
            raise TimeoutError(f"Free chat timed out after {timeout}s")

        duration_ms = int((time.monotonic() - start) * 1000)

        if proc.returncode != 0:
            err = stderr.decode().strip()
            logger.error("[free-chat-cli] Exit code %d: %s", proc.returncode, err[:500])
            raise RuntimeError(f"Free chat failed (exit {proc.returncode}): {err[:300]}")

        raw = stdout.decode().strip()
        if not raw:
            return ("I couldn't generate a response. Please try again.", claude_session_id)

        # Parse JSON output
        result_text = raw
        try:
            data = json.loads(raw)
            result_text = data.get("result", raw)
            returned_session = data.get("session_id")
            if returned_session:
                claude_session_id = returned_session
        except (json.JSONDecodeError, TypeError):
            pass

        logger.info(
            "[free-chat-cli] Completed in %dms (model=%s, resume=%s, chars=%d)",
            duration_ms, model, is_resume, len(result_text),
        )

        return (result_text, claude_session_id)

    # ── Cleanup ───────────────────────────────────────────────────

    async def close(self):
        """Close the underlying HTTP client."""
        await self._client.aclose()
