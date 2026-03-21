"use client";

import { OutputView } from "@/components/functions/output-view";

interface ResultCardProps {
  results: Record<string, unknown>[];
}

export function ResultCard({ results }: ResultCardProps) {
  if (results.length === 0) return null;

  if (results.length === 1) {
    return (
      <div className="mt-2 rounded-lg border border-clay-700 bg-clay-900/50 p-3">
        <OutputView result={results[0]} />
      </div>
    );
  }

  return (
    <div className="mt-2 space-y-2">
      {results.map((result, i) => (
        <div
          key={i}
          className="rounded-lg border border-clay-700 bg-clay-900/50 p-3"
        >
          <div className="mb-2 text-xs font-semibold text-clay-300">
            Row {i + 1}
          </div>
          <OutputView result={result} />
        </div>
      ))}
    </div>
  );
}
