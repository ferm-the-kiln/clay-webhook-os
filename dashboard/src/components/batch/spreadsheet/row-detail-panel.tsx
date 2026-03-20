"use client";

import type { Job } from "@/lib/types";
import { formatDuration, formatRelativeTime, formatCost, formatTokens } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { StatusBadge } from "@/components/dashboard/status-badge";
import { RotateCcw } from "lucide-react";

export function RowDetailPanel({
  job,
  originalData,
  onRetryRow,
}: {
  job: Job;
  originalData: Record<string, string>;
  onRetryRow?: (jobId: string) => void;
}) {
  return (
    <div className="bg-clay-950 border-b border-clay-500 px-6 py-4">
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {/* Input data */}
        <div>
          <p className="text-xs text-clay-200 uppercase tracking-wider mb-2">
            Input Data
          </p>
          <div className="space-y-1">
            {Object.entries(originalData).length > 0 ? (
              Object.entries(originalData).map(([key, val]) => (
                <div key={key} className="flex gap-2 text-xs">
                  <span className="text-clay-200 font-[family-name:var(--font-mono)] shrink-0">
                    {key}:
                  </span>
                  <span className="text-clay-300 truncate">{val}</span>
                </div>
              ))
            ) : (
              <p className="text-xs text-clay-300">No input data</p>
            )}
          </div>
        </div>

        {/* Result / Error */}
        <div>
          <p className="text-xs text-clay-200 uppercase tracking-wider mb-2">
            {job.error ? "Error" : "Result"}
          </p>
          {job.result ? (
            <pre className="text-xs text-clay-300 font-[family-name:var(--font-mono)] max-h-48 overflow-auto whitespace-pre-wrap rounded bg-clay-800 p-2 border border-clay-500">
              {JSON.stringify(job.result, null, 2)}
            </pre>
          ) : job.error ? (
            <div className="space-y-2">
              <pre className="text-xs text-kiln-coral font-[family-name:var(--font-mono)] max-h-48 overflow-auto whitespace-pre-wrap rounded bg-kiln-coral/5 p-2 border border-kiln-coral/30">
                {job.error}
              </pre>
              {onRetryRow && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => onRetryRow(job.id)}
                  className="h-7 bg-kiln-coral/10 text-kiln-coral border-kiln-coral/30 hover:bg-kiln-coral/20"
                >
                  <RotateCcw className="h-3 w-3 mr-1" />
                  Retry this row
                </Button>
              )}
            </div>
          ) : (
            <p className="text-xs text-clay-300">Pending...</p>
          )}
        </div>

        {/* Meta */}
        <div>
          <p className="text-xs text-clay-200 uppercase tracking-wider mb-2">
            Metadata
          </p>
          <div className="space-y-2">
            <div className="flex items-center gap-2">
              <span className="text-xs text-clay-200">Status:</span>
              <StatusBadge status={job.status} />
            </div>
            <div className="flex items-center gap-2">
              <span className="text-xs text-clay-200">Duration:</span>
              <span className="text-xs text-clay-300 font-[family-name:var(--font-mono)]">
                {job.duration_ms ? formatDuration(job.duration_ms) : "\u2014"}
              </span>
            </div>
            {(job.input_tokens_est || job.output_tokens_est) && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-clay-200">Tokens:</span>
                <span className="text-xs text-clay-300 font-[family-name:var(--font-mono)]">
                  {formatTokens((job.input_tokens_est ?? 0) + (job.output_tokens_est ?? 0))}
                </span>
              </div>
            )}
            {job.cost_est_usd !== undefined && job.cost_est_usd > 0 && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-clay-200">Cost est:</span>
                <span className="text-xs text-clay-300 font-[family-name:var(--font-mono)]">
                  {formatCost(job.cost_est_usd)}
                </span>
              </div>
            )}
            <div className="flex items-center gap-2">
              <span className="text-xs text-clay-200">Job ID:</span>
              <span className="text-xs text-clay-200 font-[family-name:var(--font-mono)] truncate">
                {job.id}
              </span>
            </div>
            {job.row_id && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-clay-200">Row ID:</span>
                <span className="text-xs text-clay-200 font-[family-name:var(--font-mono)]">
                  {job.row_id}
                </span>
              </div>
            )}
            {job.created_at && (
              <div className="flex items-center gap-2">
                <span className="text-xs text-clay-200">Created:</span>
                <span className="text-xs text-clay-200">
                  {formatRelativeTime(job.created_at)}
                </span>
              </div>
            )}
            {job.retry_count !== undefined && job.retry_count > 0 && (
              <Badge
                variant="outline"
                className="bg-kiln-mustard/10 text-kiln-mustard border-kiln-mustard/30 text-[10px] w-fit"
              >
                {job.retry_count} retries
              </Badge>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
