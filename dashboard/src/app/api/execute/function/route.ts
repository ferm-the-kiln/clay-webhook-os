/**
 * POST /api/execute/function
 *
 * Consolidated local function execution — gets a SINGLE mega-prompt from
 * the backend (all AI steps combined, context deduplicated) and runs it
 * in ONE claude --print call instead of one per step.
 *
 * Native API steps (findymail) are still routed to the backend.
 */
import { NextRequest, NextResponse } from "next/server";
import { executePrompt, isLocalExecutorAvailable } from "@/lib/local-executor";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://clay.nomynoms.com";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

interface NativeStep {
  step_index: number;
  tool: string;
  tool_name: string;
  executor_type: string;
  native_config: { tool_id: string; params: Record<string, string> };
}

interface ConsolidatedPrompt {
  function_id: string;
  function_name: string;
  prompt: string;
  model: string;
  task_keys: string[];
  output_keys: string[];
  has_native_steps: boolean;
  native_steps: NativeStep[];
}

async function backendFetch<T>(path: string, body: unknown): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
    },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`Backend ${res.status}: ${text}`);
  }
  return res.json();
}

/**
 * Extract final output from a consolidated response.
 * If multi-task, merges all task outputs (later tasks override earlier).
 * If single-task, returns the result directly.
 */
function extractOutput(
  raw: Record<string, unknown>,
  taskKeys: string[],
  outputKeys: string[],
): Record<string, unknown> {
  if (taskKeys.length <= 1) {
    // Single task — result is the output directly
    return raw;
  }

  // Multi-task — merge task outputs, later tasks override
  const merged: Record<string, unknown> = {};
  for (const tk of taskKeys) {
    const taskOutput = raw[tk];
    if (taskOutput && typeof taskOutput === "object") {
      Object.assign(merged, taskOutput);
    }
  }

  // If merging produced nothing (model returned flat keys instead of task_1/task_2),
  // fall back to using the raw output filtered to expected keys
  if (Object.keys(merged).length === 0) {
    for (const key of outputKeys) {
      if (key in raw) {
        merged[key] = raw[key];
      }
    }
  }

  return merged;
}

export async function POST(req: NextRequest) {
  const { functionId, data, instructions, model } = await req.json();

  const available = await isLocalExecutorAvailable();
  if (!available) {
    return NextResponse.json(
      {
        error: true,
        error_message:
          "claude CLI not available on this machine. Use remote execution mode.",
      },
      { status: 503 },
    );
  }

  // 1. Get consolidated mega-prompt from backend
  let consolidated: ConsolidatedPrompt;
  try {
    consolidated = await backendFetch(
      `/functions/${functionId}/prepare-consolidated`,
      { data, instructions, model },
    );
  } catch (e) {
    return NextResponse.json(
      {
        error: true,
        error_message: `Prompt preparation failed: ${e instanceof Error ? e.message : e}`,
      },
      { status: 502 },
    );
  }

  const startTime = Date.now();
  const accumulated: Record<string, unknown> = {};

  // 2. Execute native API steps first (if any) — these go through the backend
  if (consolidated.has_native_steps) {
    for (const step of consolidated.native_steps) {
      try {
        const result = await backendFetch<Record<string, unknown>>(
          `/functions/${functionId}/execute-step`,
          { step_index: step.step_index, data: { ...data, ...accumulated } },
        );
        delete result._meta;
        Object.assign(accumulated, result);
      } catch (e) {
        // Continue — native step failure doesn't block AI execution
      }
    }
  }

  // 3. Execute the consolidated mega-prompt — ONE claude --print call
  let prompt = consolidated.prompt;

  // If native steps produced output, inject it
  if (Object.keys(accumulated).length > 0) {
    prompt += `\n\n---\n\n# Data from Native API Steps\n\n${JSON.stringify(accumulated, null, 2)}`;
  }

  try {
    const result = await executePrompt(prompt, {
      model: consolidated.model,
      timeout: 180_000, // consolidated prompts may take longer
    });

    const output = extractOutput(
      result.result,
      consolidated.task_keys,
      consolidated.output_keys,
    );
    Object.assign(accumulated, output);

    return NextResponse.json({
      ...accumulated,
      _meta: {
        execution_mode: "local_consolidated",
        duration_ms: Date.now() - startTime,
        ai_duration_ms: result.durationMs,
        task_count: consolidated.task_keys.length,
        claude_calls: 1,
      },
    });
  } catch (e) {
    return NextResponse.json(
      {
        error: true,
        error_message: `Local execution failed: ${e instanceof Error ? e.message : e}`,
        _meta: {
          execution_mode: "local_consolidated",
          duration_ms: Date.now() - startTime,
        },
      },
      { status: 500 },
    );
  }
}
