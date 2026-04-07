"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { Download, ExternalLink, RotateCcw, CheckCircle2, XCircle, Loader2 } from "lucide-react";
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
import type { WorkflowTemplate, TableExecutionEvent, TableColumn } from "@/lib/types";
import type { CsvPreview } from "./step-upload";

type Phase = "creating" | "importing" | "configuring" | "enriching" | "done" | "error";

interface LiveCell {
  column_id: string;
  value: unknown;
}

interface StepProgressProps {
  csvPreview: CsvPreview;
  selectedRecipes: WorkflowTemplate[];
  columnMapping: Record<string, string>;
  onStartOver: () => void;
  rowLimit?: number;
}

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
  const [liveCells, setLiveCells] = useState<LiveCell[]>([]);
  const [previewRows, setPreviewRows] = useState<Record<string, unknown>[]>([]);
  const [previewColumns, setPreviewColumns] = useState<TableColumn[]>([]);
  const [showConfetti, setShowConfetti] = useState(false);
  const abortRef = useRef<AbortController | null>(null);
  const startedRef = useRef(false);

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

      // 4. Execute
      setPhase("enriching");
      await new Promise<void>((resolve, reject) => {
        const controller = streamTableExecution(
          table.id,
          (event: TableExecutionEvent) => {
            if (event.type === "execute_start") {
              setProgress({ done: 0, total: event.total_rows, errors: 0 });
            } else if (event.type === "cell_update" && event.status === "done") {
              setLiveCells((prev) => [
                { column_id: event.column_id, value: event.value },
                ...prev.slice(0, 4),
              ]);
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

      // 5. Done — save to history + fetch preview
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

      // Fetch preview rows
      try {
        const [rowsData, tableDef] = await Promise.all([
          fetchTableRows(table.id, 0, 5),
          fetchTable(table.id),
        ]);
        setPreviewRows(rowsData.rows);
        setPreviewColumns(tableDef.columns.filter((c) => !c.hidden));
      } catch {}
    } catch (err) {
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

  // Dismiss confetti after 2s
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

  const phases: { key: Phase; label: string }[] = [
    { key: "creating", label: "Creating table" },
    { key: "importing", label: "Importing data" },
    { key: "configuring", label: "Setting up enrichment" },
    { key: "enriching", label: "Enriching your data" },
    { key: "done", label: "Done" },
  ];

  const currentIdx = phases.findIndex((p) => p.key === phase);
  const successRate =
    progress.total > 0
      ? Math.round(((progress.done - progress.errors) / progress.total) * 100)
      : 0;

  return (
    <div className="space-y-8">
      <div className="text-center space-y-1">
        {/* Confetti burst */}
        {showConfetti && <ConfettiBurst />}

        <h2 className="text-lg font-semibold text-clay-100">
          {phase === "done"
            ? "Your data is ready"
            : phase === "error"
              ? "Something went wrong"
              : "Enriching your data..."}
        </h2>
        {phase !== "done" && phase !== "error" && (
          <p className="text-sm text-clay-400">
            Sit tight, this usually takes a few minutes.
          </p>
        )}
      </div>

      {/* Phase progress */}
      {phase !== "error" && (
        <div className="space-y-3 max-w-md mx-auto">
          {phases.map((p, i) => {
            const isActive = p.key === phase;
            const isDone = i < currentIdx || phase === "done";

            return (
              <div key={p.key} className="flex items-center gap-3">
                <div className="w-5 flex justify-center">
                  {isDone ? (
                    <CheckCircle2 className="h-4 w-4 text-kiln-teal" />
                  ) : isActive ? (
                    <Loader2 className="h-4 w-4 text-kiln-teal animate-spin" />
                  ) : (
                    <div className="h-2 w-2 rounded-full bg-clay-600" />
                  )}
                </div>
                <span
                  className={cn(
                    "text-sm",
                    isDone
                      ? "text-clay-400"
                      : isActive
                        ? "text-clay-100 font-medium"
                        : "text-clay-500",
                  )}
                >
                  {p.label}
                </span>
              </div>
            );
          })}
        </div>
      )}

      {/* Enrichment progress bar */}
      {phase === "enriching" && progress.total > 0 && (
        <div className="max-w-md mx-auto space-y-2">
          <div className="h-2 rounded-full bg-clay-700 overflow-hidden">
            <div
              className="h-full rounded-full bg-kiln-teal transition-all duration-300"
              style={{ width: `${Math.min(100, (progress.done / progress.total) * 100)}%` }}
            />
          </div>
          <div className="flex justify-between text-xs text-clay-400">
            <span>{progress.done} / {progress.total} cells</span>
            {progress.errors > 0 && (
              <span className="text-amber-400">{progress.errors} errors</span>
            )}
          </div>
        </div>
      )}

      {/* Live cell preview during enrichment */}
      {phase === "enriching" && liveCells.length > 0 && (
        <div className="max-w-md mx-auto space-y-1">
          <div className="text-[10px] text-clay-500 uppercase tracking-wider">Live results</div>
          {liveCells.map((cell, i) => (
            <div
              key={`${cell.column_id}-${i}`}
              className="flex items-center gap-2 text-xs p-1.5 rounded bg-clay-800/30 border border-clay-700/50"
              style={{ animation: "fadeSlideIn 0.3s ease-out" }}
            >
              <span className="text-clay-500 font-mono truncate w-28 shrink-0">{cell.column_id}</span>
              <span className="text-clay-300 truncate flex-1">
                {typeof cell.value === "string"
                  ? cell.value
                  : cell.value != null
                    ? JSON.stringify(cell.value)
                    : "—"}
              </span>
            </div>
          ))}
          <style>{`
            @keyframes fadeSlideIn {
              from { opacity: 0; transform: translateY(4px); }
              to { opacity: 1; transform: translateY(0); }
            }
          `}</style>
        </div>
      )}

      {/* Quality summary card */}
      {phase === "done" && (
        <div className="grid grid-cols-3 gap-3 max-w-md mx-auto">
          <div className="rounded-lg bg-clay-800/50 border border-clay-700 p-3 text-center">
            <div className="text-lg font-semibold text-kiln-teal">{progress.done}</div>
            <div className="text-[10px] text-clay-400 uppercase tracking-wider">Cells Enriched</div>
          </div>
          <div className="rounded-lg bg-clay-800/50 border border-clay-700 p-3 text-center">
            <div className="text-lg font-semibold text-clay-100">{successRate}%</div>
            <div className="text-[10px] text-clay-400 uppercase tracking-wider">Success Rate</div>
          </div>
          <div className="rounded-lg bg-clay-800/50 border border-clay-700 p-3 text-center">
            <div className={cn("text-lg font-semibold", progress.errors > 0 ? "text-amber-400" : "text-clay-100")}>
              {progress.errors}
            </div>
            <div className="text-[10px] text-clay-400 uppercase tracking-wider">Errors</div>
          </div>
        </div>
      )}

      {/* Results preview table */}
      {phase === "done" && previewRows.length > 0 && previewColumns.length > 0 && (
        <div className="max-w-2xl mx-auto">
          <h3 className="text-xs font-medium text-clay-400 mb-2">
            Preview (first {previewRows.length} rows)
          </h3>
          <div className="rounded-md border border-clay-700 overflow-x-auto max-h-48">
            <table className="w-full text-xs">
              <thead>
                <tr>
                  {previewColumns.map((col) => (
                    <th
                      key={col.id}
                      className="px-3 py-1.5 text-left text-clay-400 font-medium border-b border-clay-700 bg-clay-800/50 whitespace-nowrap sticky top-0"
                    >
                      {col.name}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {previewRows.map((row, ri) => (
                  <tr key={ri} className="border-b border-clay-800/50 last:border-0">
                    {previewColumns.map((col) => {
                      const val = row[`${col.id}__value`];
                      const display =
                        val == null
                          ? ""
                          : typeof val === "object"
                            ? JSON.stringify(val)
                            : String(val);
                      return (
                        <td
                          key={col.id}
                          className="px-3 py-1.5 text-clay-300 whitespace-nowrap max-w-[200px] truncate"
                        >
                          {display || <span className="text-clay-600">&mdash;</span>}
                        </td>
                      );
                    })}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Done actions */}
      {phase === "done" && (
        <div className="flex flex-col items-center gap-4">
          <div className="flex gap-3">
            <Button
              onClick={handleDownload}
              className="bg-kiln-teal text-black hover:bg-kiln-teal/90"
            >
              <Download className="h-4 w-4 mr-2" />
              Download CSV
            </Button>
            {tableId && (
              <Button
                variant="outline"
                className="border-clay-600 text-clay-300"
                asChild
              >
                <a href={`/tables/${tableId}`}>
                  <ExternalLink className="h-4 w-4 mr-2" />
                  Open in Table Builder
                </a>
              </Button>
            )}
          </div>

          <button
            onClick={onStartOver}
            className="text-xs text-clay-400 hover:text-clay-200 flex items-center gap-1 mt-2"
          >
            <RotateCcw className="h-3 w-3" />
            Enrich another file
          </button>
        </div>
      )}

      {/* Error state */}
      {phase === "error" && (
        <div className="flex flex-col items-center gap-4">
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
  const colors = ["#4A9EAD", "#22c55e", "#eab308", "#f97316", "#a855f7"];

  return (
    <div className="relative h-0 flex justify-center pointer-events-none">
      {Array.from({ length: 15 }).map((_, i) => {
        const angle = (i / 15) * 360;
        const distance = 60 + Math.random() * 40;
        const color = colors[i % colors.length];
        return (
          <div
            key={i}
            className="absolute w-2 h-2 rounded-full"
            style={{
              backgroundColor: color,
              animation: "confetti-burst 1s ease-out forwards",
              animationDelay: `${i * 30}ms`,
              ["--tx" as string]: `${Math.cos((angle * Math.PI) / 180) * distance}px`,
              ["--ty" as string]: `${Math.sin((angle * Math.PI) / 180) * distance - 30}px`,
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
    </div>
  );
}
