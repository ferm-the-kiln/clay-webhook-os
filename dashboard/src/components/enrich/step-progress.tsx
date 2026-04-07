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
} from "@/lib/api";
import type { WorkflowTemplate, TableExecutionEvent } from "@/lib/types";
import type { CsvPreview } from "./step-upload";

type Phase = "creating" | "importing" | "configuring" | "enriching" | "done" | "error";

interface StepProgressProps {
  csvPreview: CsvPreview;
  selectedRecipes: WorkflowTemplate[];
  columnMapping: Record<string, string>;
  onStartOver: () => void;
}

export function StepProgress({
  csvPreview,
  selectedRecipes,
  columnMapping,
  onStartOver,
}: StepProgressProps) {
  const [phase, setPhase] = useState<Phase>("creating");
  const [tableId, setTableId] = useState<string | null>(null);
  const [tableName, setTableName] = useState<string>("");
  const [errorMsg, setErrorMsg] = useState<string>("");
  const [progress, setProgress] = useState({ done: 0, total: 0, errors: 0 });
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
        );
        abortRef.current = controller;
      });

      setPhase("done");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Something went wrong");
      setPhase("error");
    }
  }, [csvPreview, selectedRecipes, columnMapping]);

  useEffect(() => {
    run();
    return () => {
      abortRef.current?.abort();
    };
  }, [run]);

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

  return (
    <div className="space-y-8">
      <div className="text-center space-y-1">
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

      {/* Done state */}
      {phase === "done" && (
        <div className="flex flex-col items-center gap-4">
          <div className="flex items-center gap-2 text-sm text-clay-300">
            <CheckCircle2 className="h-4 w-4 text-kiln-teal" />
            {progress.done} cells enriched
            {progress.errors > 0 && (
              <span className="text-amber-400">({progress.errors} errors)</span>
            )}
          </div>

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
