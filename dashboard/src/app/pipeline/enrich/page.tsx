"use client";

import { useState, useCallback } from "react";
import { Header } from "@/components/layout/header";
import { DatasetSelector } from "@/components/pipeline/dataset-selector";
import { StageProgressBar } from "@/components/pipeline/stage-progress-bar";
import { DatasetSpreadsheetView } from "@/components/pipeline/dataset-spreadsheet/dataset-spreadsheet-view";
import { useDatasetContext } from "@/contexts/dataset-context";
import { useStagePolling } from "@/hooks/use-dataset";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { runDatasetStage } from "@/lib/api";
import { toast } from "sonner";
import { Mail, Play, CheckCircle2, AlertCircle, Loader2, RotateCcw } from "lucide-react";

export default function FindEmailPage() {
  const {
    datasets,
    activeId,
    setActiveId,
    dataset,
    rows,
    reload,
    reloadDatasets,
  } = useDatasetContext();

  const [batchId, setBatchId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);
  const [filterMissing, setFilterMissing] = useState(true);

  const stageStatus = useStagePolling(activeId, batchId, () => {
    reload();
    setRunning(false);
  });

  const missingEmailCount = rows.filter(
    (r) => !r.email || r.email === ""
  ).length;

  const handleRun = useCallback(async (retryFailed = false) => {
    if (!activeId) return;
    setRunning(true);
    try {
      let targetRowIds: string[] | undefined;
      if (retryFailed && stageStatus) {
        // Retry only rows without email
        targetRowIds = rows
          .filter((r) => !r.email || r.email === "")
          .map((r) => r._row_id);
      } else if (filterMissing) {
        targetRowIds = rows
          .filter((r) => !r.email || r.email === "")
          .map((r) => r._row_id);
      }

      const res = await runDatasetStage(activeId, {
        stage: "find-email",
        row_ids: targetRowIds ?? null,
      });
      setBatchId(res.batch_id);
      toast.success(`Finding emails for ${res.total_rows} rows...`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to start");
      setRunning(false);
    }
  }, [activeId, rows, filterMissing, stageStatus]);

  const isCompleted = dataset?.stages_completed.includes("find-email");
  const columns = dataset?.columns.filter((c) => c.name !== "_row_id") ?? [];

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Find Email"
        breadcrumbs={[
          { label: "Pipeline", href: "/pipeline" },
          { label: "Find Email" },
        ]}
      />

      <div className="flex flex-col gap-6 p-6 max-w-[1400px]">
        {/* Dataset selector */}
        <DatasetSelector
          datasets={datasets}
          activeId={activeId}
          onSelect={setActiveId}
          onCreated={reloadDatasets}
        />

        {dataset && (
          <>
            <StageProgressBar
              completedStages={dataset.stages_completed}
              currentStage={running ? "find-email" : undefined}
            />

            {/* Controls */}
            <div className="border border-clay-600 rounded-lg p-4 bg-clay-800/50">
              <div className="flex items-center justify-between">
                <div className="flex flex-col gap-1">
                  <div className="flex items-center gap-2">
                    <span className="text-sm font-medium text-clay-100">Provider</span>
                    {isCompleted && (
                      <Badge variant="outline" className="border-kiln-teal/30 text-kiln-teal text-xs">
                        <CheckCircle2 className="h-3 w-3 mr-1" />
                        Completed
                      </Badge>
                    )}
                  </div>
                  <div className="flex items-center gap-2 mt-1">
                    <Badge className="bg-kiln-teal/10 text-kiln-teal border border-kiln-teal/20 text-xs">
                      Findymail
                    </Badge>
                    <Badge variant="outline" className="border-clay-600 text-clay-400 text-xs cursor-not-allowed">
                      DeepLine (Coming Soon)
                    </Badge>
                  </div>
                </div>

                <div className="flex items-center gap-3">
                  <label className="flex items-center gap-2 text-sm text-clay-200 cursor-pointer">
                    <input
                      type="checkbox"
                      checked={filterMissing}
                      onChange={(e) => setFilterMissing(e.target.checked)}
                      className="rounded border-clay-500"
                    />
                    Only rows missing email ({missingEmailCount})
                  </label>

                  <Button
                    onClick={() => handleRun(false)}
                    disabled={running || !rows.length}
                    className="bg-kiln-teal text-clay-900 hover:bg-kiln-teal/90"
                  >
                    {running ? (
                      <>
                        <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                        Running...
                      </>
                    ) : (
                      <>
                        <Play className="h-4 w-4 mr-1.5" />
                        Find Emails
                      </>
                    )}
                  </Button>
                </div>
              </div>

              {/* Batch progress */}
              {stageStatus && stageStatus.status === "running" && (
                <div className="mt-4 pt-4 border-t border-clay-600">
                  <div className="flex items-center justify-between text-sm mb-2">
                    <span className="text-clay-200">
                      Processing: {stageStatus.completed + stageStatus.failed}/{stageStatus.total}
                    </span>
                    {stageStatus.failed > 0 && (
                      <span className="text-red-400 flex items-center gap-1">
                        <AlertCircle className="h-3.5 w-3.5" />
                        {stageStatus.failed} failed
                      </span>
                    )}
                  </div>
                  <div className="w-full bg-clay-700 rounded-full h-2">
                    <div
                      className="bg-kiln-teal h-2 rounded-full transition-all duration-300"
                      style={{
                        width: `${((stageStatus.completed + stageStatus.failed) / stageStatus.total) * 100}%`,
                      }}
                    />
                  </div>
                </div>
              )}

              {/* Completion stats */}
              {stageStatus?.status === "completed" && (
                <div className="mt-4 pt-4 border-t border-clay-600 flex items-center justify-between">
                  <div className="flex items-center gap-4">
                    <div className="flex items-center gap-2 text-sm text-kiln-teal">
                      <CheckCircle2 className="h-4 w-4" />
                      Done
                    </div>
                    <div className="flex items-center gap-3 text-xs">
                      <span className="px-2 py-1 rounded bg-kiln-teal/10 text-kiln-teal">
                        {stageStatus.completed} found
                      </span>
                      {stageStatus.failed > 0 && (
                        <span className="px-2 py-1 rounded bg-kiln-coral/10 text-kiln-coral">
                          {stageStatus.failed} failed
                        </span>
                      )}
                      <span className="px-2 py-1 rounded bg-clay-700 text-clay-300">
                        {stageStatus.total} total
                      </span>
                    </div>
                  </div>
                  {stageStatus.failed > 0 && (
                    <Button
                      variant="outline"
                      size="sm"
                      onClick={() => handleRun(true)}
                      disabled={running}
                      className="bg-kiln-coral/10 text-kiln-coral border-kiln-coral/30 hover:bg-kiln-coral/20"
                    >
                      <RotateCcw className="h-3 w-3 mr-1" />
                      Retry Failed
                    </Button>
                  )}
                </div>
              )}
            </div>

            {/* Spreadsheet view */}
            {rows.length > 0 && (
              <DatasetSpreadsheetView columns={columns} rows={rows} />
            )}
          </>
        )}

        {!dataset && (
          <div className="flex flex-col items-center justify-center py-20 text-clay-300">
            <Mail className="h-12 w-12 mb-4 text-clay-500" />
            <p className="text-lg font-medium mb-1">Select a dataset first</p>
            <p className="text-sm">Choose a dataset with contact rows to find email addresses.</p>
          </div>
        )}
      </div>
    </div>
  );
}
