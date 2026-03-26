"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { CheckCircle, Monitor, Cloud, Zap } from "lucide-react";
import { isLocalExecutionMode } from "@/lib/api";

export function ProgressBar({
  total,
  completed,
  failed,
  done = false,
  batchStats,
}: {
  total: number;
  completed: number;
  failed: number;
  done?: boolean;
  batchStats?: {
    batchSize: number;
    claudeCalls: number;
    savedCalls: number;
  };
}) {
  const processed = completed + failed;
  const pct = total > 0 ? Math.round((processed / total) * 100) : 0;
  const isLocal = isLocalExecutionMode();

  return (
    <Card className="border-clay-500">
      <CardContent className="p-5">
        <div className="flex items-center justify-between mb-2">
          <div className="flex items-center gap-2">
            <span className="text-sm text-clay-200 font-[family-name:var(--font-sans)]">
              {processed} / {total} rows processed
            </span>
            {/* Execution mode badge */}
            <Badge
              variant="outline"
              className={
                isLocal
                  ? "text-[10px] px-1.5 py-0 h-5 bg-violet-500/15 text-violet-400 border-violet-500/30"
                  : "text-[10px] px-1.5 py-0 h-5 bg-sky-500/15 text-sky-400 border-sky-500/30"
              }
            >
              {isLocal ? (
                <Monitor className="h-3 w-3 mr-0.5" />
              ) : (
                <Cloud className="h-3 w-3 mr-0.5" />
              )}
              {isLocal ? "Local" : "Remote"}
            </Badge>
          </div>
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
        <div className="flex items-center gap-4 mt-2 text-xs text-clay-200">
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

          {/* Batch execution stats */}
          {isLocal && done && (
            <span className="ml-auto flex items-center gap-1.5 text-violet-400">
              <Zap className="h-3 w-3" />
              {batchStats ? (
                <>
                  {batchStats.claudeCalls} call{batchStats.claudeCalls !== 1 ? "s" : ""}{" "}
                  <span className="text-clay-500">
                    (saved {batchStats.savedCalls})
                  </span>
                </>
              ) : (
                <>batched /{Math.min(5, total)} per call</>
              )}
            </span>
          )}
        </div>
      </CardContent>
    </Card>
  );
}
