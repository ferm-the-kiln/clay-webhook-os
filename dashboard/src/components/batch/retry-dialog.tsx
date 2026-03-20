"use client";

import { useState, useMemo } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import { RotateCcw } from "lucide-react";
import type { BatchStatus } from "@/lib/types";

interface RetryDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  batchStatus: BatchStatus;
  onRetry: (modifiedRows?: Record<string, Record<string, unknown>>) => Promise<void>;
}

export function RetryDialog({ open, onOpenChange, batchStatus, onRetry }: RetryDialogProps) {
  const [isRetrying, setIsRetrying] = useState(false);
  const [editedData, setEditedData] = useState<Record<string, string>>({});

  const failedJobs = useMemo(
    () => batchStatus.jobs.filter((j) => j.status === "failed" || j.status === "dead_letter"),
    [batchStatus.jobs]
  );

  const handleRetryAll = async () => {
    setIsRetrying(true);
    try {
      // Parse any edited data
      const patches: Record<string, Record<string, unknown>> = {};
      for (const [jobId, raw] of Object.entries(editedData)) {
        if (raw.trim()) {
          try {
            patches[jobId] = JSON.parse(raw);
          } catch {
            // Skip invalid JSON
          }
        }
      }
      await onRetry(Object.keys(patches).length > 0 ? patches : undefined);
      onOpenChange(false);
    } finally {
      setIsRetrying(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="max-w-2xl max-h-[80vh] overflow-y-auto bg-clay-800 border-clay-500 text-clay-100">
        <DialogHeader>
          <DialogTitle className="text-clay-100 font-[family-name:var(--font-sans)]">
            Retry Failed Rows
          </DialogTitle>
          <DialogDescription className="text-clay-200">
            {failedJobs.length} failed row{failedJobs.length !== 1 ? "s" : ""} will be re-enqueued.
            Optionally edit row data before retrying.
          </DialogDescription>
        </DialogHeader>

        <div className="space-y-3 max-h-[400px] overflow-y-auto">
          {failedJobs.map((job) => (
            <div
              key={job.id}
              className="rounded-lg border border-clay-500 bg-clay-700/50 p-3"
            >
              <div className="flex items-center justify-between mb-2">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-[family-name:var(--font-mono)] text-clay-200 truncate max-w-[200px]">
                    {job.row_id || job.id}
                  </span>
                  <Badge
                    variant="outline"
                    className="bg-kiln-coral/10 text-kiln-coral border-kiln-coral/30 text-[10px]"
                  >
                    {job.status}
                  </Badge>
                </div>
              </div>
              {job.error && (
                <pre className="text-[11px] text-kiln-coral font-[family-name:var(--font-mono)] mb-2 whitespace-pre-wrap bg-kiln-coral/5 rounded p-1.5 border border-kiln-coral/20">
                  {job.error}
                </pre>
              )}
              <Textarea
                placeholder='Edit row data as JSON (e.g. {"name": "Updated"})'
                className="text-xs font-[family-name:var(--font-mono)] bg-clay-800 border-clay-500 text-clay-200 min-h-[60px]"
                value={editedData[job.id] || ""}
                onChange={(e) =>
                  setEditedData((prev) => ({ ...prev, [job.id]: e.target.value }))
                }
              />
            </div>
          ))}
        </div>

        <DialogFooter>
          <Button
            variant="ghost"
            onClick={() => onOpenChange(false)}
            className="text-clay-200"
          >
            Cancel
          </Button>
          <Button
            onClick={handleRetryAll}
            disabled={isRetrying || failedJobs.length === 0}
            className="bg-kiln-coral hover:bg-kiln-coral/90 text-white"
          >
            <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
            {isRetrying ? "Retrying..." : `Retry ${failedJobs.length} row${failedJobs.length !== 1 ? "s" : ""}`}
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}
