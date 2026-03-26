/**
 * Local executor — runs prompts via `claude --print` directly from the
 * dashboard's Node.js process, bypassing the Python backend for AI steps.
 *
 * Uses the same Max subscription as the CLI. Only works when `claude` is
 * installed on the machine (local dev mode, not Vercel).
 */

import { spawn } from "child_process";

// ── Types ───────────────────────────────────────────────

export interface ExecuteOptions {
  model?: string;
  timeout?: number;
  maxTurns?: number;
  allowedTools?: string[];
}

export interface ExecuteResult {
  result: Record<string, unknown>;
  raw: string;
  durationMs: number;
}

// ── JSON parsing (mirrors ClaudeExecutor._parse_json) ───

function parseJsonResponse(raw: string): Record<string, unknown> {
  // 1. Direct parse
  try {
    return JSON.parse(raw);
  } catch {
    // continue
  }

  // 2. Extract from markdown fences
  const fenceMatch = raw.match(/```(?:json)?\s*([\s\S]*?)```/);
  if (fenceMatch) {
    try {
      return JSON.parse(fenceMatch[1].trim());
    } catch {
      // continue
    }
  }

  // 3. Find first { ... } block
  const braceMatch = raw.match(/\{[\s\S]*\}/);
  if (braceMatch) {
    try {
      return JSON.parse(braceMatch[0]);
    } catch {
      // continue
    }
  }

  throw new Error(
    `Could not parse JSON from response: ${raw.slice(0, 500)}`
  );
}

// ── Core executor ───────────────────────────────────────

export async function executePrompt(
  prompt: string,
  options: ExecuteOptions = {}
): Promise<ExecuteResult> {
  const {
    model = "sonnet",
    timeout = 120_000,
    maxTurns = 1,
    allowedTools,
  } = options;

  const args = [
    "--print",
    "--output-format",
    "text",
    "--model",
    model,
    "--max-turns",
    String(maxTurns),
    "--dangerously-skip-permissions",
  ];

  if (allowedTools?.length) {
    for (const tool of allowedTools) {
      args.push("--allowedTools", tool);
    }
  }

  // Read prompt from stdin
  args.push("-");

  const start = Date.now();

  return new Promise<ExecuteResult>((resolve, reject) => {
    // Clean env — remove CLAUDECODE and ANTHROPIC_API_KEY so it uses Max subscription
    const env = { ...process.env };
    delete env.CLAUDECODE;
    delete env.ANTHROPIC_API_KEY;

    const proc = spawn("claude", args, {
      env,
      stdio: ["pipe", "pipe", "pipe"],
    });

    const stdout: Buffer[] = [];
    const stderr: Buffer[] = [];

    proc.stdout.on("data", (chunk: Buffer) => stdout.push(chunk));
    proc.stderr.on("data", (chunk: Buffer) => stderr.push(chunk));

    const timer = setTimeout(() => {
      proc.kill("SIGKILL");
      reject(new Error(`claude --print timed out after ${timeout}ms`));
    }, timeout);

    proc.on("close", (code) => {
      clearTimeout(timer);
      const durationMs = Date.now() - start;
      const raw = Buffer.concat(stdout).toString().trim();
      const errText = Buffer.concat(stderr).toString().trim();

      if (code !== 0) {
        // Check for subscription limit keywords
        const combined = `${errText} ${raw}`.toLowerCase();
        const limitKeywords = [
          "rate limit",
          "quota",
          "capacity",
          "usage limit",
          "token limit",
        ];
        const isLimit =
          (code === 1 && !errText) ||
          limitKeywords.some((kw) => combined.includes(kw));

        if (isLimit) {
          reject(
            new Error(
              "Claude subscription limit likely reached. Check your Claude Code Max usage."
            )
          );
          return;
        }
        reject(new Error(`claude exited with code ${code}: ${errText}`));
        return;
      }

      if (!raw) {
        reject(new Error("Empty response from claude"));
        return;
      }

      try {
        const result = parseJsonResponse(raw);
        resolve({ result, raw, durationMs });
      } catch (e) {
        // Return raw text as the result if JSON parsing fails
        resolve({
          result: { _raw: raw, _parse_failed: true },
          raw,
          durationMs,
        });
      }
    });

    proc.on("error", (err) => {
      clearTimeout(timer);
      reject(
        new Error(
          `Failed to spawn claude: ${err.message}. Is claude CLI installed?`
        )
      );
    });

    // Write prompt to stdin and close
    proc.stdin.write(prompt);
    proc.stdin.end();
  });
}

// ── Availability check ──────────────────────────────────

let _available: boolean | null = null;

export async function isLocalExecutorAvailable(): Promise<boolean> {
  if (_available !== null) return _available;

  return new Promise<boolean>((resolve) => {
    const proc = spawn("claude", ["--version"], {
      stdio: ["ignore", "pipe", "pipe"],
    });

    proc.on("close", (code) => {
      _available = code === 0;
      resolve(_available);
    });

    proc.on("error", () => {
      _available = false;
      resolve(false);
    });

    // Don't wait forever
    setTimeout(() => {
      proc.kill();
      _available = false;
      resolve(false);
    }, 5_000);
  });
}
