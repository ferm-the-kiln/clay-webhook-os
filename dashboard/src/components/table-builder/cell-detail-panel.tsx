"use client";

import { useMemo, useState } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Copy, Plus, ChevronUp, ChevronDown } from "lucide-react";
import { toast } from "sonner";
import type { TableDefinition, TableRow } from "@/lib/types";
import { getCellValue, getCellStatus, getCellError } from "@/hooks/use-table-builder";
import { extractPreviewText } from "@/lib/cell-display";

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

function formatFieldLabel(key: string): string {
  return key.replace(/_/g, " ");
}

function ReadableValue({ data }: { data: unknown }) {
  if (data === null || data === undefined) {
    return <span className="text-clay-300 italic">No data</span>;
  }
  if (typeof data === "string") {
    if (!data.trim()) return <span className="text-clay-300 italic">Empty</span>;
    return <p className="text-clay-100 whitespace-pre-wrap leading-relaxed">{data}</p>;
  }
  if (typeof data === "number" || typeof data === "boolean") {
    return <span className="text-clay-100">{String(data)}</span>;
  }
  if (Array.isArray(data)) {
    if (data.length === 0) return <span className="text-clay-300 italic">Empty list</span>;
    const allScalars = data.every(
      (d) => typeof d === "string" || typeof d === "number" || typeof d === "boolean",
    );
    if (allScalars) {
      return (
        <ul className="list-disc list-inside space-y-1 text-clay-100">
          {data.map((item, i) => (
            <li key={i} className="whitespace-pre-wrap">{String(item)}</li>
          ))}
        </ul>
      );
    }
    return (
      <div className="space-y-3">
        {data.map((item, i) => (
          <div key={i} className="pl-3 border-l border-clay-700">
            <div className="text-[10px] uppercase tracking-wide text-clay-300 mb-1">
              Item {i + 1}
            </div>
            <ReadableValue data={item} />
          </div>
        ))}
      </div>
    );
  }
  if (typeof data === "object") {
    const entries = Object.entries(data as Record<string, unknown>);
    if (entries.length === 0) return <span className="text-clay-300 italic">Empty</span>;
    return (
      <div className="space-y-3">
        {entries.map(([key, val]) => (
          <div key={key}>
            <div className="text-[11px] uppercase tracking-wide text-clay-300 mb-1">
              {formatFieldLabel(key)}
            </div>
            <div className="text-xs text-clay-100">
              <ReadableValue data={val} />
            </div>
          </div>
        ))}
      </div>
    );
  }
  return <span className="text-clay-100">{String(data)}</span>;
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
  const [showRaw, setShowRaw] = useState(false);

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

          {/* Result */}
          <div>
            <div className="flex items-center justify-between mb-2">
              <h4 className="text-xs font-medium text-clay-200">Result</h4>
              {value !== undefined && value !== null && typeof value === "object" && (
                <button
                  onClick={() => setShowRaw((v) => !v)}
                  className="text-[10px] text-clay-300 hover:text-clay-100"
                >
                  {showRaw ? "Show readable" : "Show raw JSON"}
                </button>
              )}
            </div>
            <div className="px-3 py-3 rounded bg-clay-900 border border-clay-700 text-xs max-h-[500px] overflow-y-auto">
              {value !== undefined && value !== null ? (
                showRaw ? (
                  <JsonTree data={value} onAddAsColumn={onAddAsColumn} />
                ) : (
                  <ReadableValue data={value} />
                )
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
                  const preview = extractPreviewText(cellVal).slice(0, 100);
                  const displayVal = preview || "—";

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
