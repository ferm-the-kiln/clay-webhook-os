/**
 * POST /api/execute/function/stream
 *
 * SSE streaming version of consolidated local execution.
 * Emits progress events, then ONE claude --print call for all AI steps.
 *
 * Events:
 *   event: step   data: { step_index, tool, status, ... }
 *   event: result  data: { ...final_output }
 *   event: error   data: { error_message }
 */
import { NextRequest } from "next/server";
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

function sseEvent(event: string, data: unknown): string {
  return `event: ${event}\ndata: ${JSON.stringify(data)}\n\n`;
}

function extractOutput(
  raw: Record<string, unknown>,
  taskKeys: string[],
  outputKeys: string[],
): Record<string, unknown> {
  if (taskKeys.length <= 1) return raw;

  const merged: Record<string, unknown> = {};
  for (const tk of taskKeys) {
    const taskOutput = raw[tk];
    if (taskOutput && typeof taskOutput === "object") {
      Object.assign(merged, taskOutput);
    }
  }
  if (Object.keys(merged).length === 0) {
    for (const key of outputKeys) {
      if (key in raw) merged[key] = raw[key];
    }
  }
  return merged;
}

export async function POST(req: NextRequest) {
  const { functionId, data, instructions, model } = await req.json();
  const encoder = new TextEncoder();

  const stream = new ReadableStream({
    async start(controller) {
      const emit = (event: string, payload: unknown) => {
        controller.enqueue(encoder.encode(sseEvent(event, payload)));
      };

      const available = await isLocalExecutorAvailable();
      if (!available) {
        emit("error", { error_message: "claude CLI not available. Use remote execution mode." });
        controller.close();
        return;
      }

      // Get consolidated prompt
      let consolidated: ConsolidatedPrompt;
      try {
        consolidated = await backendFetch(`/functions/${functionId}/prepare-consolidated`, {
          data, instructions, model,
        });
      } catch (e) {
        emit("error", { error_message: `Prompt preparation failed: ${e instanceof Error ? e.message : e}` });
        controller.close();
        return;
      }

      const accumulated: Record<string, unknown> = {};
      const startTime = Date.now();

      // Execute native API steps first
      if (consolidated.has_native_steps) {
        for (const step of consolidated.native_steps) {
          const stepStart = Date.now();
          emit("step", {
            step_index: step.step_index,
            tool: step.tool,
            tool_name: step.tool_name,
            executor: "native_api",
            status: "running",
            duration_ms: 0,
            resolved_params: step.native_config.params,
            output_keys: [],
          });

          try {
            const result = await backendFetch<Record<string, unknown>>(
              `/functions/${functionId}/execute-step`,
              { step_index: step.step_index, data: { ...data, ...accumulated } },
            );
            delete result._meta;
            Object.assign(accumulated, result);

            emit("step", {
              step_index: step.step_index,
              tool: step.tool,
              tool_name: step.tool_name,
              executor: "native_api",
              status: "success",
              duration_ms: Date.now() - stepStart,
              resolved_params: step.native_config.params,
              output_keys: Object.keys(result),
              output: result,
            });
          } catch (e) {
            emit("step", {
              step_index: step.step_index,
              tool: step.tool,
              tool_name: step.tool_name,
              executor: "native_api",
              status: "error",
              duration_ms: Date.now() - stepStart,
              resolved_params: {},
              output_keys: [],
              error_message: e instanceof Error ? e.message : String(e),
            });
          }
        }
      }

      // Emit a "running" event for the consolidated AI execution
      emit("step", {
        step_index: 0,
        tool: `consolidated (${consolidated.task_keys.length} tasks)`,
        tool_name: `${consolidated.task_keys.length} AI tasks combined`,
        executor: "local_consolidated",
        status: "running",
        duration_ms: 0,
        resolved_params: {},
        output_keys: [],
      });

      // ONE claude --print call for all AI steps
      let prompt = consolidated.prompt;
      if (Object.keys(accumulated).length > 0) {
        prompt += `\n\n---\n\n# Data from Native API Steps\n\n${JSON.stringify(accumulated, null, 2)}`;
      }

      try {
        const result = await executePrompt(prompt, {
          model: consolidated.model,
          timeout: 180_000,
        });

        const output = extractOutput(
          result.result,
          consolidated.task_keys,
          consolidated.output_keys,
        );
        Object.assign(accumulated, output);

        emit("step", {
          step_index: 0,
          tool: `consolidated (${consolidated.task_keys.length} tasks)`,
          tool_name: `${consolidated.task_keys.length} AI tasks combined`,
          executor: "local_consolidated",
          status: "success",
          duration_ms: result.durationMs,
          resolved_params: {},
          output_keys: Object.keys(output),
          output,
        });
      } catch (e) {
        emit("step", {
          step_index: 0,
          tool: `consolidated (${consolidated.task_keys.length} tasks)`,
          tool_name: `${consolidated.task_keys.length} AI tasks combined`,
          executor: "local_consolidated",
          status: "error",
          duration_ms: Date.now() - startTime,
          resolved_params: {},
          output_keys: [],
          error_message: e instanceof Error ? e.message : String(e),
        });
      }

      // Final result
      emit("result", {
        ...accumulated,
        _meta: {
          execution_mode: "local_consolidated",
          duration_ms: Date.now() - startTime,
          task_count: consolidated.task_keys.length,
          claude_calls: 1,
        },
      });

      controller.close();
    },
  });

  return new Response(stream, {
    headers: {
      "Content-Type": "text/event-stream",
      "Cache-Control": "no-cache",
      Connection: "keep-alive",
    },
  });
}
