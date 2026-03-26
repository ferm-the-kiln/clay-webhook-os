/**
 * POST /api/execute/function/batch
 *
 * Batch local execution — processes N rows through a function in ONE
 * claude --print call instead of N separate calls.
 *
 * Request: { functionId, rows: [{...}, {...}, ...], batchSize?, instructions?, model? }
 * Response: { results: [{row_id, ...output}, ...], _meta: {...} }
 */
import { NextRequest, NextResponse } from "next/server";
import { executePrompt, isLocalExecutorAvailable } from "@/lib/local-executor";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://clay.nomynoms.com";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

const DEFAULT_BATCH_SIZE = 5;
const MAX_BATCH_SIZE = 15;

interface ConsolidatedPrompt {
  function_id: string;
  function_name: string;
  prompt: string;
  model: string;
  task_keys: string[];
  output_keys: string[];
  has_native_steps: boolean;
  native_steps: unknown[];
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
 * Parse batch output — extract per-row results from the consolidated response.
 */
function parseBatchOutput(
  raw: Record<string, unknown>,
  expectedRows: number,
  taskKeys: string[],
  outputKeys: string[],
): Array<Record<string, unknown>> {
  const rows = raw.rows as Array<Record<string, unknown>> | undefined;
  if (!Array.isArray(rows)) {
    // Model returned flat structure — try to use it as a single result
    return [raw];
  }

  return rows.map((row, i) => {
    // Remove row_id from output
    const { row_id, ...rest } = row;

    // If multi-task, merge task outputs
    const merged: Record<string, unknown> = {};
    let hasTasks = false;
    for (const tk of taskKeys) {
      if (tk in rest && typeof rest[tk] === "object" && rest[tk] !== null) {
        Object.assign(merged, rest[tk] as Record<string, unknown>);
        hasTasks = true;
      }
    }

    if (hasTasks) return merged;

    // Single task or flat structure — filter to output keys
    const filtered: Record<string, unknown> = {};
    for (const key of outputKeys) {
      if (key in rest) filtered[key] = rest[key];
    }
    return Object.keys(filtered).length > 0 ? filtered : rest;
  });
}

export async function POST(req: NextRequest) {
  const {
    functionId,
    rows,
    batchSize: requestedBatchSize,
    instructions,
    model,
  } = await req.json();

  if (!Array.isArray(rows) || rows.length === 0) {
    return NextResponse.json(
      { error: true, error_message: "rows must be a non-empty array" },
      { status: 400 },
    );
  }

  const available = await isLocalExecutorAvailable();
  if (!available) {
    return NextResponse.json(
      { error: true, error_message: "claude CLI not available. Use remote execution mode." },
      { status: 503 },
    );
  }

  const batchSize = Math.min(
    requestedBatchSize || DEFAULT_BATCH_SIZE,
    MAX_BATCH_SIZE,
  );
  const startTime = Date.now();
  const allResults: Array<{ rowIndex: number; output: Record<string, unknown> | null; error?: string }> = [];
  let totalClaudeCalls = 0;

  // Process rows in batches
  for (let batchStart = 0; batchStart < rows.length; batchStart += batchSize) {
    const batch = rows.slice(batchStart, batchStart + batchSize);

    // Get consolidated batch prompt from backend
    let consolidated: ConsolidatedPrompt;
    try {
      consolidated = await backendFetch(
        `/functions/${functionId}/prepare-consolidated`,
        {
          rows: batch,
          data: batch[0], // fallback for single-row compat
          instructions,
          model,
        },
      );
    } catch (e) {
      // Mark all rows in this batch as failed
      for (let i = 0; i < batch.length; i++) {
        allResults.push({
          rowIndex: batchStart + i,
          output: null,
          error: `Preparation failed: ${e instanceof Error ? e.message : e}`,
        });
      }
      continue;
    }

    // Execute ONE claude --print call for the entire batch
    try {
      const result = await executePrompt(consolidated.prompt, {
        model: consolidated.model,
        timeout: 300_000, // batches can take longer
      });
      totalClaudeCalls++;

      const batchResults = parseBatchOutput(
        result.result,
        batch.length,
        consolidated.task_keys,
        consolidated.output_keys,
      );

      // Map results back to row indices
      for (let i = 0; i < batch.length; i++) {
        if (i < batchResults.length) {
          allResults.push({
            rowIndex: batchStart + i,
            output: batchResults[i],
          });
        } else {
          allResults.push({
            rowIndex: batchStart + i,
            output: null,
            error: "Row missing from batch output",
          });
        }
      }
    } catch (e) {
      // Batch failed — mark all rows as failed
      totalClaudeCalls++;
      for (let i = 0; i < batch.length; i++) {
        allResults.push({
          rowIndex: batchStart + i,
          output: null,
          error: e instanceof Error ? e.message : String(e),
        });
      }
    }
  }

  return NextResponse.json({
    results: allResults,
    _meta: {
      execution_mode: "local_batch",
      total_rows: rows.length,
      batch_size: batchSize,
      batch_count: Math.ceil(rows.length / batchSize),
      claude_calls: totalClaudeCalls,
      duration_ms: Date.now() - startTime,
    },
  });
}
