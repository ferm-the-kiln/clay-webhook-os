"use client";

import { Search, Brain, Calculator, Filter, Pencil, Type } from "lucide-react";
import type { TableDefinition, TableRow, TableColumn } from "@/lib/types";
import { getCellValue, getCellStatus } from "@/hooks/use-table-builder";

interface TableFormulaBarProps {
  table: TableDefinition;
  selectedCell: { rowId: string; columnId: string } | null;
  rows: TableRow[];
}

const TYPE_ICONS: Record<string, typeof Search> = {
  enrichment: Search,
  ai: Brain,
  formula: Calculator,
  gate: Filter,
  input: Pencil,
  static: Type,
};

function getColumnDescription(col: TableColumn): string {
  if (col.column_type === "enrichment" && col.tool) {
    const params = Object.entries(col.params)
      .map(([k, v]) => v)
      .join(", ");
    return `${col.tool}(${params})`;
  }
  if (col.column_type === "ai" && col.ai_prompt) {
    return col.ai_prompt.slice(0, 80) + (col.ai_prompt.length > 80 ? "..." : "");
  }
  if (col.column_type === "formula" && col.formula) {
    return `= ${col.formula}`;
  }
  if (col.column_type === "gate" && col.condition) {
    return `IF ${col.condition}`;
  }
  return "";
}

export function TableFormulaBar({
  table,
  selectedCell,
  rows,
}: TableFormulaBarProps) {
  if (!selectedCell) {
    return (
      <div className="h-8 shrink-0 flex items-center px-4 border-b border-clay-700 bg-clay-900/50">
        <span className="text-xs text-clay-300">Select a cell to see details</span>
      </div>
    );
  }

  const col = table.columns.find((c) => c.id === selectedCell.columnId);
  const row = rows.find((r) => r._row_id === selectedCell.rowId);

  if (!col || !row) {
    return (
      <div className="h-8 shrink-0 flex items-center px-4 border-b border-clay-700 bg-clay-900/50">
        <span className="text-xs text-clay-300">—</span>
      </div>
    );
  }

  const Icon = TYPE_ICONS[col.column_type] || Type;
  const value = getCellValue(row, col.id);
  const status = getCellStatus(row, col.id);
  const description = getColumnDescription(col);

  const displayValue =
    value === null || value === undefined
      ? ""
      : typeof value === "object"
        ? JSON.stringify(value).slice(0, 200)
        : String(value);

  // Find row index
  const rowIdx = rows.findIndex((r) => r._row_id === selectedCell.rowId);

  return (
    <div className="h-8 shrink-0 flex items-center gap-3 px-4 border-b border-clay-700 bg-clay-900/50">
      {/* Cell reference */}
      <span className="text-[10px] font-mono bg-clay-700 text-clay-200 px-1.5 py-0.5 rounded shrink-0">
        {col.name}:{rowIdx + 1}
      </span>

      {/* Column type icon */}
      <Icon className="w-3 h-3 text-clay-300 shrink-0" />

      {/* Formula or value */}
      {col.column_type === "input" || col.column_type === "static" ? (
        <span className="text-xs text-clay-100 truncate">{displayValue}</span>
      ) : (
        <div className="flex items-center gap-2 min-w-0 flex-1">
          {description && (
            <span className="text-xs text-clay-300 font-mono truncate">
              {description}
            </span>
          )}
          {status === "done" && displayValue && (
            <>
              <span className="text-clay-500">→</span>
              <span className="text-xs text-clay-100 truncate">{displayValue}</span>
            </>
          )}
          {status === "error" && (
            <span className="text-xs text-red-400">Error</span>
          )}
        </div>
      )}
    </div>
  );
}
