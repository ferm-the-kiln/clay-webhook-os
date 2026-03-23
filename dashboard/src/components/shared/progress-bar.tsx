"use client";

import { Card, CardContent } from "@/components/ui/card";
import { CheckCircle } from "lucide-react";

export function ProgressBar({
  total,
  completed,
  failed,
  done = false,
}: {
  total: number;
  completed: number;
  failed: number;
  done?: boolean;
}) {
  const processed = completed + failed;
  const pct = total > 0 ? Math.round((processed / total) * 100) : 0;

  return (
    <Card className="border-clay-500">
      <CardContent className="p-5">
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-clay-200 font-[family-name:var(--font-sans)]">
            {processed} / {total} rows processed
          </span>
          <div className="flex items-center gap-2">
            <span className="text-sm font-[family-name:var(--font-mono)] text-clay-200">
              {pct}%
            </span>
            {done && <CheckCircle className="h-4 w-4 text-kiln-teal" />}
          </div>
        </div>
        <div className="h-2.5 rounded-full bg-clay-800 overflow-hidden">
          <div
            className={`h-full rounded-full transition-all duration-500 ${
              done
                ? "bg-kiln-teal"
                : "bg-gradient-to-r from-kiln-teal to-kiln-teal-light bg-[length:200%_100%] animate-shimmer"
            }`}
            style={{ width: `${pct}%` }}
          />
        </div>
        <div className="flex gap-4 mt-2 text-xs text-clay-200">
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
            <span className="text-clay-200">{total - processed}</span>
          </span>
        </div>
      </CardContent>
    </Card>
  );
}
