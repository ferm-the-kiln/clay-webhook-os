"use client";

import { Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { useEffect, useState, useRef, useCallback } from "react";
import { Header } from "@/components/layout/header";
import { fetchBatchStatus, fetchJob } from "@/lib/api";
import { SpreadsheetView } from "@/components/batch/spreadsheet/spreadsheet-view";
import type { BatchStatus, Job } from "@/lib/types";
import { Loader2, AlertCircle, FileSpreadsheet } from "lucide-react";

function BatchResultsInner() {
  const searchParams = useSearchParams();
  const batchId = searchParams.get("id");

  const [batchStatus, setBatchStatus] = useState<BatchStatus | null>(null);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [batchDone, setBatchDone] = useState(false);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const fetchFullJobs = useCallback(async (bs: BatchStatus) => {
    const fullJobs = await Promise.all(bs.jobs.map((j) => fetchJob(j.id)));
    setJobs(fullJobs);
  }, []);

  // Initial fetch + polling
  useEffect(() => {
    if (!batchId) return;

    setLoading(true);
    setError(null);

    const loadBatch = async () => {
      try {
        const bs = await fetchBatchStatus(batchId);
        setBatchStatus(bs);

        if (bs.done) {
          setBatchDone(true);
          await fetchFullJobs(bs);
          setLoading(false);
        } else {
          setLoading(false);
          // Start polling
          pollingRef.current = setInterval(async () => {
            try {
              const updated = await fetchBatchStatus(batchId);
              setBatchStatus(updated);

              if (updated.done) {
                setBatchDone(true);
                if (pollingRef.current) clearInterval(pollingRef.current);
                await fetchFullJobs(updated);
              }
            } catch {
              // Silently retry on next interval
            }
          }, 2000);
        }
      } catch (e) {
        setError((e as Error).message);
        setLoading(false);
      }
    };

    loadBatch();

    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [batchId, fetchFullJobs]);

  // No batch ID provided
  if (!batchId) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="text-center space-y-3 max-w-md">
          <FileSpreadsheet className="h-12 w-12 text-clay-300 mx-auto" />
          <h2 className="text-lg font-semibold text-clay-100">
            No batch ID provided
          </h2>
          <p className="text-sm text-clay-200">
            Navigate here from the Run page after completing a batch.
          </p>
        </div>
      </div>
    );
  }

  // Loading state
  if (loading && !batchStatus) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="text-center space-y-3">
          <Loader2 className="h-8 w-8 text-kiln-teal animate-spin mx-auto" />
          <p className="text-sm text-clay-200">Loading batch results...</p>
        </div>
      </div>
    );
  }

  // Error state
  if (error) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <div className="text-center space-y-3 max-w-md">
          <AlertCircle className="h-12 w-12 text-kiln-coral mx-auto" />
          <h2 className="text-lg font-semibold text-clay-100">
            Failed to load batch
          </h2>
          <p className="text-sm text-clay-200">
            Batch ID: <code className="text-kiln-teal">{batchId}</code>
          </p>
          <p className="text-sm text-clay-300">{error}</p>
        </div>
      </div>
    );
  }

  const truncatedId = batchId.length > 12
    ? `${batchId.slice(0, 6)}...${batchId.slice(-4)}`
    : batchId;

  return (
    <div className="flex-1 overflow-auto p-4 md:p-6 space-y-4 pb-20 md:pb-6">
      {/* Summary bar */}
      {batchStatus && (
        <div className="flex items-center gap-6 px-6 py-3 border border-clay-500 rounded-lg bg-clay-900/50">
          <div>
            <span className="text-xs text-clay-200">Batch</span>
            <p className="text-sm text-clay-100 font-medium font-mono">
              {truncatedId}
            </p>
          </div>
          <div>
            <span className="text-xs text-clay-200">Total</span>
            <p className="text-sm text-clay-100 font-medium">
              {batchStatus.total_rows}
            </p>
          </div>
          <div>
            <span className="text-xs text-clay-200">Completed</span>
            <p className="text-sm text-status-success font-medium">
              {batchStatus.completed}
            </p>
          </div>
          <div>
            <span className="text-xs text-clay-200">Failed</span>
            <p className="text-sm text-kiln-coral font-medium">
              {batchStatus.failed}
            </p>
          </div>
          <div>
            <span className="text-xs text-clay-200">Cost</span>
            <p className="text-sm text-clay-100 font-medium">
              ${batchStatus.cost.equivalent_api_usd.toFixed(4)}
            </p>
          </div>
          {!batchDone && (
            <div className="ml-auto flex items-center gap-2">
              <Loader2 className="h-4 w-4 text-kiln-teal animate-spin" />
              <span className="text-xs text-kiln-teal">Processing...</span>
            </div>
          )}
        </div>
      )}

      {/* Spreadsheet */}
      {jobs.length > 0 && (
        <SpreadsheetView
          jobs={jobs}
          originalRows={[]}
          csvHeaders={[]}
        />
      )}

      {/* Still processing, no jobs yet */}
      {!batchDone && jobs.length === 0 && batchStatus && (
        <div className="flex items-center justify-center py-12">
          <div className="text-center space-y-3">
            <Loader2 className="h-8 w-8 text-kiln-teal animate-spin mx-auto" />
            <p className="text-sm text-clay-200">
              Waiting for batch to complete... ({batchStatus.completed}/{batchStatus.total_rows} done)
            </p>
          </div>
        </div>
      )}
    </div>
  );
}

export default function BatchResultsPage() {
  return (
    <div className="flex flex-col h-full">
      <Header title="Batch Results" />
      <Suspense>
        <BatchResultsInner />
      </Suspense>
    </div>
  );
}
