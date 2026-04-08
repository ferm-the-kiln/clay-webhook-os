"use client";

import { useMemo } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Button } from "@/components/ui/button";
import { Copy, Plus, RotateCcw, ChevronUp, ChevronDown, X } from "lucide-react";
import { toast } from "sonner";
import type { TableDefinition, TableRow, TableColumn, CellState } from "@/lib/types";
import { getCellValue, getCellStatus, getCellError } from "@/hooks/use-table-builder";

interface CellDetailPanelProps {
  open: boolean;
  onClose: () => void;
  table: TableDefinition;
  row: TableRow | null;
  columnId: string | null;
  onAddAsColumn?: (path: string, value: unknown) => void;
  onNavigate?: (direction: "up" | "down") => void;
}

function JsonTree({
  data,
  path = "",
  onAddAsColumn,
}: {
  data: unknown;
  path?: string;
  onAddAsColumn?: (path: string, value: unknown) => void;
}) {
  if (data === null || data === undefined) {
    return <span className="text-clay-300 italic">null</span>;
  }

  if (typeof data === "string") {
    return (
      <div className="flex items-start gap-2 group">
        <span className="text-emerald-400 break-all">&quot;{data}&quot;</span>
        <button
          onClick={() => {
            navigator.clipboard.writeText(data);
            toast.success("Copied");
          }}
          className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-clay-500"
        >
          <Copy className="w-3 h-3 text-clay-300" />
        </button>
      </div>
    );
  }

  if (typeof data === "number" || typeof data === "boolean") {
    return <span className="text-amber-400">{String(data)}</span>;
  }

  if (Array.isArray(data)) {
    return (
      <div className="space-y-1 pl-3 border-l border-clay-700">
        {data.map((item, i) => (
          <div key={i}>
            <span className="text-clay-300 text-xs">[{i}]</span>
            <div className="pl-2">
              <JsonTree data={item} path={`${path}[${i}]`} onAddAsColumn={onAddAsColumn} />
            </div>
          </div>
        ))}
      </div>
    );
  }

  if (typeof data === "object") {
    return (
      <div className="space-y-1.5 pl-3 border-l border-clay-700">
        {Object.entries(data as Record<string, unknown>).map(([key, val]) => {
          const fieldPath = path ? `${path}.${key}` : key;
          const isSimple =
            typeof val === "string" || typeof val === "number" || typeof val === "boolean";
          return (
            <div key={key} className="group/field">
              <div className="flex items-center gap-1.5">
                <span className="text-blue-400 text-xs font-mono">{key}:</span>
                {isSimple && (
                  <span className="text-clay-100 text-xs truncate flex-1">
                    {typeof val === "string" ? `"${val}"` : String(val)}
                  </span>
                )}
                {onAddAsColumn && isSimple && (
                  <button
                    onClick={() => onAddAsColumn(fieldPath, val)}
                    className="opacity-0 group-hover/field:opacity-100 flex items-center gap-0.5 px-1.5 py-0.5 rounded text-[10px] bg-clay-700 hover:bg-clay-500 text-kiln-teal"
                    title="Add as column"
                  >
                    <Plus className="w-2.5 h-2.5" />
                    Column
                  </button>
                )}
              </div>
              {!isSimple && (
                <div className="mt-1">
                  <JsonTree data={val} path={fieldPath} onAddAsColumn={onAddAsColumn} />
                </div>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  return <span className="text-clay-300">{String(data)}</span>;
}

export function CellDetailPanel({
  open,
  onClose,
  table,
  row,
  columnId,
  onAddAsColumn,
  onNavigate,
}: CellDetailPanelProps) {
  const column = useMemo(
    () => table.columns.find((c) => c.id === columnId),
    [table.columns, columnId],
  );

  if (!row || !column) return null;

  const value = getCellValue(row, column.id);
  const status = getCellStatus(row, column.id);
  const error = getCellError(row, column.id);

  const statusLabel =
    status === "done" ? "Completed" :
    status === "error" ? "Error" :
    status === "running" ? "Running" :
    status === "pending" ? "Pending" :
    status === "filtered" ? "Filtered" :
    "Empty";

  const statusColor =
    status === "done" ? "text-emerald-400" :
    status === "error" ? "text-red-400" :
    status === "running" ? "text-blue-400" :
    "text-clay-300";

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent
        side="right"
        className="w-[420px] bg-clay-950 border-clay-700 text-white overflow-y-auto"
      >
        <SheetHeader>
          <div className="flex items-center justify-between">
            <SheetTitle className="text-white text-sm">{column.name}</SheetTitle>
            <div className="flex items-center gap-1">
              {onNavigate && (
                <>
                  <button
                    onClick={() => onNavigate("up")}
                    className="p-1 rounded hover:bg-clay-700 text-clay-200"
                    title="Previous row"
                  >
                    <ChevronUp className="w-4 h-4" />
                  </button>
                  <button
                    onClick={() => onNavigate("down")}
                    className="p-1 rounded hover:bg-clay-700 text-clay-200"
                    title="Next row"
                  >
                    <ChevronDown className="w-4 h-4" />
                  </button>
                </>
              )}
            </div>
          </div>
          <SheetDescription className="text-clay-300 text-xs">
            Row: {row._row_id}
          </SheetDescription>
        </SheetHeader>

        <div className="mt-4 space-y-4">
          {/* Status */}
          <div className="flex items-center gap-2 px-3 py-2 rounded bg-clay-900 border border-clay-700">
            <div
              className={`w-2 h-2 rounded-full ${
                status === "done" ? "bg-emerald-500" :
                status === "error" ? "bg-red-500" :
                status === "running" ? "bg-blue-500 animate-pulse" :
                "bg-clay-400"
              }`}
            />
            <span className={`text-xs font-medium ${statusColor}`}>{statusLabel}</span>
          </div>

          {/* Error details */}
          {error && (
            <div className="px-3 py-2 rounded bg-red-500/10 border border-red-500/20">
              <p className="text-xs text-red-400">{error}</p>
            </div>
          )}

          {/* Value / JSON tree */}
          <div>
            <h4 className="text-xs font-medium text-clay-200 mb-2">Result</h4>
            <div className="px-3 py-2 rounded bg-clay-900 border border-clay-700 text-xs max-h-[400px] overflow-y-auto">
              {value !== undefined && value !== null ? (
                <JsonTree data={value} onAddAsColumn={onAddAsColumn} />
              ) : (
                <span className="text-clay-300 italic">No data</span>
              )}
            </div>
          </div>

          {/* All row data */}
          <div>
            <h4 className="text-xs font-medium text-clay-200 mb-2">All Columns</h4>
            <div className="space-y-1">
              {table.columns
                .filter((c) => !c.hidden)
                .map((col) => {
                  const cellVal = getCellValue(row, col.id);
                  const cellStatus = getCellStatus(row, col.id);
                  const displayVal =
                    cellVal === undefined || cellVal === null
                      ? "—"
                      : typeof cellVal === "object"
                        ? JSON.stringify(cellVal).slice(0, 100)
                        : String(cellVal).slice(0, 100);

                  return (
                    <div
                      key={col.id}
                      className={`flex items-center gap-2 px-2 py-1.5 rounded text-xs ${
                        col.id === columnId ? "bg-clay-700" : "hover:bg-clay-900"
                      }`}
                    >
                      <div
                        className={`w-1.5 h-1.5 rounded-full shrink-0 ${
                          cellStatus === "done" ? "bg-emerald-500" :
                          cellStatus === "error" ? "bg-red-500" :
                          "bg-clay-400"
                        }`}
                      />
                      <span className="text-clay-300 w-24 truncate shrink-0">{col.name}</span>
                      <span className="text-clay-100 truncate">{displayVal}</span>
                    </div>
                  );
                })}
            </div>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
