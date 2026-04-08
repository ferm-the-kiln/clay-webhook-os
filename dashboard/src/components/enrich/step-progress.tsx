"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Download, ExternalLink, RotateCcw, CheckCircle2, XCircle, Loader2, Square, Search, Brain, Calculator, Filter } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import {
  createTable,
  importTableCsv,
  addTableColumn,
  streamTableExecution,
  exportTableCsv,
  fetchTableRows,
  fetchTable,
} from "@/lib/api";
import type { WorkflowTemplate, TableExecutionEvent, TableColumn, TableRow, CellState } from "@/lib/types";
import { EnrichmentCell } from "@/components/table-builder/enrichment-cell";
import type { CsvPreview } from "./step-upload";

type Phase = "creating" | "importing" | "configuring" | "enriching" | "done" | "error";

interface StepProgressProps {
  csvPreview: CsvPreview;
  selectedRecipes: WorkflowTemplate[];
  columnMapping: Record<string, string>;
  onStartOver: () => void;
  rowLimit?: number;
}

const COLUMN_TYPE_STYLES: Record<string, { icon: typeof Search; color: string }> = {
  enrichment: { icon: Search, color: "border-l-blue-500" },
  ai: { icon: Brain, color: "border-l-purple-500" },
  formula: { icon: Calculator, color: "border-l-teal-500" },
  gate: { icon: Filter, color: "border-l-amber-500" },
};

export function StepProgress({
  csvPreview,
  selectedRecipes,
  columnMapping,
  onStartOver,
  rowLimit,
}: StepProgressProps) {
  const [phase, setPhase] = useState<Phase>("creating");
  const [tableId, setTableId] = useState<string | null>(null);
  const [tableName, setTableName] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string>("");
  const [progress, setProgress] = useState({ done: 0, total: 0, errors: 0 });
  const [columns, setColumns] = useState<TableColumn[]>([]);
  const [rows, setRows] = useState<TableRow[]>([]);
  const [showConfetti, setShowConfetti] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const startedRef = useRef(false);
  const gridRef = useRef<HTMLDivElement>(null);

  const handleStop = useCallback(() => {
    abortRef.current?.abort();
    setPhase("done");
  }, []);

  const run = useCallback(async () => {
    if (startedRef.current) return;
    startedRef.current = true;

    try {
      // 1. Create table
      setPhase("creating");
      const name = `Enrichment - ${new Date().toLocaleDateString("en-US", {
        month: "short",
        day: "numeric",
        year: "numeric",
        hour: "numeric",
        minute: "2-digit",
      })}`;
      setTableName(name);
      const table = await createTable({ name });
      setTableId(table.id);

      // 2. Import CSV
      setPhase("importing");
      await importTableCsv(table.id, csvPreview.file, columnMapping);

      // 3. Add enrichment columns from recipes
      setPhase("configuring");
      for (const recipe of selectedRecipes) {
        for (const col of recipe.columns) {
          await addTableColumn(table.id, {
            name: col.name,
            column_type: col.column_type,
            tool: col.tool,
            params: col.params,
            ai_prompt: col.ai_prompt,
            ai_model: col.ai_model,
            output_key: col.output_key,
          });
        }
      }

      // 4. Fetch table definition + rows for the grid
      const [tableDef, rowsData] = await Promise.all([
        fetchTable(table.id),
        fetchTableRows(table.id, 0, rowLimit ?? 1000),
      ]);
      setColumns(tableDef.columns.filter((c) => !c.hidden));
      setRows(rowsData.rows as TableRow[]);

      // 5. Execute with SSE — update grid cells in real-time
      setPhase("enriching");
      await new Promise<void>((resolve, reject) => {
        const controller = streamTableExecution(
          table.id,
          (event: TableExecutionEvent) => {
            if (event.type === "execute_start") {
              setProgress({ done: 0, total: event.total_rows, errors: 0 });
            } else if (event.type === "cell_update") {
              // Update the specific cell in the rows state
              setRows((prev) =>
                prev.map((r) =>
                  r._row_id === event.row_id
                    ? {
                        ...r,
                        [`${event.column_id}__value`]: event.value,
                        [`${event.column_id}__status`]: event.status,
                        [`${event.column_id}__error`]: event.error,
                      }
                    : r,
                ),
              );
            } else if (event.type === "column_progress") {
              setProgress((prev) => ({
                ...prev,
                done: event.done,
                errors: event.errors,
              }));
            } else if (event.type === "execute_complete") {
              setProgress({
                done: event.cells_done,
                total: event.cells_done + event.cells_errored,
                errors: event.cells_errored,
              });
              resolve();
            }
          },
          (err) => reject(new Error(err)),
          rowLimit ? { limit: rowLimit } : undefined,
        );
        abortRef.current = controller;
      });

      // 6. Done
      setPhase("done");
      setShowConfetti(true);

      // Save to localStorage for history
      try {
        const entry = {
          id: table.id,
          name: csvPreview.file.name,
          rows: csvPreview.totalRows,
          recipes: selectedRecipes.map((r) => r.name),
          timestamp: Date.now(),
        };
        const history = JSON.parse(localStorage.getItem("enrich-history") || "[]");
        history.unshift(entry);
        localStorage.setItem("enrich-history", JSON.stringify(history.slice(0, 10)));
      } catch {}
    } catch (err) {
      if ((err as Error)?.name === "AbortError") {
        setPhase("done");
        return;
      }
      setErrorMsg(err instanceof Error ? err.message : "Something went wrong");
      setPhase("error");
    }
  }, [csvPreview, selectedRecipes, columnMapping, rowLimit]);

  useEffect(() => {
    run();
    return () => {
      abortRef.current?.abort();
    };
  }, [run]);

  useEffect(() => {
    if (showConfetti) {
      const t = setTimeout(() => setShowConfetti(false), 2000);
      return () => clearTimeout(t);
    }
  }, [showConfetti]);

  const handleDownload = useCallback(async () => {
    if (!tableId) return;
    try {
      const blob = await exportTableCsv(tableId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${tableName || "enriched"}.csv`;
      a.click();
      URL.revokeObjectURL(url);
    } catch {
      setErrorMsg("Failed to export CSV");
    }
  }, [tableId, tableName]);

  const pct = progress.total > 0 ? Math.min(100, Math.round((progress.done / progress.total) * 100)) : 0;
  const showGrid = columns.length > 0 && rows.length > 0;
  const isPreGrid = phase === "creating" || phase === "importing" || phase === "configuring";

  return (
    <div className="space-y-4">
      {/* ── Status bar ── */}
      {phase !== "error" && (
        <div className="flex items-center gap-3">
          {/* Phase indicator */}
          <div className="flex items-center gap-2 flex-1 min-w-0">
            {isPreGrid ? (
              <>
                <Loader2 className="h-4 w-4 text-kiln-teal animate-spin shrink-0" />
                <span className="text-sm text-clay-200">
                  {phase === "creating"
                    ? "Creating table..."
                    : phase === "importing"
                      ? "Importing data..."
                      : "Setting up enrichment..."}
                </span>
              </>
            ) : phase === "enriching" ? (
              <>
                <Loader2 className="h-4 w-4 text-kiln-teal animate-spin shrink-0" />
                <span className="text-sm text-clay-200">Enriching...</span>
                <div className="flex-1 h-1.5 rounded-full bg-clay-700 overflow-hidden max-w-xs">
                  <div
                    className="h-full rounded-full bg-kiln-teal transition-all duration-300"
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <span className="text-xs text-clay-400 tabular-nums shrink-0">
                  {progress.done}/{progress.total}
                </span>
                {progress.errors > 0 && (
                  <span className="text-xs text-amber-400 shrink-0">{progress.errors} err</span>
                )}
              </>
            ) : (
              <>
                {showConfetti && <ConfettiBurst />}
                <CheckCircle2 className="h-4 w-4 text-kiln-teal shrink-0" />
                <span className="text-sm text-clay-200">
                  Done — {progress.done} cells enriched
                  {progress.errors > 0 && (
                    <span className="text-amber-400 ml-1">({progress.errors} errors)</span>
                  )}
                </span>
              </>
            )}
          </div>

          {/* Action buttons */}
          <div className="flex items-center gap-2 shrink-0">
            {phase === "enriching" && (
              <Button
                variant="outline"
                size="sm"
                className="h-7 border-red-500/30 text-red-400 hover:bg-red-500/10 hover:text-red-300"
                onClick={handleStop}
              >
                <Square className="h-3 w-3 mr-1 fill-current" />
                Stop
              </Button>
            )}
            {phase === "done" && (
              <>
                <Button
                  size="sm"
                  className="h-7 bg-kiln-teal text-black hover:bg-kiln-teal/90"
                  onClick={handleDownload}
                >
                  <Download className="h-3 w-3 mr-1" />
                  Download CSV
                </Button>
                {tableId && (
                  <Button variant="outline" size="sm" className="h-7 border-clay-600 text-clay-300" asChild>
                    <a href={`/tables/${tableId}`}>
                      <ExternalLink className="h-3 w-3 mr-1" />
                      Table Builder
                    </a>
                  </Button>
                )}
                <button
                  onClick={onStartOver}
                  className="text-xs text-clay-500 hover:text-clay-300 flex items-center gap-1 ml-1"
                >
                  <RotateCcw className="h-3 w-3" />
                </button>
              </>
            )}
          </div>
        </div>
      )}

      {/* ── Pre-grid loading state ── */}
      {isPreGrid && !showGrid && (
        <div className="flex items-center justify-center py-24">
          <div className="text-center space-y-3">
            <div className="h-10 w-10 mx-auto rounded-full border-2 border-kiln-teal border-t-transparent animate-spin" />
            <p className="text-sm text-clay-400">Preparing your data...</p>
          </div>
        </div>
      )}

      {/* ── Live spreadsheet grid ── */}
      {showGrid && (
        <div
          ref={gridRef}
          className="rounded-lg border border-clay-700 overflow-auto"
          style={{ maxHeight: "calc(100vh - 240px)" }}
        >
          <table className="w-full text-xs border-collapse">
            <thead className="sticky top-0 z-10">
              <tr>
                <th className="px-2 py-2 text-left text-clay-500 font-medium bg-clay-800 border-b border-clay-700 w-10 text-[10px]">
                  #
                </th>
                {columns.map((col) => {
                  const typeStyle = COLUMN_TYPE_STYLES[col.column_type];
                  return (
                    <th
                      key={col.id}
                      className={cn(
                        "px-3 py-2 text-left font-medium border-b border-clay-700 bg-clay-800 whitespace-nowrap min-w-[140px]",
                        typeStyle ? `border-l-2 ${typeStyle.color}` : "border-l-2 border-l-clay-600",
                      )}
                    >
                      <div className="flex items-center gap-1.5">
                        {typeStyle && <typeStyle.icon className="h-3 w-3 text-clay-400 shrink-0" />}
                        <span className="text-clay-200 truncate">{col.name}</span>
                      </div>
                      {col.column_type !== "input" && col.tool && (
                        <div className="text-[9px] text-clay-500 mt-0.5">{col.tool}</div>
                      )}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {rows.map((row, ri) => (
                <tr
                  key={row._row_id}
                  className="border-b border-clay-800/50 last:border-0 hover:bg-clay-800/30 transition-colors"
                >
                  <td className="px-2 py-1.5 text-clay-600 text-[10px] tabular-nums">
                    {ri + 1}
                  </td>
                  {columns.map((col) => {
                    const value = row[`${col.id}__value`];
                    const status = (row[`${col.id}__status`] as CellState) || (col.column_type === "input" ? "done" : "empty");
                    const error = row[`${col.id}__error`] as string | undefined;

                    return (
                      <td
                        key={col.id}
                        className={cn(
                          "px-3 py-1.5 max-w-[250px]",
                          col.column_type === "input"
                            ? "text-clay-300"
                            : "",
                        )}
                      >
                        {col.column_type === "input" ? (
                          <span className="truncate block">
                            {value != null ? String(value) : <span className="text-clay-600">&mdash;</span>}
                          </span>
                        ) : (
                          <EnrichmentCell
                            value={value}
                            status={status}
                            error={error}
                          />
                        )}
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Error state ── */}
      {phase === "error" && (
        <div className="flex flex-col items-center gap-4 py-12">
          <div className="flex items-center gap-2 text-sm text-red-400">
            <XCircle className="h-4 w-4" />
            {errorMsg}
          </div>
          <Button
            variant="outline"
            className="border-clay-600 text-clay-300"
            onClick={onStartOver}
          >
            <RotateCcw className="h-4 w-4 mr-2" />
            Start over
          </Button>
        </div>
      )}
    </div>
  );
}

/* ─── Confetti burst animation ────────────────────────── */

function ConfettiBurst() {
  const [visible, setVisible] = useState(true);
  const colors = ["#4A9EAD", "#22c55e", "#eab308", "#f97316", "#a855f7"];

  useEffect(() => {
    const t = setTimeout(() => setVisible(false), 2000);
    return () => clearTimeout(t);
  }, []);

  if (!visible) return null;

  return (
    <span className="relative inline-flex pointer-events-none">
      {Array.from({ length: 12 }).map((_, i) => {
        const angle = (i / 12) * 360;
        const distance = 20 + Math.random() * 15;
        const color = colors[i % colors.length];
        return (
          <span
            key={i}
            className="absolute w-1.5 h-1.5 rounded-full"
            style={{
              backgroundColor: color,
              animation: "confetti-burst 0.8s ease-out forwards",
              animationDelay: `${i * 25}ms`,
              ["--tx" as string]: `${Math.cos((angle * Math.PI) / 180) * distance}px`,
              ["--ty" as string]: `${Math.sin((angle * Math.PI) / 180) * distance}px`,
            }}
          />
        );
      })}
      <style>{`
        @keyframes confetti-burst {
          0% { transform: translate(0, 0) scale(1); opacity: 1; }
          100% { transform: translate(var(--tx), var(--ty)) scale(0); opacity: 0; }
        }
      `}</style>
    </span>
  );
}
