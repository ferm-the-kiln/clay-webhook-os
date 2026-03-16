"use client";

import { useCallback } from "react";
import { useDatasetContext } from "@/contexts/dataset-context";
import { useWorkbench } from "@/hooks/use-workbench";
import { WorkbenchToolbar } from "./workbench-toolbar";
import { PhaseStepper } from "./phase-stepper";
import { ActionPanel } from "./action-panel";
import { DatasetSpreadsheetView } from "@/components/pipeline/dataset-spreadsheet/dataset-spreadsheet-view";
import { UserSearch } from "lucide-react";

export function WorkbenchPage() {
  const { dataset, rows, reload } = useDatasetContext();
  const {
    activePhase,
    panelOpen,
    togglePhase,
    closePanel,
    startStagePolling,
    getStageStatus,
    isStageRunning,
  } = useWorkbench();

  const activeId = dataset?.id ?? null;

  const handleStartPolling = useCallback(
    (stage: string, batchId: string, onComplete?: () => void) => {
      if (!activeId) return;
      startStagePolling(activeId, stage, batchId, onComplete);
    },
    [activeId, startStagePolling]
  );

  const columns = dataset?.columns.filter((c) => c.name !== "_row_id") ?? [];
  const completedStages = dataset?.stages_completed ?? [];

  return (
    <div className="flex flex-col h-full">
      {/* Toolbar: dataset selector + actions */}
      <WorkbenchToolbar />

      {dataset ? (
        <>
          {/* Phase stepper */}
          <PhaseStepper
            activePhase={activePhase}
            panelOpen={panelOpen}
            onPhaseClick={togglePhase}
            completedStages={completedStages}
            getStageStatus={getStageStatus}
          />

          {/* Main area: spreadsheet + action panel */}
          <div className="flex flex-1 min-h-0 overflow-hidden">
            {/* Spreadsheet */}
            <div className="flex-1 min-w-0 overflow-auto p-4">
              {rows.length > 0 ? (
                <DatasetSpreadsheetView
                  columns={columns}
                  rows={rows}
                  className="h-full"
                />
              ) : (
                <div className="flex flex-col items-center justify-center h-full text-clay-300 py-20">
                  <UserSearch className="h-10 w-10 mb-3 text-clay-500" />
                  <p className="text-sm font-medium">No rows yet</p>
                  <p className="text-xs text-clay-400 mt-1">
                    Click Source to import a CSV or generate leads
                  </p>
                </div>
              )}
            </div>

            {/* Action panel (slides in from right) */}
            <ActionPanel
              phase={activePhase}
              open={panelOpen}
              onClose={closePanel}
              startPolling={handleStartPolling}
              getStageStatus={getStageStatus}
              isStageRunning={isStageRunning}
            />
          </div>

          {/* Status bar */}
          <div className="flex items-center gap-3 px-4 py-1.5 border-t border-clay-600 bg-clay-800/50 text-xs text-clay-300">
            <span>{rows.length} rows</span>
            <span>&middot;</span>
            <span>{columns.length} columns</span>
            {completedStages.length > 0 && (
              <>
                <span>&middot;</span>
                <span className="text-kiln-teal">{completedStages.length} stages done</span>
              </>
            )}
            {dataset.updated_at && (
              <>
                <span>&middot;</span>
                <span>updated {formatRelativeTime(dataset.updated_at)}</span>
              </>
            )}
          </div>
        </>
      ) : (
        <div className="flex flex-col items-center justify-center flex-1 text-clay-300">
          <UserSearch className="h-12 w-12 mb-4 text-clay-500" />
          <p className="text-lg font-medium mb-1">Select a dataset</p>
          <p className="text-sm">Choose or create a dataset to start prospecting.</p>
        </div>
      )}
    </div>
  );
}

function formatRelativeTime(timestamp: number): string {
  const now = Date.now() / 1000;
  const diff = now - timestamp;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  return `${Math.floor(diff / 86400)}d ago`;
}
