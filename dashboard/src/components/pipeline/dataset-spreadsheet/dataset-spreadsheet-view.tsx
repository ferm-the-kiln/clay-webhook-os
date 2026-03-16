"use client";

import { useRef, useCallback } from "react";
import { useVirtualizer } from "@tanstack/react-virtual";
import Papa from "papaparse";
import type { DatasetColumn, DatasetRow } from "@/lib/types";
import { useDatasetSpreadsheet } from "./use-dataset-spreadsheet";
import { DatasetSpreadsheetToolbar } from "./dataset-spreadsheet-toolbar";
import { DatasetHeaderCell } from "./dataset-header-cell";
import { DatasetSpreadsheetRowComponent } from "./dataset-spreadsheet-row";

export function DatasetSpreadsheetView({
  columns,
  rows,
  onExport,
  className,
}: {
  columns: DatasetColumn[];
  rows: DatasetRow[];
  onExport?: () => void;
  className?: string;
}) {
  const {
    table,
    selectedRowIds,
    globalFilter,
    setGlobalFilter,
    columnVisibility,
    setColumnVisibility,
    clearSelection,
  } = useDatasetSpreadsheet(columns, rows);

  const parentRef = useRef<HTMLDivElement>(null);
  const { rows: tableRows } = table.getRowModel();

  const virtualizer = useVirtualizer({
    count: tableRows.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 40,
    overscan: 15,
  });

  const downloadCsv = useCallback(() => {
    const csvRows = rows.map((row) => {
      const out: Record<string, string> = {};
      for (const col of columns) {
        if (col.name === "_row_id") continue;
        const val = row[col.name];
        out[col.name] = val === null || val === undefined
          ? ""
          : typeof val === "string"
            ? val
            : JSON.stringify(val);
      }
      return out;
    });
    const csv = Papa.unparse(csvRows);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `dataset-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [rows, columns]);

  const exportSelected = useCallback(() => {
    const selectedSet = new Set(selectedRowIds);
    const selectedRows = rows.filter((r) => selectedSet.has(r._row_id));
    const csvRows = selectedRows.map((row) => {
      const out: Record<string, string> = {};
      for (const col of columns) {
        if (col.name === "_row_id") continue;
        const val = row[col.name];
        out[col.name] = val === null || val === undefined
          ? ""
          : typeof val === "string"
            ? val
            : JSON.stringify(val);
      }
      return out;
    });
    const csv = Papa.unparse(csvRows);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `dataset-selected-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  }, [rows, columns, selectedRowIds]);

  const visibleCols = columns.filter((c) => c.name !== "_row_id");

  return (
    <div className={`rounded-xl border border-clay-500 overflow-hidden ${className ?? ""}`}>
      <DatasetSpreadsheetToolbar
        globalFilter={globalFilter}
        onGlobalFilterChange={setGlobalFilter}
        selectedCount={selectedRowIds.length}
        onClearSelection={clearSelection}
        onExportAll={onExport ?? downloadCsv}
        onExportSelected={selectedRowIds.length > 0 ? exportSelected : undefined}
        totalRows={rows.length}
        columns={visibleCols}
        columnVisibility={columnVisibility}
        onColumnVisibilityChange={setColumnVisibility}
      />

      <div ref={parentRef} className="overflow-auto max-h-[600px]">
        <table className="w-full border-collapse">
          <thead className="sticky top-0 z-10">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {headerGroup.headers.map((header) => (
                  <DatasetHeaderCell key={header.id} header={header} />
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
                const row = tableRows[virtualRow.index];
                if (!row) return null;
                return (
                  <DatasetSpreadsheetRowComponent
                    key={row.id}
                    row={row}
                  />
                );
              })
            )}
          </tbody>
        </table>
      </div>

      <div className="flex items-center gap-3 px-4 py-1.5 border-t border-clay-500 bg-clay-800/50 text-xs text-clay-200">
        <span>{rows.length} rows</span>
        <span className="text-clay-300">&middot;</span>
        <span>{visibleCols.length} cols</span>
        {selectedRowIds.length > 0 && (
          <>
            <span className="text-clay-300">&middot;</span>
            <span className="text-kiln-teal">{selectedRowIds.length} selected</span>
          </>
        )}
      </div>
    </div>
  );
}
