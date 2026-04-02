"use client";

import { motion } from "framer-motion";
import type { TableDefinition, TableRow, CellState } from "@/lib/types";
import { getCellStatus } from "@/hooks/use-table-builder";

interface TableStatusBarProps {
  table: TableDefinition;
  rows: TableRow[];
  executing: boolean;
  onFilterByStatus?: (status: CellState | "all") => void;
}

interface StatusCounts {
  total: number;
  done: number;
  errors: number;
  pending: number;
  running: number;
  filtered: number;
  empty: number;
}

function computeStats(table: TableDefinition, rows: TableRow[]): StatusCounts {
  const enrichCols = table.columns.filter(
    (c) => c.column_type !== "input" && c.column_type !== "static",
  );
  const counts: StatusCounts = {
    total: rows.length,
    done: 0,
    errors: 0,
    pending: 0,
    running: 0,
    filtered: 0,
    empty: 0,
  };

  for (const row of rows) {
    let rowBest: CellState = "empty";
    for (const col of enrichCols) {
      const status = getCellStatus(row, col.id);
      if (status === "done") counts.done++;
      else if (status === "error") counts.errors++;
      else if (status === "pending") counts.pending++;
      else if (status === "running") counts.running++;
      else if (status === "filtered") counts.filtered++;
      else counts.empty++;
    }
  }

  return counts;
}

export function TableStatusBar({
  table,
  rows,
  executing,
  onFilterByStatus,
}: TableStatusBarProps) {
  const stats = computeStats(table, rows);
  const enrichCols = table.columns.filter(
    (c) => c.column_type !== "input" && c.column_type !== "static",
  );
  const totalCells = rows.length * enrichCols.length;
  const progressPercent =
    totalCells > 0
      ? Math.round(((stats.done + stats.errors) / totalCells) * 100)
      : 0;

  return (
    <div className="relative shrink-0 border-t border-zinc-800 bg-zinc-900/80 backdrop-blur-sm px-4 py-1.5">
      {/* Progress bar during execution */}
      {executing && (
        <motion.div
          className="absolute top-0 left-0 h-0.5 bg-emerald-500"
          initial={{ width: 0 }}
          animate={{ width: `${progressPercent}%` }}
          transition={{ duration: 0.3 }}
        />
      )}

      <div className="flex items-center gap-4 text-xs">
        {/* Row count */}
        <button
          className="text-zinc-400 hover:text-white transition-colors"
          onClick={() => onFilterByStatus?.("all")}
        >
          {stats.total} rows
        </button>

        <span className="text-zinc-700">|</span>

        {/* Done */}
        {stats.done > 0 && (
          <button
            className="flex items-center gap-1 text-emerald-400 hover:text-emerald-300 transition-colors"
            onClick={() => onFilterByStatus?.("done")}
          >
            <div className="w-1.5 h-1.5 rounded-full bg-emerald-500" />
            {stats.done} enriched
          </button>
        )}

        {/* Errors */}
        {stats.errors > 0 && (
          <button
            className="flex items-center gap-1 text-red-400 hover:text-red-300 transition-colors"
            onClick={() => onFilterByStatus?.("error")}
          >
            <div className="w-1.5 h-1.5 rounded-full bg-red-500" />
            {stats.errors} errors
          </button>
        )}

        {/* Pending + Running */}
        {(stats.pending > 0 || stats.running > 0) && (
          <button
            className="flex items-center gap-1 text-amber-400 hover:text-amber-300 transition-colors"
            onClick={() => onFilterByStatus?.("pending")}
          >
            <div className="w-1.5 h-1.5 rounded-full bg-amber-500" />
            {stats.pending + stats.running} pending
          </button>
        )}

        {/* Filtered */}
        {stats.filtered > 0 && (
          <button
            className="flex items-center gap-1 text-zinc-500 hover:text-zinc-400 transition-colors"
            onClick={() => onFilterByStatus?.("filtered")}
          >
            {stats.filtered} filtered
          </button>
        )}

        {/* Spacer */}
        <div className="flex-1" />

        {/* Execution progress */}
        {executing && (
          <span className="text-zinc-500 tabular-nums">
            {progressPercent}% complete
          </span>
        )}

        {/* Column count */}
        <span className="text-zinc-600">
          {enrichCols.length} enrichment col{enrichCols.length !== 1 ? "s" : ""}
        </span>
      </div>
    </div>
  );
}
