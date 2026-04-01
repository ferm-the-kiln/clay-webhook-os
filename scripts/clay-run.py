#!/usr/bin/env python3
"""clay-run — Local CLI runner for Clay Webhook OS functions.

Fetches assembled prompts from the server, runs them in Claude Code
on your local machine, and posts results back.

Usage:
    clay-run <function-id> --data '{"company": "Acme"}'   # one-off run
    clay-run <function-id> --data '...' --dry-run          # show prompt only
    clay-run <function-id> --csv leads.csv                 # batch from CSV
    clay-run --watch                                       # pick up queued jobs
    clay-run --setup                                       # configure server URL + API key
    clay-run --list                                        # list available functions

Requires: requests (pip install requests)
"""

import argparse
import csv
import json
import os
import platform
import subprocess
import sys
import time
from pathlib import Path

try:
    import requests
except ImportError:
    print("Error: 'requests' package required. Run: pip install requests")
    sys.exit(1)

CONFIG_PATH = Path.home() / ".clay-run.json"
DEFAULT_SERVER = "https://clay.nomynoms.com"


# ── Config ────────────────────────────────────────────────


def _load_dotenv() -> dict[str, str]:
    """Read .env file from project root (simple key=value parser)."""
    env_vals: dict[str, str] = {}
    # Walk up from script location to find .env
    script_dir = Path(__file__).resolve().parent
    for candidate in [script_dir.parent, Path.cwd()]:
        env_path = candidate / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                line = line.strip()
                if not line or line.startswith("#"):
                    continue
                if "=" in line:
                    key, _, val = line.partition("=")
                    env_vals[key.strip()] = val.strip()
            break
    return env_vals


def load_config() -> dict:
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def save_config(config: dict) -> None:
    CONFIG_PATH.write_text(json.dumps(config, indent=2))
    print(f"Config saved to {CONFIG_PATH}")


def get_config() -> dict:
    config = load_config()

    # Auto-detect from .env if no saved config
    if not config.get("server_url") or not config.get("api_key"):
        dotenv = _load_dotenv()
        api_key = dotenv.get("WEBHOOK_API_KEY", "")
        if api_key and api_key != "change-me":
            config.setdefault("server_url", DEFAULT_SERVER)
            config["api_key"] = api_key
            return config

    if not config.get("server_url") or not config.get("api_key"):
        print("clay-run is not configured.")
        print("  Option 1: Set WEBHOOK_API_KEY in your .env file")
        print("  Option 2: Run: clay-run --setup")
        sys.exit(1)
    return config


def setup_interactive() -> None:
    config = load_config()
    print("=== clay-run setup ===\n")

    server = input(f"Server URL [{config.get('server_url', DEFAULT_SERVER)}]: ").strip()
    if not server:
        server = config.get("server_url", DEFAULT_SERVER)

    api_key = input(f"API Key [{config.get('api_key', '')}]: ").strip()
    if not api_key:
        api_key = config.get("api_key", "")

    if not api_key:
        print("Error: API key is required.")
        sys.exit(1)

    config["server_url"] = server.rstrip("/")
    config["api_key"] = api_key
    save_config(config)
    print("\nDone! Test with: clay-run --list")


# ── API Client ────────────────────────────────────────────


class ClayClient:
    def __init__(self, server_url: str, api_key: str):
        self.base = server_url
        self.headers = {"x-api-key": api_key, "Content-Type": "application/json"}

    def list_functions(self) -> list[dict]:
        r = requests.get(f"{self.base}/functions", headers=self.headers)
        r.raise_for_status()
        data = r.json()
        return data.get("functions", data) if isinstance(data, dict) else data

    def queue_local(self, func_id: str, data: dict, instructions: str | None = None,
                    model: str | None = None) -> dict:
        body: dict = {"data": data}
        if instructions:
            body["instructions"] = instructions
        if model:
            body["model"] = model
        r = requests.post(f"{self.base}/functions/{func_id}/queue-local",
                          headers=self.headers, json=body)
        r.raise_for_status()
        return r.json()

    def prepare_consolidated(self, func_id: str, data: dict, instructions: str | None = None,
                             model: str | None = None) -> dict:
        body: dict = {"data": data}
        if instructions:
            body["instructions"] = instructions
        if model:
            body["model"] = model
        r = requests.post(f"{self.base}/functions/{func_id}/prepare-consolidated",
                          headers=self.headers, json=body)
        r.raise_for_status()
        return r.json()

    def submit_result(self, func_id: str, job_id: str, result: dict,
                      duration_ms: int | None = None) -> dict:
        body: dict = {"job_id": job_id, "result": result}
        if duration_ms is not None:
            body["duration_ms"] = duration_ms
        r = requests.post(f"{self.base}/functions/{func_id}/submit-result",
                          headers=self.headers, json=body)
        r.raise_for_status()
        return r.json()

    def list_pending_jobs(self) -> list[dict]:
        r = requests.get(f"{self.base}/functions/local-queue",
                         headers=self.headers, params={"status": "pending"})
        r.raise_for_status()
        return r.json().get("jobs", [])

    def get_job(self, job_id: str) -> dict:
        r = requests.get(f"{self.base}/functions/local-queue/{job_id}",
                         headers=self.headers)
        r.raise_for_status()
        return r.json()

    def update_job_status(self, job_id: str, status: str) -> dict:
        r = requests.patch(f"{self.base}/functions/local-queue/{job_id}",
                           headers=self.headers, json={"status": status})
        r.raise_for_status()
        return r.json()

    def push_logs(self, job_id: str, entries: list[dict]) -> None:
        """Push log entries to the backend for live dashboard display."""
        try:
            requests.post(
                f"{self.base}/functions/local-queue/{job_id}/log",
                headers=self.headers, json={"entries": entries}, timeout=5,
            )
        except Exception:
            pass  # Non-critical — execution continues even if log push fails


# ── Claude Code Execution ─────────────────────────────────


def run_claude(prompt: str, model: str = "sonnet") -> tuple[str, float]:
    """Run prompt through Claude Code using -p flag. Returns (output, duration_ms)."""
    start = time.time()

    cmd = ["claude", "-p", "--output-format", "text", "--model", model]

    # Remove ANTHROPIC_API_KEY so claude -p uses Max subscription (OAuth) instead of API credits
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "CLAUDECODE")}

    try:
        proc = subprocess.run(
            cmd,
            input=prompt,
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )
    except FileNotFoundError:
        print("Error: 'claude' CLI not found. Install Claude Code first.")
        sys.exit(1)
    except subprocess.TimeoutExpired:
        print("Error: Claude Code timed out after 300s.")
        return "", (time.time() - start) * 1000

    duration_ms = (time.time() - start) * 1000

    if proc.returncode != 0:
        stderr = proc.stderr.strip()
        if any(kw in stderr.lower() for kw in ["rate limit", "quota", "capacity"]):
            print(f"Error: Subscription limit reached. Wait and retry.\n  {stderr}")
        else:
            print(f"Error: Claude Code exited with code {proc.returncode}")
            if stderr:
                print(f"  stderr: {stderr[:500]}")
        return "", duration_ms

    return proc.stdout.strip(), duration_ms


def parse_json_output(text: str) -> dict | None:
    """Extract JSON from Claude's response. Handles markdown fences."""
    # Try direct parse first
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass

    # Try extracting from markdown code fence
    import re
    patterns = [
        r"```json\s*\n(.*?)\n\s*```",
        r"```\s*\n(.*?)\n\s*```",
        r"\{[\s\S]*\}",
    ]
    for pattern in patterns:
        match = re.search(pattern, text, re.DOTALL)
        if match:
            candidate = match.group(1) if match.lastindex else match.group(0)
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                continue

    return None


# ── Streaming Execution ──────────────────────────────────


def format_stream_event(event: dict, start_time: float) -> dict | None:
    """Parse a stream-json event into a human-readable log entry."""
    elapsed = int((time.time() - start_time) * 1000)
    etype = event.get("type", "")
    subtype = event.get("subtype", "")

    if etype == "system" and subtype == "init":
        model = event.get("model", "unknown")
        return {"elapsed_ms": elapsed, "type": "init", "message": f"Session started (model: {model})"}

    if etype == "assistant":
        msg = event.get("message", {})
        content = msg.get("content", [])
        for block in content:
            btype = block.get("type", "")

            if btype == "tool_use":
                name = block.get("name", "unknown")
                inp = block.get("input", {})
                # Extract the most useful param for display
                detail = inp.get("query") or inp.get("url") or inp.get("command") or inp.get("pattern") or ""
                if isinstance(detail, str) and len(detail) > 120:
                    detail = detail[:120] + "..."
                return {"elapsed_ms": elapsed, "type": "tool_use", "message": f"{name}: {detail}" if detail else name}

            if btype == "tool_result":
                content_text = block.get("content", "")
                if isinstance(content_text, str):
                    preview = content_text[:80].replace("\n", " ")
                    return {"elapsed_ms": elapsed, "type": "tool_result", "message": f"Got result ({len(content_text)} chars)"}
                return {"elapsed_ms": elapsed, "type": "tool_result", "message": "Got result"}

            if btype == "text":
                text = block.get("text", "")
                if len(text) > 5:  # Skip tiny fragments
                    preview = text[:100].replace("\n", " ").strip()
                    return {"elapsed_ms": elapsed, "type": "text", "message": preview}

        # Check for errors in the message
        error = event.get("error")
        if error:
            error_text = msg.get("content", [{}])[0].get("text", str(error)) if content else str(error)
            return {"elapsed_ms": elapsed, "type": "error", "message": error_text[:200]}

    if etype == "result":
        duration = event.get("duration_ms", 0)
        result_text = event.get("result", "")
        is_error = event.get("is_error", False)
        if is_error:
            return {"elapsed_ms": elapsed, "type": "error", "message": str(result_text)[:200]}
        # Try to count output fields
        try:
            parsed = json.loads(result_text) if isinstance(result_text, str) else result_text
            field_count = len(parsed) if isinstance(parsed, dict) else 0
            return {"elapsed_ms": elapsed, "type": "result", "message": f"Done — {field_count} fields ({duration / 1000:.1f}s)"}
        except (json.JSONDecodeError, TypeError):
            return {"elapsed_ms": elapsed, "type": "result", "message": f"Done ({duration / 1000:.1f}s)"}

    return None


def run_claude_streaming(
    prompt: str, model: str, job_id: str, client: "ClayClient",
) -> tuple[str, float]:
    """Run prompt through Claude Code with streaming output.

    Uses Popen + stream-json to capture events line-by-line and push
    them to the backend for live dashboard display.
    Returns (final_output_text, duration_ms).
    """
    start = time.time()
    cmd = [
        "claude", "-p",
        "--output-format", "stream-json",
        "--verbose",
        "--model", model,
    ]
    env = {k: v for k, v in os.environ.items() if k not in ("ANTHROPIC_API_KEY", "CLAUDECODE")}

    try:
        proc = subprocess.Popen(
            cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
            stderr=subprocess.PIPE, text=True, env=env,
        )
    except FileNotFoundError:
        client.push_logs(job_id, [{"elapsed_ms": 0, "type": "error", "message": "claude CLI not found — install Claude Code"}])
        return "", 0

    proc.stdin.write(prompt)
    proc.stdin.close()

    final_text = ""
    all_text_chunks: list[str] = []  # Collect all assistant text for JSON extraction
    batch: list[dict] = []
    BATCH_SIZE = 3

    for line in proc.stdout:
        line = line.strip()
        if not line:
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue

        entry = format_stream_event(event, start)
        if entry:
            batch.append(entry)
            if len(batch) >= BATCH_SIZE:
                client.push_logs(job_id, batch)
                batch = []

        # Collect all text content from assistant messages (JSON is here)
        if event.get("type") == "assistant":
            for block in event.get("message", {}).get("content", []):
                if block.get("type") == "text":
                    all_text_chunks.append(block["text"])

        # Also capture the result event's text
        if event.get("type") == "result":
            result_text = event.get("result", "")
            if result_text:
                all_text_chunks.append(result_text)

    # Flush remaining batch
    if batch:
        client.push_logs(job_id, batch)

    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()

    duration_ms = (time.time() - start) * 1000

    # Build final text from all collected chunks — try each for valid JSON
    # Check result text first, then concatenated chunks, then individual chunks
    combined = "\n".join(all_text_chunks)
    final_text = combined

    # If no text captured, check stderr
    if not final_text:
        stderr = proc.stderr.read().strip() if proc.stderr else ""
        if stderr:
            client.push_logs(job_id, [{"elapsed_ms": int(duration_ms), "type": "error", "message": stderr[:200]}])

    return final_text, duration_ms


# ── Commands ──────────────────────────────────────────────


def cmd_run(client: ClayClient, func_id: str, data: dict, instructions: str | None = None,
            model: str | None = None, dry_run: bool = False) -> dict | None:
    """Run a single function execution."""
    if dry_run:
        print(f"Fetching prompt for {func_id}...")
        result = client.prepare_consolidated(func_id, data, instructions, model)
        print(f"\n{'='*60}")
        print(f"Function: {result.get('function_name', func_id)}")
        print(f"Model: {result.get('model', 'sonnet')}")
        print(f"Prompt chars: {len(result.get('prompt', ''))}")
        print(f"Output keys: {', '.join(result.get('output_keys', []))}")
        print(f"{'='*60}\n")
        print(result.get("prompt", ""))
        return None

    # Queue the job
    print(f"Queuing {func_id}...")
    job = client.queue_local(func_id, data, instructions, model)
    job_id = job["job_id"]
    prompt = job["prompt"]

    print(f"  Job: {job_id}")
    print(f"  Model: {job['model']}")
    print(f"  Prompt: {job.get('prompt_chars', len(prompt))} chars (~{job.get('prompt_tokens_est', len(prompt)//4)} tokens)")
    print(f"  Expected outputs: {', '.join(job.get('output_keys', []))}")

    if job.get("native_results"):
        print(f"  Native API results: {len(job['native_results'])} fields pre-fetched")

    # Mark as running
    client.update_job_status(job_id, "running")

    # Run in Claude Code
    print(f"\nRunning in Claude Code ({job['model']})...")
    output, duration_ms = run_claude(prompt, model=job["model"])

    if not output:
        client.update_job_status(job_id, "failed")
        print("Failed: No output from Claude Code.")
        return None

    # Parse JSON
    result = parse_json_output(output)
    if result is None:
        print(f"\nWarning: Could not parse JSON from output. Raw output:\n{output[:1000]}")
        client.update_job_status(job_id, "failed")
        return None

    # Submit result
    print(f"Submitting result...")
    response = client.submit_result(func_id, job_id, result, int(duration_ms))

    print(f"\n{'='*60}")
    print(f"  Status: saved")
    print(f"  Exec ID: {response.get('exec_id')}")
    print(f"  Duration: {duration_ms/1000:.1f}s")
    if response.get("warnings"):
        for w in response["warnings"]:
            print(f"  Warning: {w}")
    print(f"{'='*60}")
    print(f"\nResult:")
    print(json.dumps(result, indent=2)[:2000])

    return result


def cmd_watch(client: ClayClient) -> None:
    """Watch mode: poll for pending jobs and execute them."""
    print("Watching for local execution jobs... (Ctrl+C to stop)\n")
    while True:
        try:
            jobs = client.list_pending_jobs()
            if jobs:
                job_summary = jobs[0]
                print(f"\nPicked up: {job_summary['function_name']} ({job_summary['id']})")

                # Fetch full job with prompt
                job = client.get_job(job_summary["id"])
                client.update_job_status(job["id"], "running")

                # Execute
                print(f"  Running in Claude Code ({job['model']})...")
                output, duration_ms = run_claude(job["prompt"], model=job["model"])

                if not output:
                    client.update_job_status(job["id"], "failed")
                    print("  Failed: No output.")
                    continue

                result = parse_json_output(output)
                if result is None:
                    print(f"  Failed: Could not parse JSON.")
                    client.update_job_status(job["id"], "failed")
                    continue

                response = client.submit_result(
                    job["function_id"], job["id"], result, int(duration_ms)
                )
                print(f"  Done in {duration_ms/1000:.1f}s — saved as {response.get('exec_id')}")
            else:
                sys.stdout.write(".")
                sys.stdout.flush()

            time.sleep(5)

        except KeyboardInterrupt:
            print("\n\nStopped watching.")
            break
        except Exception as e:
            print(f"\nError: {e}")
            time.sleep(10)


def cmd_daemon(client: ClayClient) -> None:
    """Daemon mode: same as watch but logs to file, runs silently in background."""
    import logging

    log_path = os.path.expanduser("~/Library/Logs/clay-run.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    logging.basicConfig(
        filename=log_path,
        level=logging.INFO,
        format="%(asctime)s [clay-run] %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )
    log = logging.getLogger("clay-run")

    pid_path = os.path.expanduser("~/.clay-run.pid")
    with open(pid_path, "w") as f:
        f.write(str(os.getpid()))

    heartbeat_path = os.path.expanduser("~/.clay-run-heartbeat")

    log.info("Daemon started (PID %d)", os.getpid())

    while True:
        try:
            # Write heartbeat timestamp
            with open(heartbeat_path, "w") as f:
                f.write(str(time.time()))

            jobs = client.list_pending_jobs()
            if jobs:
                job_summary = jobs[0]
                log.info("Picked up: %s (%s)", job_summary["function_name"], job_summary["id"])

                job = client.get_job(job_summary["id"])
                client.update_job_status(job["id"], "running")

                log.info("Streaming execution in Claude Code (%s)...", job["model"])
                output, duration_ms = run_claude_streaming(
                    job["prompt"], job["model"], job["id"], client,
                )

                if not output:
                    client.update_job_status(job["id"], "failed")
                    log.warning("Failed: No output for job %s", job["id"])
                    continue

                result = parse_json_output(output)
                if result is None:
                    client.update_job_status(job["id"], "failed")
                    log.warning("Failed: Could not parse JSON for job %s", job["id"])
                    continue

                response = client.submit_result(
                    job["function_id"], job["id"], result, int(duration_ms)
                )
                log.info("Done in %.1fs — saved as %s", duration_ms / 1000, response.get("exec_id"))

            time.sleep(5)

        except KeyboardInterrupt:
            log.info("Daemon stopped")
            break
        except Exception as e:
            log.error("Error: %s", e)
            time.sleep(10)

    # Clean up PID file
    try:
        os.remove(pid_path)
    except OSError:
        pass


def cmd_batch(client: ClayClient, func_id: str, csv_path: str,
              instructions: str | None = None, model: str | None = None) -> None:
    """Batch mode: process CSV rows one at a time."""
    path = Path(csv_path)
    if not path.exists():
        print(f"Error: File not found: {csv_path}")
        sys.exit(1)

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    if not rows:
        print("Error: CSV is empty.")
        sys.exit(1)

    print(f"Processing {len(rows)} rows from {path.name}\n")

    results = []
    success = 0
    errors = 0
    start_all = time.time()

    for i, row in enumerate(rows):
        # Clean up empty values
        data = {k: v for k, v in row.items() if v}
        label = data.get("company") or data.get("name") or data.get("domain") or f"row {i+1}"
        print(f"[{i+1}/{len(rows)}] {label}...", end=" ", flush=True)

        try:
            result = cmd_run(client, func_id, data, instructions, model)
            if result:
                results.append({**data, **result, "_status": "success"})
                success += 1
                print("done")
            else:
                results.append({**data, "_status": "error"})
                errors += 1
                print("failed")
        except Exception as e:
            results.append({**data, "_status": "error", "_error": str(e)})
            errors += 1
            print(f"error: {e}")

    total_time = time.time() - start_all

    # Write output CSV
    output_path = path.with_stem(f"{path.stem}_output")
    if results:
        all_keys = []
        for r in results:
            for k in r.keys():
                if k not in all_keys:
                    all_keys.append(k)

        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_keys)
            writer.writeheader()
            writer.writerows(results)

    print(f"\n{'='*60}")
    print(f"  Rows: {len(rows)}")
    print(f"  Success: {success}")
    print(f"  Errors: {errors}")
    print(f"  Total time: {total_time:.1f}s")
    print(f"  Avg per row: {total_time/len(rows):.1f}s")
    if results:
        print(f"  Output: {output_path}")
    print(f"{'='*60}")


def cmd_list(client: ClayClient) -> None:
    """List available functions."""
    functions = client.list_functions()
    if not functions:
        print("No functions found.")
        return

    print(f"\n{'='*60}")
    print(f"  Available Functions ({len(functions)})")
    print(f"{'='*60}\n")

    for func in functions:
        fid = func.get("id", "?")
        name = func.get("name", "Untitled")
        desc = func.get("description", "")[:60]
        inputs = [i.get("name") for i in func.get("inputs", [])]
        outputs = [o.get("key") for o in func.get("outputs", [])]
        print(f"  {fid}")
        print(f"    Name: {name}")
        if desc:
            print(f"    Desc: {desc}")
        if inputs:
            print(f"    Inputs: {', '.join(inputs)}")
        if outputs:
            print(f"    Outputs: {', '.join(outputs)}")
        print()


def cmd_open_terminal(prompt: str, model: str = "sonnet") -> None:
    """Open a new terminal tab with the Claude Code command (macOS only)."""
    if platform.system() != "Darwin":
        print("Terminal auto-open is only supported on macOS.")
        print("Run manually: claude -p '<prompt>'")
        return

    # Write prompt to a temp file to avoid shell escaping issues
    import tempfile
    tmp = tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False, prefix="clay-prompt-")
    tmp.write(prompt)
    tmp.close()

    cmd = f'cat "{tmp.name}" | claude -p --output-format text --model {model}'

    # Try iTerm2 first, fall back to Terminal.app
    iterm_script = f'''
tell application "iTerm2"
    create window with default profile
    tell current session of current window
        write text "{cmd}"
    end tell
end tell
'''
    terminal_script = f'''
tell application "Terminal"
    do script "{cmd}"
    activate
end tell
'''

    try:
        subprocess.run(["osascript", "-e", iterm_script], capture_output=True, timeout=5)
        print(f"Opened in iTerm2. Prompt saved to {tmp.name}")
    except Exception:
        try:
            subprocess.run(["osascript", "-e", terminal_script], capture_output=True, timeout=5)
            print(f"Opened in Terminal.app. Prompt saved to {tmp.name}")
        except Exception as e:
            print(f"Could not open terminal: {e}")
            print(f"Run manually: {cmd}")


# ── Main ──────────────────────────────────────────────────


def main():
    parser = argparse.ArgumentParser(
        description="Clay Webhook OS — Local function runner",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  clay-run func-email-gen --data '{"company": "Acme", "domain": "acme.com"}'
  clay-run func-email-gen --data '{"company": "Acme"}' --dry-run
  clay-run func-email-gen --csv leads.csv
  clay-run --watch
  clay-run --list
  clay-run --setup
        """,
    )

    parser.add_argument("function_id", nargs="?", help="Function ID to execute")
    parser.add_argument("--data", help="Input data as JSON string")
    parser.add_argument("--csv", dest="csv_path", help="CSV file for batch processing")
    parser.add_argument("--instructions", help="Campaign instructions")
    parser.add_argument("--model", help="Model override (opus/sonnet/haiku)")
    parser.add_argument("--dry-run", action="store_true", help="Show prompt without executing")
    parser.add_argument("--watch", action="store_true", help="Watch for queued jobs")
    parser.add_argument("--daemon", action="store_true", help="Background daemon mode (logs to ~/Library/Logs/clay-run.log)")
    parser.add_argument("--list", action="store_true", help="List available functions")
    parser.add_argument("--setup", action="store_true", help="Configure server URL and API key")
    parser.add_argument("--open", action="store_true", help="Open in a new terminal tab (macOS)")

    args = parser.parse_args()

    # Setup mode
    if args.setup:
        setup_interactive()
        return

    # Need config for everything else
    config = get_config()
    client = ClayClient(config["server_url"], config["api_key"])

    # List functions
    if args.list:
        cmd_list(client)
        return

    # Watch mode
    if args.watch:
        cmd_watch(client)
        return

    # Daemon mode (background)
    if args.daemon:
        cmd_daemon(client)
        return

    # Need function_id for remaining commands
    if not args.function_id:
        parser.print_help()
        sys.exit(1)

    # Parse data
    data = {}
    if args.data:
        try:
            data = json.loads(args.data)
        except json.JSONDecodeError as e:
            print(f"Error: Invalid JSON in --data: {e}")
            sys.exit(1)

    # Open in terminal mode
    if args.open:
        result = client.prepare_consolidated(args.function_id, data, args.instructions, args.model)
        cmd_open_terminal(result["prompt"], model=result.get("model", "sonnet"))
        return

    # Batch CSV mode
    if args.csv_path:
        cmd_batch(client, args.function_id, args.csv_path, args.instructions, args.model)
        return

    # Single run
    if not data and not args.dry_run:
        print("Error: --data is required for single runs (or use --dry-run)")
        sys.exit(1)

    cmd_run(client, args.function_id, data, args.instructions, args.model, args.dry_run)


if __name__ == "__main__":
    main()
