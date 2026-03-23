"use client";

import { useCallback } from "react";
import { Activity } from "lucide-react";
import Papa from "papaparse";
import { EmptyState } from "@/components/ui/empty-state";
import { ExecutionTrace } from "./execution-trace";
import { ProgressBar } from "./progress-bar";
import { ResultsTable } from "./results-table";
import type { ExecutionState, RowStatus } from "@/hooks/use-chat";
import type { FunctionDefinition } from "@/lib/types";

interface ActivityPanelProps {
  executionState: ExecutionState | null;
  rowStatuses: RowStatus[];
  streamProgress: { current: number; total: number } | null;
  completedResults: Record<string, unknown>[];
  streaming: boolean;
  selectedFunction: FunctionDefinition | null;
}

export function ActivityPanel({
  executionState,
  rowStatuses,
  streamProgress,
  completedResults,
  streaming,
  selectedFunction,
}: ActivityPanelProps) {
  const isIdle =
    !streaming && completedResults.length === 0 && executionState === null;

  const handleExportCsv = useCallback(() => {
    if (completedResults.length === 0) return;
    const csv = Papa.unparse(completedResults);
    const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    const filename = selectedFunction
      ? `${selectedFunction.name.toLowerCase().replace(/\s+/g, "-")}-results.csv`
      : "results.csv";
    link.download = filename;
    link.click();
    URL.revokeObjectURL(url);
  }, [completedResults, selectedFunction]);

  return (
    <div className="hidden lg:flex w-80 border-l border-clay-600 flex-col bg-clay-950 h-full">
      {/* Header */}
      <div className="px-4 py-3 border-b border-clay-700 flex items-center gap-2">
        <Activity className="h-4 w-4 text-clay-300" />
        <span className="text-xs font-semibold text-clay-300">Activity</span>
      </div>

      {/* Content area */}
      <div className="flex-1 flex flex-col overflow-hidden">
        <ExecutionTrace
          executionState={executionState}
          hasResults={completedResults.length > 0}
        />
        <ProgressBar
          rowStatuses={rowStatuses}
          streamProgress={streamProgress}
        />

        {rowStatuses.length > 0 ? (
          <div className="flex-1 flex flex-col overflow-hidden">
            <ResultsTable
              rowStatuses={rowStatuses}
              columns={selectedFunction?.outputs || []}
              onExportCsv={handleExportCsv}
              streaming={streaming}
            />
          </div>
        ) : (
          !streaming && !executionState && (
            <div className="flex-1 flex items-center justify-center p-6">
              <EmptyState
                title="Activity"
                description="Execution details will appear here when you run a function."
                icon={Activity}
              />
            </div>
          )
        )}
      </div>
    </div>
  );
}
