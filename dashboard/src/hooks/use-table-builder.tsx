"use client";

import { useState, useEffect, useCallback, useMemo, useRef } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  type SortingState,
  type ColumnDef,
  type RowSelectionState,
  type ColumnSizingState,
} from "@tanstack/react-table";
import type {
  TableDefinition,
  TableColumn,
  TableRow,
  CellState,
  TableExecutionEvent,
} from "@/lib/types";
import {
  fetchTable,
  fetchTableRows,
  updateTable,
  addTableColumn,
  updateTableColumn,
  removeTableColumn,
  reorderTableColumns,
  importTableRows,
  importTableCsv,
  addTableRow,
  deleteTableRows,
  streamTableExecution,
  updateTableCells,
} from "@/lib/api";

export interface ColumnProgress {
  done: number;
  total: number;
  errors: number;
}

export interface ExecutionSummaryData {
  totalDurationMs: number;
  cellsDone: number;
  cellsErrored: number;
  halted: boolean;
}

export interface UseTableBuilderReturn {
  // Table definition
  table: TableDefinition | null;
  loading: boolean;
  error: string | null;

  // Rows
  rows: TableRow[];
  totalRows: number;

  // Column CRUD
  addColumn: (body: Record<string, unknown>) => Promise<string | undefined>;
  editColumn: (columnId: string, body: Record<string, unknown>) => Promise<void>;
  deleteColumn: (columnId: string) => Promise<void>;
  reorderCols: (columnIds: string[]) => Promise<void>;

  // Row CRUD
  importCsv: (file: File, columnMapping?: Record<string, string>) => Promise<void>;
  importRows: (rows: Record<string, unknown>[]) => Promise<void>;
  addRow: (data: Record<string, unknown>) => Promise<void>;
  removeRows: (rowIds: string[]) => Promise<void>;
  updateCell: (rowId: string, columnId: string, value: unknown) => Promise<void>;
  duplicateRow: (rowId: string) => Promise<void>;

  // Row expansion
  expandedRowId: string | null;
  setExpandedRowId: (id: string | null) => void;

  // Table meta
  rename: (name: string) => Promise<void>;

  // Execution
  executing: boolean;
  columnProgress: Record<string, ColumnProgress>;
  cellStates: Record<string, Record<string, CellState>>;
  executeTable: (options?: { limit?: number; columnIds?: string[]; rowIds?: string[]; model?: string }) => void;
  stopExecution: () => void;

  // Detail panel
  selectedCell: { rowId: string; columnId: string } | null;
  setSelectedCell: (cell: { rowId: string; columnId: string } | null) => void;

  // TanStack table
  tanstackColumns: ColumnDef<TableRow>[];
  sorting: SortingState;
  setSorting: (s: SortingState) => void;
  rowSelection: RowSelectionState;
  setRowSelection: (s: RowSelectionState | ((prev: RowSelectionState) => RowSelectionState)) => void;
  columnSizing: ColumnSizingState;
  setColumnSizing: (s: ColumnSizingState) => void;
  globalFilter: string;
  setGlobalFilter: (s: string) => void;

  // Refresh
  refresh: () => Promise<void>;

  // Execution summary
  executionSummary: ExecutionSummaryData | null;
  dismissSummary: () => void;
}

/** Get the display value for a cell from raw row data */
export function getCellValue(row: TableRow, columnId: string): unknown {
  return row[`${columnId}__value`];
}

/** Get the status for a cell from raw row data */
export function getCellStatus(row: TableRow, columnId: string): CellState {
  return (row[`${columnId}__status`] as CellState) || "empty";
}

/** Get the error for a cell from raw row data */
export function getCellError(row: TableRow, columnId: string): string | undefined {
  return row[`${columnId}__error`] as string | undefined;
}

export function useTableBuilder(tableId: string): UseTableBuilderReturn {
  const [table, setTable] = useState<TableDefinition | null>(null);
  const [rows, setRows] = useState<TableRow[]>([]);
  const [totalRows, setTotalRows] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Execution state
  const [executing, setExecuting] = useState(false);
  const [columnProgress, setColumnProgress] = useState<Record<string, ColumnProgress>>({});
  const [cellStates, setCellStates] = useState<Record<string, Record<string, CellState>>>({});
  const [executionSummary, setExecutionSummary] = useState<ExecutionSummaryData | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  // Detail panel
  const [selectedCell, setSelectedCell] = useState<{ rowId: string; columnId: string } | null>(null);
  const [expandedRowId, setExpandedRowId] = useState<string | null>(null);

  // TanStack state
  const [sorting, setSorting] = useState<SortingState>([]);
  const [rowSelection, setRowSelection] = useState<RowSelectionState>({});
  const [columnSizing, setColumnSizing] = useState<ColumnSizingState>({});
  const [globalFilter, setGlobalFilter] = useState("");

  // Load table + rows
  const refresh = useCallback(async () => {
    try {
      setLoading(true);
      const [tableData, rowsData] = await Promise.all([
        fetchTable(tableId),
        fetchTableRows(tableId, 0, 500),
      ]);
      setTable(tableData);
      setRows(rowsData.rows as TableRow[]);
      setTotalRows(rowsData.total);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load table");
    } finally {
      setLoading(false);
    }
  }, [tableId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  // Column CRUD
  const addColumn = useCallback(
    async (body: Record<string, unknown>): Promise<string | undefined> => {
      const beforeIds = new Set(table?.columns.map((c) => c.id) || []);
      const updated = await addTableColumn(tableId, body);
      setTable(updated);
      // Find the newly added column ID
      const newCol = updated.columns.find((c) => !beforeIds.has(c.id));
      return newCol?.id;
    },
    [tableId, table?.columns],
  );

  const editColumn = useCallback(
    async (columnId: string, body: Record<string, unknown>) => {
      const updated = await updateTableColumn(tableId, columnId, body);
      setTable(updated);
    },
    [tableId],
  );

  const deleteColumn = useCallback(
    async (columnId: string) => {
      const updated = await removeTableColumn(tableId, columnId);
      setTable(updated);
      await refresh();
    },
    [tableId, refresh],
  );

  const reorderCols = useCallback(
    async (columnIds: string[]) => {
      const updated = await reorderTableColumns(tableId, columnIds);
      setTable(updated);
    },
    [tableId],
  );

  // Row CRUD
  const importCsv = useCallback(
    async (file: File, columnMapping?: Record<string, string>) => {
      await importTableCsv(tableId, file, columnMapping);
      await refresh();
    },
    [tableId, refresh],
  );

  const importRowsFn = useCallback(
    async (newRows: Record<string, unknown>[]) => {
      await importTableRows(tableId, newRows);
      await refresh();
    },
    [tableId, refresh],
  );

  const addRowFn = useCallback(
    async (data: Record<string, unknown>) => {
      await addTableRow(tableId, data);
      await refresh();
    },
    [tableId, refresh],
  );

  const removeRows = useCallback(
    async (rowIds: string[]) => {
      await deleteTableRows(tableId, rowIds);
      await refresh();
    },
    [tableId, refresh],
  );

  // Update a single cell value
  const updateCell = useCallback(
    async (rowId: string, columnId: string, value: unknown) => {
      await updateTableCells(tableId, {
        [rowId]: {
          [`${columnId}__value`]: value,
          [`${columnId}__status`]: "done",
        },
      });
      setRows((prev) =>
        prev.map((r) =>
          r._row_id === rowId
            ? { ...r, [`${columnId}__value`]: value, [`${columnId}__status`]: "done" }
            : r,
        ),
      );
    },
    [tableId],
  );

  // Duplicate a row (copies input values, clears enrichment)
  const duplicateRow = useCallback(
    async (rowId: string) => {
      const row = rows.find((r) => r._row_id === rowId);
      if (!row || !table) return;
      const inputData: Record<string, unknown> = {};
      for (const col of table.columns) {
        if (col.column_type === "input" || col.column_type === "static") {
          const val = row[`${col.id}__value`];
          if (val !== undefined) inputData[col.name] = val;
        }
      }
      await addTableRow(tableId, inputData);
      await refresh();
    },
    [tableId, rows, table, refresh],
  );

  // Rename
  const rename = useCallback(
    async (name: string) => {
      const updated = await updateTable(tableId, { name });
      setTable(updated);
    },
    [tableId],
  );

  // --- Execution ---

  const handleExecutionEvent = useCallback((event: TableExecutionEvent) => {
    switch (event.type) {
      case "cell_update":
        // Update cell state
        setCellStates((prev) => ({
          ...prev,
          [event.row_id]: {
            ...prev[event.row_id],
            [event.column_id]: event.status,
          },
        }));
        // Update row data in-place for display
        if (event.status === "done" && event.value !== undefined) {
          setRows((prev) =>
            prev.map((r) =>
              r._row_id === event.row_id
                ? {
                    ...r,
                    [`${event.column_id}__value`]: event.value,
                    [`${event.column_id}__status`]: "done",
                  }
                : r,
            ),
          );
        } else if (event.status === "error") {
          setRows((prev) =>
            prev.map((r) =>
              r._row_id === event.row_id
                ? {
                    ...r,
                    [`${event.column_id}__status`]: "error",
                    [`${event.column_id}__error`]: event.error,
                  }
                : r,
            ),
          );
        } else if (event.status === "skipped") {
          setRows((prev) =>
            prev.map((r) =>
              r._row_id === event.row_id
                ? {
                    ...r,
                    [`${event.column_id}__status`]: "skipped",
                    [`${event.column_id}__skip_reason`]: event.skip_reason,
                    [`${event.column_id}__upstream_column_id`]: event.upstream_column_id,
                  }
                : r,
            ),
          );
        }
        break;

      case "column_progress":
        setColumnProgress((prev) => ({
          ...prev,
          [event.column_id]: {
            done: event.done,
            total: event.total,
            errors: event.errors,
          },
        }));
        break;

      case "execute_complete":
        setExecuting(false);
        abortRef.current = null;
        setExecutionSummary({
          totalDurationMs: event.total_duration_ms,
          cellsDone: event.cells_done,
          cellsErrored: event.cells_errored,
          halted: event.halted || false,
        });
        break;
    }
  }, []);

  const executeTable = useCallback(
    (options?: { limit?: number; columnIds?: string[]; rowIds?: string[]; model?: string }) => {
      if (executing) return;
      setExecuting(true);
      setColumnProgress({});
      setExecutionSummary(null);

      const controller = streamTableExecution(
        tableId,
        handleExecutionEvent,
        (err) => {
          setExecuting(false);
          setError(err);
        },
        {
          limit: options?.limit,
          column_ids: options?.columnIds,
          row_ids: options?.rowIds,
          model: options?.model,
        },
      );
      abortRef.current = controller;
    },
    [tableId, executing, handleExecutionEvent],
  );

  const stopExecution = useCallback(() => {
    if (abortRef.current) {
      abortRef.current.abort();
      abortRef.current = null;
      setExecuting(false);
    }
  }, []);

  // Build TanStack columns from table definition
  const tanstackColumns = useMemo<ColumnDef<TableRow>[]>(() => {
    if (!table) return [];

    const cols: ColumnDef<TableRow>[] = [];

    // Checkbox column
    cols.push({
      id: "_select",
      size: 40,
      enableResizing: false,
      header: ({ table: t }) => (
        <input
          type="checkbox"
          checked={t.getIsAllRowsSelected()}
          onChange={t.getToggleAllRowsSelectedHandler()}
          className="rounded border-clay-400"
        />
      ),
      cell: ({ row }) => (
        <input
          type="checkbox"
          checked={row.getIsSelected()}
          onChange={row.getToggleSelectedHandler()}
          className="rounded border-clay-400"
        />
      ),
    });

    // Row number column
    cols.push({
      id: "_row_num",
      size: 50,
      enableResizing: false,
      header: () => <span className="text-clay-300 text-xs">#</span>,
      cell: ({ row }) => (
        <span className="text-clay-300 text-xs">{row.index + 1}</span>
      ),
    });

    // Data columns from table definition
    for (const col of table.columns.filter((c) => !c.hidden)) {
      cols.push({
        id: col.id,
        size: col.width,
        header: () => col.name,
        accessorFn: (row) => row[`${col.id}__value`],
        cell: ({ getValue }) => {
          const val = getValue();
          if (val === undefined || val === null) return <span className="text-clay-300">—</span>;
          if (typeof val === "object") return <span className="text-clay-200 truncate">{JSON.stringify(val).slice(0, 60)}</span>;
          return <span className="truncate">{String(val)}</span>;
        },
      });
    }

    return cols;
  }, [table]);

  return {
    table,
    loading,
    error,
    rows,
    totalRows,
    addColumn,
    editColumn,
    deleteColumn,
    reorderCols,
    importCsv,
    importRows: importRowsFn,
    addRow: addRowFn,
    removeRows,
    updateCell,
    duplicateRow,
    expandedRowId,
    setExpandedRowId,
    rename,
    executing,
    columnProgress,
    cellStates,
    executeTable,
    stopExecution,
    selectedCell,
    setSelectedCell,
    tanstackColumns,
    sorting,
    setSorting,
    rowSelection,
    setRowSelection,
    columnSizing,
    setColumnSizing,
    globalFilter,
    setGlobalFilter,
    refresh,
    executionSummary,
    dismissSummary: () => setExecutionSummary(null),
  };
}
