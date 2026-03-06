"use client";

import type { WebhookResponse } from "@/lib/types";
import { formatDuration } from "@/lib/utils";

export function ResultViewer({
  result,
  loading,
}: {
  result: WebhookResponse | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <div className="flex h-full items-center justify-center rounded-xl border border-zinc-800 bg-zinc-900 p-8">
        <div className="flex items-center gap-3 text-zinc-400">
          <svg className="h-5 w-5 animate-spin" viewBox="0 0 24 24" fill="none">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
          Processing...
        </div>
      </div>
    );
  }

  if (!result) {
    return (
      <div className="flex h-full items-center justify-center rounded-xl border border-zinc-800 bg-zinc-900 p-8">
        <p className="text-zinc-500">Select a skill and click Run to see results.</p>
      </div>
    );
  }

  const meta = result._meta;
  const isError = result.error;
  const display = { ...result };
  delete display._meta;

  return (
    <div className="flex flex-col rounded-xl border border-zinc-800 bg-zinc-900 overflow-hidden">
      {meta && (
        <div className="flex items-center gap-4 border-b border-zinc-800 px-4 py-2 text-xs text-zinc-500">
          <span>Model: <span className="text-zinc-300">{meta.model}</span></span>
          <span>Duration: <span className="text-zinc-300">{formatDuration(meta.duration_ms)}</span></span>
          {meta.cached && <span className="text-yellow-400">cached</span>}
        </div>
      )}
      <pre
        className={`flex-1 overflow-auto p-4 font-mono text-sm leading-relaxed ${
          isError ? "text-red-400" : "text-zinc-200"
        }`}
      >
        {JSON.stringify(display, null, 2)}
      </pre>
    </div>
  );
}
