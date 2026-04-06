"""Sandboxed script executor for script column type.

Executes Python/Bash/Node scripts in subprocess with row data on stdin,
parses JSON output from stdout.
"""

import asyncio
import json
import logging
import shlex
import tempfile
from pathlib import Path

logger = logging.getLogger("clay-webhook-os")

# Language → interpreter command
_INTERPRETERS = {
    "python": "/opt/homebrew/bin/python3.11",
    "bash": "/bin/bash",
    "node": "node",
}


def _shell_escape(value: str) -> str:
    """Shell-escape a value to prevent injection."""
    return shlex.quote(value)


async def execute_script(
    code: str,
    language: str,
    row_data: dict,
    timeout: int = 30,
) -> dict | str | list | None:
    """Execute a script with row data piped as JSON on stdin.

    Returns parsed JSON from stdout, or raw string if not valid JSON.
    Raises RuntimeError on failure or timeout.
    """
    interpreter = _INTERPRETERS.get(language)
    if not interpreter:
        raise ValueError(f"Unsupported script language: {language}")

    # Write script to temp file (avoids shell injection via code content)
    with tempfile.NamedTemporaryFile(
        mode="w",
        suffix=f".{_ext(language)}",
        delete=False,
    ) as f:
        f.write(code)
        script_path = f.name

    try:
        # Serialize row data as JSON for stdin
        stdin_data = json.dumps(row_data).encode()

        proc = await asyncio.create_subprocess_exec(
            interpreter, script_path,
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            env=_safe_env(),
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(input=stdin_data),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.wait()
            raise RuntimeError(f"Script timed out after {timeout}s")

        if proc.returncode != 0:
            err_text = stderr.decode(errors="replace").strip()[:500]
            raise RuntimeError(f"Script exited with code {proc.returncode}: {err_text}")

        output = stdout.decode(errors="replace").strip()
        if not output:
            return None

        # Try JSON parse
        try:
            return json.loads(output)
        except json.JSONDecodeError:
            return output

    finally:
        Path(script_path).unlink(missing_ok=True)


def _ext(language: str) -> str:
    return {"python": "py", "bash": "sh", "node": "js"}.get(language, "txt")


def _safe_env() -> dict[str, str]:
    """Build a minimal environment for script execution."""
    import os
    return {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ.get("HOME", "/tmp"),
        "LANG": "en_US.UTF-8",
    }
