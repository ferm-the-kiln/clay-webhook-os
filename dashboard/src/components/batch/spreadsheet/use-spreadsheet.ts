"use client";

import { useMemo, useState, useRef, useEffect } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  type SortingState,
  type ColumnFiltersState,
  type RowSelectionState,
  type ColumnSizingState,
} from "@tanstack/react-table";
import type { Job } from "@/lib/types";
import { buildColumns, buildRows, type SpreadsheetRow } from "./column-utils";

export function useSpreadsheet(
  jobs: Job[],
  originalRows: Record<string, string>[],
  csvHeaders: string[]
) {
  const [sorting, setSorting] = useState<SortingState>([]);
  const [columnFilters, setColumnFilters] = useState<ColumnFiltersState>([]);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({});
  const [globalFilter, setGlobalFilter] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");

  // Persist selection across data refreshes using a ref keyed by job ID
  const selectionRef = useRef<Set<string>>(new Set());

  // Sync ref -> state when jobs change (reconcile: keep IDs that still exist)
  useEffect(() => {
    const jobIds = new Set(jobs.map((j) => j.id));
    // Remove stale IDs from ref
    for (const id of selectionRef.current) {
      if (!jobIds.has(id)) selectionRef.current.delete(id);
    }
    // Build RowSelectionState from ref
    const newSelection: RowSelectionState = {};
    for (const id of selectionRef.current) {
      newSelection[id] = true;
    }
    setRowSelection(newSelection);
  }, [jobs]);

  // Keep ref in sync when user changes selection
  const handleRowSelectionChange = (updater: RowSelectionState | ((prev: RowSelectionState) => RowSelectionState)) => {
    setRowSelection((prev) => {
      const next = typeof updater === "function" ? updater(prev) : updater;
      selectionRef.current = new Set(Object.keys(next).filter((id) => next[id]));
      return next;
    });
  };

  const columns = useMemo(
    () => buildColumns(csvHeaders, jobs),
    // Re-compute columns when result shape changes (check first completed job keys)
    [csvHeaders, jobs.filter((j) => j.status === "completed").length > 0]
  );

  const data = useMemo(() => buildRows(jobs, originalRows), [jobs, originalRows]);

  // Pre-filter by status
  const filteredData = useMemo(() => {
    if (statusFilter === "all") return data;
    return data.filter((row) => row._job.status === statusFilter);
  }, [data, statusFilter]);

  const table = useReactTable({
    data: filteredData,
    columns,
    state: {
      sorting,
      columnFilters,
      rowSelection,
      columnSizing,
      globalFilter,
    },
    onSortingChange: setSorting,
    onColumnFiltersChange: setColumnFilters,
    onRowSelectionChange: handleRowSelectionChange,
    onColumnSizingChange: setColumnSizing,
    onGlobalFilterChange: setGlobalFilter,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    enableRowSelection: true,
    enableColumnResizing: true,
    columnResizeMode: "onChange",
    getRowId: (row) => row._job.id,
  });

  // Stats
  const stats = useMemo(() => {
    const total = jobs.length;
    const complete = jobs.filter((j) => j.status === "completed").length;
    const failed = jobs.filter((j) => j.status === "failed" || j.status === "dead_letter").length;
    const running = jobs.filter((j) => j.status === "processing" || j.status === "queued").length;
    return { total, complete, failed, running };
  }, [jobs]);

  // Selected job IDs
  const selectedJobIds = useMemo(() => {
    return Object.keys(rowSelection).filter((id) => rowSelection[id]);
  }, [rowSelection]);

  const selectAllFailed = () => {
    const newSelection: RowSelectionState = {};
    for (const row of filteredData) {
      if (row._job.status === "failed" || row._job.status === "dead_letter") {
        newSelection[row._job.id] = true;
      }
    }
    selectionRef.current = new Set(Object.keys(newSelection));
    setRowSelection(newSelection);
  };

  const clearSelection = () => {
    selectionRef.current.clear();
    setRowSelection({});
  };

  return {
    table,
    stats,
    selectedJobIds,
    statusFilter,
    setStatusFilter,
    globalFilter,
    setGlobalFilter,
    selectAllFailed,
    clearSelection,
  };
}
