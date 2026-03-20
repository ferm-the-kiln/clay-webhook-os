"use client";

import { useRef, useCallback } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import Papa from "papaparse";
import type { Job } from "@/lib/types";
import { useSpreadsheet } from "./use-spreadsheet";
import { SpreadsheetToolbar } from "./spreadsheet-toolbar";
import { SpreadsheetHeaderCell } from "./spreadsheet-header";
import { SpreadsheetRowComponent } from "./spreadsheet-row";
import { SpreadsheetFooter } from "./spreadsheet-footer";

export function SpreadsheetView({
  jobs,
  originalRows,
  csvHeaders,
  onRetrySelected,
  onPushSelected,
  onRowClick,
}: {
  jobs: Job[];
  originalRows: Record<string, string>[];
  csvHeaders: string[];
  onRetrySelected?: (jobIds: string[]) => void;
  onPushSelected?: (jobIds: string[]) => void;
  onRowClick?: (job: Job) => void;
}) {
  const {
    table,
    stats,
    selectedJobIds,
    statusFilter,
    setStatusFilter,
    globalFilter,
    setGlobalFilter,
    selectAllFailed,
    clearSelection,
  } = useSpreadsheet(jobs, originalRows, csvHeaders);

  const parentRef = useRef<HTMLDivElement>(null);

  const { rows } = table.getRowModel();

  const virtualizer = useVirtualizer({
    count: rows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 40,
    overscan: 15,
  });

  const downloadCsv = useCallback(() => {
    const csvRows = jobs.map((job, i) => {
      const original = originalRows[i] || {};
      const result = job.result || {};
      return {
        ...original,
        _status: job.status,
        _duration_ms: job.duration_ms,
        _error: job.error || "",
        ...Object.fromEntries(
          Object.entries(result).map(([k, v]) => [
            `_result_${k}`,
            typeof v === "string" ? v : JSON.stringify(v),
          ])
        ),
      };
    });
    const csv = Papa.unparse(csvRows);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `batch-results-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [jobs, originalRows]);

  const exportSelected = useCallback(() => {
    const selectedJobs = jobs.filter((j) => selectedJobIds.includes(j.id));
    const csvRows = selectedJobs.map((job) => {
      const idx = jobs.indexOf(job);
      const original = originalRows[idx] || {};
      const result = job.result || {};
      return {
        ...original,
        _status: job.status,
        _duration_ms: job.duration_ms,
        _error: job.error || "",
        ...Object.fromEntries(
          Object.entries(result).map(([k, v]) => [
            `_result_${k}`,
            typeof v === "string" ? v : JSON.stringify(v),
          ])
        ),
      };
    });
    const csv = Papa.unparse(csvRows);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `batch-selected-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [jobs, originalRows, selectedJobIds]);

  return (
    <div className="rounded-xl border border-clay-500  overflow-hidden">
      <SpreadsheetToolbar
        statusFilter={statusFilter}
        onStatusFilterChange={setStatusFilter}
        globalFilter={globalFilter}
        onGlobalFilterChange={setGlobalFilter}
        selectedCount={selectedJobIds.length}
        failedCount={stats.failed}
        onRetrySelected={
          onRetrySelected && selectedJobIds.length > 0
            ? () => onRetrySelected(selectedJobIds)
            : undefined
        }
        onPushSelected={
          onPushSelected && selectedJobIds.length > 0
            ? () => onPushSelected(selectedJobIds)
            : undefined
        }
        onExportSelected={selectedJobIds.length > 0 ? exportSelected : undefined}
        onSelectAllFailed={stats.failed > 0 ? selectAllFailed : undefined}
        onClearSelection={clearSelection}
        onDownloadAll={downloadCsv}
        totalRows={stats.total}
        completedCount={stats.complete}
      />

      <div ref={parentRef} className="overflow-auto max-h-[600px]">
        <table className="w-full border-collapse">
          <thead className="sticky top-0 z-10">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <SpreadsheetHeaderCell key={header.id} header={header} />
                ))}
              </tr>
            ))}
          </thead>
          <tbody>
            {virtualizer.getVirtualItems().length === 0 ? (
              <tr>
                <td
                  colSpan={table.getHeaderGroups()[0]?.headers.length || 1}
                  className="text-center py-12 text-sm text-clay-200"
                >
                  No matching rows
                </td>
              </tr>
            ) : (
              virtualizer.getVirtualItems().map((virtualRow) => {
                const row = rows[virtualRow.index];
                if (!row) return null;
                return (
                  <SpreadsheetRowComponent
                    key={row.id}
                    row={row}
                    onRowClick={onRowClick}
                  />
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <SpreadsheetFooter
        total={stats.total}
        complete={stats.complete}
        failed={stats.failed}
        running={stats.running}
      />
    </div>
  );
}
