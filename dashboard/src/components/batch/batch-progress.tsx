"use client";

import { Card, CardContent } from "@/components/ui/card";

export function BatchProgress({
  total,
  completed,
  failed,
}: {
  total: number;
  completed: number;
  failed: number;
}) {
  const done = completed + failed;
  const pct = total > 0 ? Math.round((done / total) * 100) : 0;

  return (
    <Card className="border-clay-800 bg-clay-900">
      <CardContent className="p-4">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-clay-300 font-[family-name:var(--font-sans)]">
            {done} / {total} rows processed
          </span>
          <span className="text-sm font-[family-name:var(--font-mono)] text-clay-400">
            {pct}%
          </span>
        </div>
        <div className="h-2.5 rounded-full bg-clay-800 overflow-hidden">
          <div
            className="h-full rounded-full bg-gradient-to-r from-kiln-teal to-kiln-teal-light transition-all duration-300"
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="flex gap-4 mt-2 text-xs text-clay-500">
          <span>
            Completed:{" "}
            <span className="text-kiln-teal font-medium">{completed}</span>
          </span>
          <span>
            Failed:{" "}
            <span className="text-kiln-coral font-medium">{failed}</span>
          </span>
          <span>
            Queued:{" "}
            <span className="text-clay-400">{total - done}</span>
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
