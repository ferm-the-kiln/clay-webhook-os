"use client";

import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { BarChart3 } from "lucide-react";
import type { TableColumn, TableRow } from "@/lib/types";
import { getCellValue, getCellStatus } from "@/hooks/use-table-builder";

interface ColumnStatsPopoverProps {
  column: TableColumn;
  rows: TableRow[];
  children: React.ReactNode;
}

interface ColumnStats {
  totalRows: number;
  filledCount: number;
  fillRate: number;
  uniqueCount: number;
  topValues: { value: string; count: number }[];
  // Number stats
  min?: number;
  max?: number;
  avg?: number;
  // Enrichment stats
  successCount: number;
  errorCount: number;
  avgDurationMs?: number;
}

function computeStats(column: TableColumn, rows: TableRow[]): ColumnStats {
  const values: unknown[] = [];
  let filled = 0;
  let successCount = 0;
  let errorCount = 0;

  for (const row of rows) {
    const val = getCellValue(row, column.id);
    const status = getCellStatus(row, column.id);
    if (val !== null && val !== undefined && val !== "") {
      values.push(val);
      filled++;
    }
    if (status === "done") successCount++;
    if (status === "error") errorCount++;
  }

  // Frequency count
  const freq: Record<string, number> = {};
  for (const v of values) {
    const key = typeof v === "object" ? "[object]" : String(v).slice(0, 50);
    freq[key] = (freq[key] || 0) + 1;
  }
  const topValues = Object.entries(freq)
    .sort((a, b) => b[1] - a[1])
    .slice(0, 5)
    .map(([value, count]) => ({ value, count }));

  const stats: ColumnStats = {
    totalRows: rows.length,
    filledCount: filled,
    fillRate: rows.length > 0 ? filled / rows.length : 0,
    uniqueCount: Object.keys(freq).length,
    topValues,
    successCount,
    errorCount,
  };

  // Number stats
  const numbers = values.filter((v) => typeof v === "number") as number[];
  if (numbers.length > 0) {
    stats.min = Math.min(...numbers);
    stats.max = Math.max(...numbers);
    stats.avg = numbers.reduce((a, b) => a + b, 0) / numbers.length;
  }

  return stats;
}

export function ColumnStatsPopover({
  column,
  rows,
  children,
}: ColumnStatsPopoverProps) {
  const stats = computeStats(column, rows);

  return (
    <Popover>
      <PopoverTrigger asChild>{children}</PopoverTrigger>
      <PopoverContent
        side="bottom"
        align="start"
        className="w-64 bg-clay-900 border-clay-500 p-3"
      >
        <div className="space-y-3">
          {/* Header */}
          <div className="flex items-center gap-2 text-sm font-medium text-white">
            <BarChart3 className="w-3.5 h-3.5 text-kiln-teal" />
            {column.name}
          </div>

          {/* Fill rate */}
          <div>
            <div className="flex justify-between text-xs mb-1">
              <span className="text-clay-200">Fill rate</span>
              <span className="text-clay-100">
                {Math.round(stats.fillRate * 100)}% ({stats.filledCount}/
                {stats.totalRows})
              </span>
            </div>
            <div className="h-1.5 rounded-full bg-clay-700 overflow-hidden">
              <div
                className="h-full bg-kiln-teal rounded-full"
                style={{ width: `${stats.fillRate * 100}%` }}
              />
            </div>
          </div>

          {/* Unique values */}
          <div className="flex justify-between text-xs">
            <span className="text-clay-200">Unique values</span>
            <span className="text-clay-100">{stats.uniqueCount}</span>
          </div>

          {/* Number stats */}
          {stats.min !== undefined && (
            <div className="grid grid-cols-3 gap-2 text-xs">
              <div>
                <div className="text-clay-300">Min</div>
                <div className="text-clay-100">{stats.min}</div>
              </div>
              <div>
                <div className="text-clay-300">Avg</div>
                <div className="text-clay-100">
                  {stats.avg?.toFixed(1)}
                </div>
              </div>
              <div>
                <div className="text-clay-300">Max</div>
                <div className="text-clay-100">{stats.max}</div>
              </div>
            </div>
          )}

          {/* Enrichment stats */}
          {(stats.successCount > 0 || stats.errorCount > 0) && (
            <div className="flex gap-3 text-xs">
              <span className="text-emerald-400">
                {stats.successCount} success
              </span>
              {stats.errorCount > 0 && (
                <span className="text-red-400">
                  {stats.errorCount} errors
                </span>
              )}
            </div>
          )}

          {/* Top values */}
          {stats.topValues.length > 0 && (
            <div>
              <div className="text-xs text-clay-300 mb-1">Top values</div>
              <div className="space-y-1">
                {stats.topValues.map((tv, i) => (
                  <div key={i} className="flex items-center gap-2 text-xs">
                    <div className="flex-1 truncate text-clay-100">
                      {tv.value}
                    </div>
                    <div className="flex items-center gap-1.5 shrink-0">
                      <div
                        className="h-1 rounded-full bg-kiln-teal/50"
                        style={{
                          width: `${(tv.count / stats.totalRows) * 60}px`,
                        }}
                      />
                      <span className="text-clay-300 tabular-nums w-5 text-right">
                        {tv.count}
                      </span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
      </PopoverContent>
    </Popover>
  );
}
