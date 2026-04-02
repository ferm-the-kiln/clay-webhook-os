"use client";

import { useRef, useMemo } from "react";
import {
  useReactTable,
  getCoreRowModel,
  getSortedRowModel,
  getFilteredRowModel,
  flexRender,
  type ColumnDef,
  type SortingState,
  type RowSelectionState,
  type ColumnSizingState,
} from "@tanstack/react-table";
import { useVirtualizer } from "@tanstack/react-virtual";
import {
  Plus,
  Search,
  Brain,
  Calculator,
  Filter,
  Pencil,
  Type,
  MoreVertical,
  Trash2,
  ArrowUp,
  ArrowDown,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import type {
  TableDefinition,
  TableRow,
  TableColumn,
  CellState,
} from "@/lib/types";
import type { ColumnProgress } from "@/hooks/use-table-builder";
import { getCellValue, getCellStatus } from "@/hooks/use-table-builder";
import { EnrichmentCell } from "./enrichment-cell";
import { TableColumnHeader } from "./table-column-header";

// Column type → icon mapping
const COLUMN_TYPE_ICONS: Record<string, typeof Search> = {
  enrichment: Search,
  ai: Brain,
  formula: Calculator,
  gate: Filter,
  input: Pencil,
  static: Type,
};

// Column type → color mapping
const COLUMN_TYPE_COLORS: Record<string, string> = {
  enrichment: "border-l-blue-500",
  ai: "border-l-purple-500",
  formula: "border-l-teal-500",
  gate: "border-l-amber-500",
  input: "border-l-zinc-600",
  static: "border-l-zinc-600",
};

interface TableGridProps {
  table: TableDefinition;
  rows: TableRow[];
  columns: ColumnDef<TableRow>[];
  sorting: SortingState;
  onSortingChange: (s: SortingState) => void;
  rowSelection: RowSelectionState;
  onRowSelectionChange: (
    s: RowSelectionState | ((prev: RowSelectionState) => RowSelectionState),
  ) => void;
  columnSizing: ColumnSizingState;
  onColumnSizingChange: (s: ColumnSizingState) => void;
  globalFilter: string;
  columnProgress: Record<string, ColumnProgress>;
  cellStates: Record<string, Record<string, CellState>>;
  selectedCell: { rowId: string; columnId: string } | null;
  onCellClick: (cell: { rowId: string; columnId: string } | null) => void;
  onAddColumn: () => void;
  onDeleteColumn: (columnId: string) => Promise<void>;
}

export function TableGrid({
  table,
  rows,
  columns,
  sorting,
  onSortingChange,
  rowSelection,
  onRowSelectionChange,
  columnSizing,
  onColumnSizingChange,
  globalFilter,
  columnProgress,
  cellStates,
  selectedCell,
  onCellClick,
  onAddColumn,
  onDeleteColumn,
}: TableGridProps) {
  const tableContainerRef = useRef<HTMLDivElement>(null);

  const reactTable = useReactTable({
    data: rows,
    columns,
    state: { sorting, rowSelection, columnSizing, globalFilter },
    onSortingChange: onSortingChange as never,
    onRowSelectionChange: onRowSelectionChange as never,
    onColumnSizingChange: onColumnSizingChange as never,
    getCoreRowModel: getCoreRowModel(),
    getSortedRowModel: getSortedRowModel(),
    getFilteredRowModel: getFilteredRowModel(),
    getRowId: (row) => row._row_id,
    enableColumnResizing: true,
    columnResizeMode: "onChange",
    enableRowSelection: true,
  });

  const { rows: tableRows } = reactTable.getRowModel();

  const rowVirtualizer = useVirtualizer({
    count: tableRows.length,
    getScrollElement: () => tableContainerRef.current,
    estimateSize: () => 36,
    overscan: 20,
  });

  const visibleColumns = table.columns.filter((c) => !c.hidden);

  return (
    <div
      ref={tableContainerRef}
      className="flex-1 overflow-auto"
    >
      <table className="w-full border-collapse text-sm">
        {/* Header */}
        <thead className="sticky top-0 z-20 bg-zinc-900">
          {reactTable.getHeaderGroups().map((headerGroup) => (
            <tr key={headerGroup.id}>
              {headerGroup.headers.map((header) => {
                const tableCol = visibleColumns.find(
                  (c) => c.id === header.id,
                );
                const isSystem = header.id === "_select" || header.id === "_row_num";

                return (
                  <th
                    key={header.id}
                    className={`relative px-3 py-2 text-left text-xs font-medium text-zinc-400 border-b border-zinc-800 select-none ${
                      tableCol
                        ? `border-l-2 ${COLUMN_TYPE_COLORS[tableCol.column_type] || "border-l-zinc-600"}`
                        : ""
                    } ${isSystem ? "bg-zinc-900" : "bg-zinc-900 hover:bg-zinc-800/50"}`}
                    style={{
                      width: header.getSize(),
                      minWidth: isSystem ? header.getSize() : 100,
                      position: isSystem || tableCol?.frozen ? "sticky" : undefined,
                      left: isSystem || tableCol?.frozen ? 0 : undefined,
                      zIndex: isSystem || tableCol?.frozen ? 10 : undefined,
                    }}
                  >
                    {tableCol ? (
                      <TableColumnHeader
                        column={tableCol}
                        progress={columnProgress[tableCol.id]}
                        onDelete={() => onDeleteColumn(tableCol.id)}
                        onSort={() => {
                          onSortingChange(
                            sorting[0]?.id === tableCol.id
                              ? [{ id: tableCol.id, desc: !sorting[0].desc }]
                              : [{ id: tableCol.id, desc: false }],
                          );
                        }}
                        sortDir={
                          sorting[0]?.id === tableCol.id
                            ? sorting[0].desc
                              ? "desc"
                              : "asc"
                            : null
                        }
                      />
                    ) : (
                      flexRender(
                        header.column.columnDef.header,
                        header.getContext(),
                      )
                    )}

                    {/* Column resize handle */}
                    {!isSystem && (
                      <div
                        onMouseDown={header.getResizeHandler()}
                        onTouchStart={header.getResizeHandler()}
                        className="absolute right-0 top-0 bottom-0 w-1 cursor-col-resize hover:bg-kiln-teal/50 active:bg-kiln-teal"
                      />
                    )}
                  </th>
                );
              })}
              {/* Add column button */}
              <th className="px-2 py-2 border-b border-zinc-800 bg-zinc-900 w-10">
                <button
                  onClick={() => onAddColumn()}
                  className="flex items-center justify-center w-6 h-6 rounded hover:bg-zinc-700 text-zinc-500 hover:text-kiln-teal transition-colors"
                  title="Add column"
                >
                  <Plus className="w-4 h-4" />
                </button>
              </th>
            </tr>
          ))}
        </thead>

        {/* Body */}
        <tbody>
          {/* Spacer for virtual scroll */}
          {rowVirtualizer.getVirtualItems().length > 0 && (
            <tr>
              <td
                style={{ height: rowVirtualizer.getVirtualItems()[0]?.start ?? 0 }}
                colSpan={columns.length + 1}
              />
            </tr>
          )}

          {rowVirtualizer.getVirtualItems().map((virtualRow) => {
            const row = tableRows[virtualRow.index];
            if (!row) return null;
            const rowId = row.id;

            return (
              <tr
                key={rowId}
                className={`border-b border-zinc-800/50 hover:bg-zinc-800/30 ${
                  rowSelection[rowId] ? "bg-kiln-teal/5" : ""
                }`}
                style={{ height: virtualRow.size }}
              >
                {row.getVisibleCells().map((cell) => {
                  const tableCol = visibleColumns.find(
                    (c) => c.id === cell.column.id,
                  );
                  const isSystem =
                    cell.column.id === "_select" ||
                    cell.column.id === "_row_num";
                  const isSelected =
                    selectedCell?.rowId === rowId &&
                    selectedCell?.columnId === cell.column.id;

                  return (
                    <td
                      key={cell.id}
                      className={`px-3 py-1.5 truncate ${
                        isSelected ? "ring-1 ring-kiln-teal ring-inset" : ""
                      } ${isSystem ? "bg-zinc-950" : ""}`}
                      style={{
                        width: cell.column.getSize(),
                        maxWidth: cell.column.getSize(),
                        position:
                          isSystem || tableCol?.frozen ? "sticky" : undefined,
                        left:
                          isSystem || tableCol?.frozen ? 0 : undefined,
                        zIndex: isSystem || tableCol?.frozen ? 5 : undefined,
                      }}
                      onClick={() => {
                        if (!isSystem && tableCol) {
                          onCellClick({ rowId, columnId: tableCol.id });
                        }
                      }}
                    >
                      {tableCol &&
                      tableCol.column_type !== "input" &&
                      tableCol.column_type !== "static" ? (
                        <EnrichmentCell
                          value={getCellValue(row.original, tableCol.id)}
                          status={getCellStatus(row.original, tableCol.id)}
                        />
                      ) : (
                        flexRender(
                          cell.column.columnDef.cell,
                          cell.getContext(),
                        )
                      )}
                    </td>
                  );
                })}
                {/* Empty cell for add-column column */}
                <td className="w-10" />
              </tr>
            );
          })}

          {/* Bottom spacer for virtual scroll */}
          {rowVirtualizer.getVirtualItems().length > 0 && (
            <tr>
              <td
                style={{
                  height:
                    rowVirtualizer.getTotalSize() -
                    (rowVirtualizer.getVirtualItems().at(-1)?.end ?? 0),
                }}
                colSpan={columns.length + 1}
              />
            </tr>
          )}
        </tbody>
      </table>

      {/* Empty state */}
      {rows.length === 0 && (
        <div className="flex flex-col items-center justify-center py-20 text-zinc-500">
          <p className="text-sm mb-2">No rows yet</p>
          <p className="text-xs text-zinc-600">
            Import a CSV or add rows to get started
          </p>
        </div>
      )}
    </div>
  );
}
