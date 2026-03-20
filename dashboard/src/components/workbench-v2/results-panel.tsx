"use client";

import type { FunctionDefinition } from "@/lib/types";
import type {
  ResultRow,
  RowStatus,
  ColumnMapping,
} from "@/hooks/use-function-workbench";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  Check,
  X,
  Loader2,
  AlertCircle,
  RefreshCw,
  Download,
  ChevronDown,
  ChevronUp,
} from "lucide-react";

interface ResultsPanelProps {
  results: ResultRow[];
  displayResults: ResultRow[];
  selectedFunction: FunctionDefinition;
  mappings: ColumnMapping[];
  running: boolean;
  statusFilter: RowStatus | "all";
  sortColumn: string | null;
  sortDir: "asc" | "desc";
  expandedCell: { row: number; col: string } | null;
  expandedError: number | null;
  successRate: number;
  doneCount: number;
  errorCount: number;
  onStatusFilterChange: (filter: RowStatus | "all") => void;
  onSortColumnChange: (col: string | null) => void;
  onSortDirChange: (dir: "asc" | "desc") => void;
  onExpandedCellChange: (cell: { row: number; col: string } | null) => void;
  onExpandedErrorChange: (row: number | null) => void;
  onRetryFailed: () => void;
  onExport: (selectedOnly?: boolean) => void;
  onNewRun: () => void;
}

export function ResultsPanel({
  results,
  displayResults,
  selectedFunction,
  mappings,
  running,
  statusFilter,
  sortColumn,
  sortDir,
  expandedCell,
  expandedError,
  successRate,
  doneCount,
  errorCount,
  onStatusFilterChange,
  onSortColumnChange,
  onSortDirChange,
  onExpandedCellChange,
  onExpandedErrorChange,
  onRetryFailed,
  onExport,
  onNewRun,
}: ResultsPanelProps) {
  const pendingCount = results.filter(
    (r) => r.status === "pending" || r.status === "running"
  ).length;

  const handleSort = (col: string) => {
    if (sortColumn === col) {
      onSortDirChange(sortDir === "asc" ? "desc" : "asc");
    } else {
      onSortColumnChange(col);
      onSortDirChange("asc");
    }
  };

  return (
    <div className="space-y-4">
      {/* Summary stats bar */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
        <div className="bg-clay-800/60 rounded-lg px-3 py-2">
          <div className="text-[10px] text-clay-300 uppercase tracking-wider">
            Success Rate
          </div>
          <div
            className={cn(
              "text-lg font-bold",
              successRate >= 80
                ? "text-green-400"
                : successRate >= 50
                  ? "text-yellow-400"
                  : "text-red-400"
            )}
          >
            {successRate.toFixed(0)}%
          </div>
        </div>
        <div className="bg-clay-800/60 rounded-lg px-3 py-2">
          <div className="text-[10px] text-clay-300 uppercase tracking-wider">
            Processed
          </div>
          <div className="text-lg font-bold text-clay-100">
            {doneCount + errorCount}
            <span className="text-sm text-clay-300">/{results.length}</span>
          </div>
        </div>
        <div className="bg-clay-800/60 rounded-lg px-3 py-2">
          <div className="text-[10px] text-clay-300 uppercase tracking-wider">
            Errors
          </div>
          <div
            className={cn(
              "text-lg font-bold",
              errorCount > 0 ? "text-red-400" : "text-clay-100"
            )}
          >
            {errorCount}
          </div>
        </div>
        <div className="bg-clay-800/60 rounded-lg px-3 py-2">
          <div className="text-[10px] text-clay-300 uppercase tracking-wider">
            Successful
          </div>
          <div className="text-lg font-bold text-green-400">{doneCount}</div>
        </div>
      </div>

      {/* Toolbar */}
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3 text-xs text-clay-300">
          <span className="flex items-center gap-1">
            <Check className="h-3 w-3 text-green-400" />
            {doneCount} done
          </span>
          <span className="flex items-center gap-1">
            <X className="h-3 w-3 text-red-400" />
            {errorCount} errors
          </span>
          {pendingCount > 0 && (
            <span className="flex items-center gap-1">
              <Loader2 className="h-3 w-3 animate-spin text-clay-300" />
              {pendingCount} pending
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="border-clay-600 text-clay-300 text-xs"
              >
                Filter: {statusFilter === "all" ? "All" : statusFilter}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent className="bg-clay-800 border-clay-600">
              {(
                ["all", "done", "error", "pending", "running"] as const
              ).map((s) => (
                <DropdownMenuItem
                  key={s}
                  onClick={() => onStatusFilterChange(s)}
                  className="text-xs"
                >
                  {s === "all" ? "All" : s}
                </DropdownMenuItem>
              ))}
            </DropdownMenuContent>
          </DropdownMenu>

          {errorCount > 0 && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRetryFailed}
              disabled={running}
              className="border-clay-600 text-clay-300 text-xs"
            >
              <RefreshCw className="h-3 w-3 mr-1" />
              Retry Failed
            </Button>
          )}
          <Button
            variant="outline"
            size="sm"
            onClick={() => onExport()}
            className="border-clay-600 text-clay-300 text-xs"
          >
            <Download className="h-3 w-3 mr-1" />
            Export All
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={() => onExport(true)}
            className="border-clay-600 text-clay-300 text-xs"
          >
            Export Successful
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={onNewRun}
            className="border-clay-600 text-clay-300 text-xs"
          >
            New Run
          </Button>
        </div>
      </div>

      {/* Results table */}
      <div className="overflow-x-auto rounded-lg border border-clay-600">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-clay-800">
              <th className="px-3 py-2 text-left text-clay-300 font-medium w-12">
                #
              </th>
              <th className="px-3 py-2 text-left text-clay-300 font-medium w-16">
                Status
              </th>
              {mappings.map((m) => (
                <th
                  key={`in-${m.functionInput}`}
                  className="px-3 py-2 text-left text-clay-300 font-medium whitespace-nowrap cursor-pointer hover:text-clay-100"
                  onClick={() => handleSort(m.functionInput)}
                >
                  {m.functionInput}
                  {sortColumn === m.functionInput &&
                    (sortDir === "asc" ? " \u2191" : " \u2193")}
                </th>
              ))}
              {selectedFunction.outputs.map((o) => (
                <th
                  key={`out-${o.key}`}
                  className="px-3 py-2 text-left text-kiln-teal font-medium whitespace-nowrap cursor-pointer hover:text-kiln-teal-light"
                  onClick={() => handleSort(o.key)}
                >
                  {o.key}
                  {sortColumn === o.key &&
                    (sortDir === "asc" ? " \u2191" : " \u2193")}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {displayResults.map((row) => (
              <>
                <tr
                  key={row.rowIndex}
                  className="border-t border-clay-700 hover:bg-clay-800/50"
                >
                  <td className="px-3 py-1.5 text-clay-300">
                    {row.rowIndex + 1}
                  </td>
                  <td className="px-3 py-1.5">
                    {row.status === "done" && (
                      <Check className="h-3.5 w-3.5 text-green-400" />
                    )}
                    {row.status === "error" && (
                      <button
                        className="flex items-center gap-1 text-red-400"
                        onClick={() =>
                          onExpandedErrorChange(
                            expandedError === row.rowIndex
                              ? null
                              : row.rowIndex
                          )
                        }
                        title="Click to expand error"
                      >
                        <AlertCircle className="h-3.5 w-3.5" />
                        {expandedError === row.rowIndex ? (
                          <ChevronUp className="h-3 w-3" />
                        ) : (
                          <ChevronDown className="h-3 w-3" />
                        )}
                      </button>
                    )}
                    {row.status === "running" && (
                      <Loader2 className="h-3.5 w-3.5 text-kiln-teal animate-spin" />
                    )}
                    {row.status === "pending" && (
                      <span className="h-2 w-2 rounded-full bg-clay-500 inline-block" />
                    )}
                  </td>
                  {mappings.map((m) => (
                    <td
                      key={`in-${m.functionInput}`}
                      className="px-3 py-1.5 text-clay-200 max-w-[200px] truncate cursor-pointer"
                      onClick={() =>
                        onExpandedCellChange(
                          expandedCell?.row === row.rowIndex &&
                            expandedCell?.col === m.functionInput
                            ? null
                            : { row: row.rowIndex, col: m.functionInput }
                        )
                      }
                    >
                      {expandedCell?.row === row.rowIndex &&
                      expandedCell?.col === m.functionInput ? (
                        <div className="whitespace-pre-wrap break-words max-w-md">
                          {String(row.input[m.functionInput] ?? "")}
                        </div>
                      ) : (
                        String(row.input[m.functionInput] ?? "")
                      )}
                    </td>
                  ))}
                  {selectedFunction.outputs.map((o) => (
                    <td
                      key={`out-${o.key}`}
                      className={cn(
                        "px-3 py-1.5 max-w-[200px] truncate cursor-pointer",
                        row.status === "error" ? "text-red-400" : "text-clay-100"
                      )}
                      onClick={() =>
                        onExpandedCellChange(
                          expandedCell?.row === row.rowIndex &&
                            expandedCell?.col === o.key
                            ? null
                            : { row: row.rowIndex, col: o.key }
                        )
                      }
                    >
                      {row.status === "error"
                        ? row.error
                        : expandedCell?.row === row.rowIndex &&
                            expandedCell?.col === o.key
                          ? (
                              <div className="whitespace-pre-wrap break-words max-w-md">
                                {typeof row.output?.[o.key] === "object"
                                  ? JSON.stringify(row.output?.[o.key], null, 2)
                                  : String(row.output?.[o.key] ?? "")}
                              </div>
                            )
                          : typeof row.output?.[o.key] === "object"
                            ? JSON.stringify(row.output?.[o.key])
                            : String(row.output?.[o.key] ?? "")}
                    </td>
                  ))}
                </tr>
                {/* Expanded error detail row */}
                {row.status === "error" && expandedError === row.rowIndex && (
                  <tr key={`err-${row.rowIndex}`} className="bg-red-950/20">
                    <td
                      colSpan={
                        2 +
                        mappings.length +
                        selectedFunction.outputs.length
                      }
                      className="px-3 py-2"
                    >
                      <div className="text-xs text-red-300 whitespace-pre-wrap font-mono">
                        {row.error || "Unknown error"}
                      </div>
                    </td>
                  </tr>
                )}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
