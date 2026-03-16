"use client";

import { useMemo, useState } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  type SortingState,
  type RowSelectionState,
  type ColumnSizingState,
  type VisibilityState,
} from "@tanstack/react-table";
import type { DatasetColumn, DatasetRow } from "@/lib/types";
import {
  buildDatasetColumns,
  buildDatasetRows,
  type DatasetSpreadsheetRow,
} from "./dataset-column-utils";

export function useDatasetSpreadsheet(
  columns: DatasetColumn[],
  rows: DatasetRow[]
) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({});
  const [globalFilter, setGlobalFilter] = useState("");
  const [columnVisibility, setColumnVisibility] = useState<VisibilityState>({});

  const tableCols = useMemo(
    () => buildDatasetColumns(columns),
    [columns]
  );

  const data = useMemo(() => buildDatasetRows(rows), [rows]);

  const table = useReactTable({
    data,
    columns: tableCols,
    state: {
      sorting,
      rowSelection,
      columnSizing,
      globalFilter,
      columnVisibility,
    },
    onSortingChange: setSorting,
    onRowSelectionChange: setRowSelection,
    onColumnSizingChange: setColumnSizing,
    onGlobalFilterChange: setGlobalFilter,
    onColumnVisibilityChange: setColumnVisibility,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    enableRowSelection: true,
    enableColumnResizing: true,
    columnResizeMode: "onChange",
    getRowId: (row) => row._row_id,
  });

  const selectedRowIds = useMemo(() => {
    return Object.keys(rowSelection).filter((id) => rowSelection[id]);
  }, [rowSelection]);

  const clearSelection = () => setRowSelection({});

  return {
    table,
    selectedRowIds,
    globalFilter,
    setGlobalFilter,
    columnVisibility,
    setColumnVisibility,
    clearSelection,
  };
}
