"use client";

import { useState } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  CheckCircle2,
  AlertTriangle,
  Download,
  ClipboardCheck,
  X,
  RefreshCw,
  Clock,
  FileSpreadsheet,
  HardDrive,
  ExternalLink,
  Loader2,
  Zap,
  Brain,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ExecutionSummaryData, ColumnProgress } from "@/hooks/use-table-builder";
import type { TableDefinition } from "@/lib/types";
import { motion, AnimatePresence } from "framer-motion";
import { toast } from "sonner";

interface ExecutionSummaryProps {
  summary: ExecutionSummaryData;
  table: TableDefinition;
  columnProgress: Record<string, ColumnProgress>;
  onDismiss: () => void;
  onExport?: () => void;
  onExportSheet?: () => Promise<{ url: string }>;
  onExportDrive?: () => Promise<{ url: string }>;
  onSendToReview?: () => void;
  onRetryFailed?: () => void;
}

function formatDuration(ms: number): string {
  if (ms < 1000) return `${ms}ms`;
  const secs = ms / 1000;
  if (secs < 60) return `${secs.toFixed(1)}s`;
  const mins = Math.floor(secs / 60);
  const remSecs = Math.round(secs % 60);
  return `${mins}m ${remSecs}s`;
}

export function ExecutionSummary({
  summary,
  table,
  columnProgress,
  onDismiss,
  onExport,
  onExportSheet,
  onExportDrive,
  onSendToReview,
  onRetryFailed,
}: ExecutionSummaryProps) {
  const [sheetLoading, setSheetLoading] = useState(false);
  const [driveLoading, setDriveLoading] = useState(false);

  const totalCells = summary.cellsDone + summary.cellsErrored;
  const successRate = totalCells > 0 ? (summary.cellsDone / totalCells) * 100 : 0;
  const isGreatResult = successRate >= 90;

  const enrichmentCols = table.columns.filter(
    (c) => c.column_type !== "input" && c.column_type !== "static" && !c.hidden
  );

  // Compute per-column stats
  const colStats = enrichmentCols.map((col) => {
    const prog = columnProgress[col.id];
    const isDeepline = col.column_type === "enrichment" && col.tool && !["call_ai", "web_search", "gate", "run_javascript"].includes(col.tool);
    return {
      col,
      prog,
      isDeepline,
      rate: prog && prog.total > 0 ? (prog.done / prog.total) * 100 : 0,
    };
  });

  const handleExportSheet = async () => {
    if (!onExportSheet) return;
    setSheetLoading(true);
    try {
      const result = await onExportSheet();
      toast.success("Exported to Google Sheets");
      window.open(result.url, "_blank");
    } catch {
      toast.error("Failed to export to Sheets");
    } finally {
      setSheetLoading(false);
    }
  };

  const handleExportDrive = async () => {
    if (!onExportDrive) return;
    setDriveLoading(true);
    try {
      const result = await onExportDrive();
      toast.success("Saved to Google Drive");
      window.open(result.url, "_blank");
    } catch {
      toast.error("Failed to save to Drive");
    } finally {
      setDriveLoading(false);
    }
  };

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-50 flex items-center justify-center px-4"
      >
        {/* Backdrop */}
        <div
          className="absolute inset-0 bg-black/50 backdrop-blur-sm"
          onClick={onDismiss}
        />

        <motion.div
          initial={{ scale: 0.95, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          exit={{ scale: 0.95, opacity: 0 }}
          transition={{ type: "spring", damping: 25, stiffness: 350 }}
          className="relative w-full max-w-md"
        >
          <Card className="border-clay-600 bg-clay-800 shadow-2xl shadow-black/50">
            <CardContent className="p-6">
              {/* Close button */}
              <button
                onClick={onDismiss}
                className="absolute top-4 right-4 text-clay-400 hover:text-clay-200 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>

              {/* Status header — centered */}
              <div className="text-center mb-5">
                <div
                  className={cn(
                    "inline-flex items-center justify-center w-12 h-12 rounded-2xl mb-3",
                    isGreatResult
                      ? "bg-emerald-500/10 text-emerald-400"
                      : summary.cellsErrored > 0
                        ? "bg-amber-500/10 text-amber-400"
                        : "bg-kiln-teal/10 text-kiln-teal"
                  )}
                >
                  {isGreatResult ? (
                    <CheckCircle2 className="h-6 w-6" />
                  ) : (
                    <AlertTriangle className="h-6 w-6" />
                  )}
                </div>
                <h3 className="text-base font-semibold text-clay-100">
                  {summary.halted ? "Execution halted" : "Execution complete"}
                </h3>
                <p className="text-xs text-clay-400 mt-0.5">
                  {table.name} &middot; {table.row_count} rows
                </p>
              </div>

              {/* Stats strip */}
              <div className="grid grid-cols-3 gap-3 mb-5">
                <div className="rounded-xl bg-clay-700/40 px-3 py-2.5 text-center">
                  <div className="text-xl font-bold text-clay-100">
                    {summary.cellsDone}
                  </div>
                  <div className="text-[10px] text-clay-400 uppercase tracking-wider">
                    Succeeded
                  </div>
                </div>
                <div className="rounded-xl bg-clay-700/40 px-3 py-2.5 text-center">
                  <div className={cn(
                    "text-xl font-bold",
                    summary.cellsErrored > 0 ? "text-red-400" : "text-clay-100"
                  )}>
                    {summary.cellsErrored}
                  </div>
                  <div className="text-[10px] text-clay-400 uppercase tracking-wider">
                    Errors
                  </div>
                </div>
                <div className="rounded-xl bg-clay-700/40 px-3 py-2.5 text-center">
                  <div className="text-xl font-bold text-clay-100 flex items-center justify-center gap-1">
                    <Clock className="h-4 w-4 text-clay-400" />
                    {formatDuration(summary.totalDurationMs)}
                  </div>
                  <div className="text-[10px] text-clay-400 uppercase tracking-wider">
                    Duration
                  </div>
                </div>
              </div>

              {/* Success rate bar */}
              <div className="mb-5">
                <div className="flex items-center justify-between mb-1.5">
                  <span className="text-xs text-clay-400">Success rate</span>
                  <span className={cn(
                    "text-xs font-semibold",
                    isGreatResult ? "text-emerald-400" : "text-amber-400"
                  )}>
                    {successRate.toFixed(0)}%
                  </span>
                </div>
                <div className="h-2 rounded-full bg-clay-700 overflow-hidden">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all duration-700",
                      isGreatResult ? "bg-emerald-500" : "bg-amber-500"
                    )}
                    style={{ width: `${successRate}%` }}
                  />
                </div>
              </div>

              {/* Per-column breakdown */}
              {colStats.length > 0 && (
                <div className="mb-5">
                  <p className="text-[10px] text-clay-400 uppercase tracking-wider mb-2">
                    Column breakdown
                  </p>
                  <div className="space-y-2">
                    {colStats.map(({ col, prog, isDeepline, rate }) => {
                      if (!prog) return null;
                      return (
                        <div key={col.id} className="flex items-center gap-2">
                          {/* Icon: Deepline bolt or Claude brain */}
                          {isDeepline ? (
                            <Zap className="h-3 w-3 text-kiln-teal shrink-0" />
                          ) : (
                            <Brain className="h-3 w-3 text-purple-400 shrink-0" />
                          )}
                          <span className="text-xs text-clay-200 truncate flex-1">{col.name}</span>
                          <span className="text-[10px] text-clay-400 shrink-0">
                            {prog.done}/{prog.total}
                          </span>
                          {prog.errors > 0 && (
                            <span className="text-[10px] text-red-400 shrink-0">
                              {prog.errors} err
                            </span>
                          )}
                          {/* Mini progress bar */}
                          <div className="w-12 h-1.5 rounded-full bg-clay-700 overflow-hidden shrink-0">
                            <div
                              className={cn(
                                "h-full rounded-full",
                                rate >= 90 ? "bg-emerald-500" : rate > 0 ? "bg-amber-500" : "bg-clay-600"
                              )}
                              style={{ width: `${rate}%` }}
                            />
                          </div>
                          <span className={cn(
                            "text-[10px] font-medium w-7 text-right shrink-0",
                            rate >= 90 ? "text-emerald-400" : "text-amber-400"
                          )}>
                            {rate.toFixed(0)}%
                          </span>
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              {/* Action buttons — stacked for clarity */}
              <div className="space-y-2">
                {/* Primary row */}
                <div className="flex gap-2">
                  {onExport && (
                    <Button
                      size="sm"
                      className="bg-kiln-teal text-black hover:bg-kiln-teal/90 flex-1 h-9"
                      onClick={onExport}
                    >
                      <Download className="h-3.5 w-3.5 mr-1.5" />
                      Export CSV
                    </Button>
                  )}
                  {onExportSheet && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="border-clay-600 text-clay-200 hover:bg-clay-700 flex-1 h-9"
                      onClick={handleExportSheet}
                      disabled={sheetLoading}
                    >
                      {sheetLoading ? (
                        <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                      ) : (
                        <FileSpreadsheet className="h-3.5 w-3.5 mr-1.5" />
                      )}
                      Google Sheets
                    </Button>
                  )}
                </div>

                {/* Secondary row */}
                <div className="flex gap-2">
                  {onExportDrive && (
                    <Button
                      size="sm"
                      variant="outline"
                      className="border-clay-600 text-clay-200 hover:bg-clay-700 flex-1 h-9"
                      onClick={handleExportDrive}
                      disabled={driveLoading}
                    >
                      {driveLoading ? (
                        <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                      ) : (
                        <HardDrive className="h-3.5 w-3.5 mr-1.5" />
                      )}
                      Save to Drive
                    </Button>
                  )}
                  {onSendToReview && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="border-clay-600 text-clay-200 hover:bg-clay-700 flex-1 h-9"
                      onClick={onSendToReview}
                    >
                      <ClipboardCheck className="h-3.5 w-3.5 mr-1.5" />
                      Send to Review
                    </Button>
                  )}
                  {summary.cellsErrored > 0 && onRetryFailed && (
                    <Button
                      variant="outline"
                      size="sm"
                      className="border-red-500/30 text-red-400 hover:bg-red-500/10 flex-1 h-9"
                      onClick={onRetryFailed}
                    >
                      <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
                      Retry failed
                    </Button>
                  )}
                </div>
              </div>
            </CardContent>
          </Card>
        </motion.div>
      </motion.div>
    </AnimatePresence>
  );
}
