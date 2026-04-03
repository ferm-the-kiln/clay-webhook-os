"use client";

import { useRef, useState, useCallback } from "react";
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
import { Plus, ChevronDown, ChevronRight } from "lucide-react";
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
import { ColumnContextMenu } from "./column-context-menu";

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
  onRenameColumn?: (columnId: string, newName: string) => Promise<void>;
  onEditColumnConfig?: (column: TableColumn) => void;
  onDuplicateColumn?: (columnId: string) => Promise<void>;
  onHideColumn?: (columnId: string) => Promise<void>;
  onRunColumn?: (columnId: string) => void;
  onRerunColumnFailed?: (columnId: string) => void;
  // Inline editing
  onUpdateCell?: (rowId: string, columnId: string, value: unknown) => Promise<void>;
  // Row expansion
  expandedRowId?: string | null;
  onToggleExpandRow?: (rowId: string) => void;
  // Clipboard paste
  onPasteRows?: (rows: Record<string, unknown>[]) => Promise<void>;
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
  onUpdateCell,
  expandedRowId,
  onToggleExpandRow,
  onPasteRows,
  onRenameColumn,
  onEditColumnConfig,
  onDuplicateColumn,
  onHideColumn,
  onRunColumn,
  onRerunColumnFailed,
}: TableGridProps) {
  const tableContainerRef = useRef<HTMLDivElement>(null);

  // Inline editing state
  const [editingCell, setEditingCell] = useState<{ rowId: string; columnId: string } | null>(null);
  const [editValue, setEditValue] = useState("");

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
    estimateSize: (index) => {
      const row = tableRows[index];
      return row && expandedRowId === row.id ? 200 : 36;
    },
    overscan: 20,
  });

  const visibleColumns = table.columns.filter((c) => !c.hidden);

  // Start inline editing on double-click
  const handleDoubleClick = useCallback(
    (rowId: string, col: TableColumn) => {
      if (col.column_type !== "input" && col.column_type !== "static") return;
      const row = rows.find((r) => r._row_id === rowId);
      const val = row ? getCellValue(row, col.id) : "";
      setEditingCell({ rowId, columnId: col.id });
      setEditValue(val !== null && val !== undefined ? String(val) : "");
    },
    [rows],
  );

  // Commit inline edit
  const commitEdit = useCallback(async () => {
    if (!editingCell || !onUpdateCell) return;
    await onUpdateCell(editingCell.rowId, editingCell.columnId, editValue);
    setEditingCell(null);
  }, [editingCell, editValue, onUpdateCell]);

  // Handle clipboard paste
  const handlePaste = useCallback(
    async (e: React.ClipboardEvent) => {
      if (!selectedCell || !onUpdateCell) return;
      const text = e.clipboardData.getData("text/plain");
      if (!text) return;

      // Parse TSV
      const lines = text.split("\n").filter((l) => l.trim());
      if (lines.length === 0) return;

      e.preventDefault();

      // Find the column index of the selected cell
      const selectedColIdx = visibleColumns.findIndex((c) => c.id === selectedCell.columnId);
      if (selectedColIdx < 0) return;

      // Find the row index
      const selectedRowIdx = rows.findIndex((r) => r._row_id === selectedCell.rowId);
      if (selectedRowIdx < 0) return;

      // Apply paste data
      for (let lineIdx = 0; lineIdx < lines.length; lineIdx++) {
        const rowIdx = selectedRowIdx + lineIdx;
        if (rowIdx >= rows.length) break;
        const row = rows[rowIdx];
        const cells = lines[lineIdx].split("\t");

        for (let cellIdx = 0; cellIdx < cells.length; cellIdx++) {
          const colIdx = selectedColIdx + cellIdx;
          if (colIdx >= visibleColumns.length) break;
          const col = visibleColumns[colIdx];
          if (col.column_type === "input" || col.column_type === "static") {
            await onUpdateCell(row._row_id, col.id, cells[cellIdx]);
          }
        }
      }
    },
    [selectedCell, rows, visibleColumns, onUpdateCell],
  );

  return (
    <div
      ref={tableContainerRef}
      className="flex-1 overflow-auto"
      onPaste={handlePaste}
      tabIndex={0}
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
                      <ColumnContextMenu
                        column={tableCol}
                        onEditConfig={() => onEditColumnConfig?.(tableCol)}
                        onRename={() => {
                          // Trigger inline rename via the header component
                          const nameEl = document.querySelector(
                            `[data-col-rename="${tableCol.id}"]`,
                          ) as HTMLElement | null;
                          nameEl?.dispatchEvent(new MouseEvent("dblclick", { bubbles: true }));
                        }}
                        onDuplicate={() => onDuplicateColumn?.(tableCol.id)}
                        onInsertLeft={() => onAddColumn()}
                        onInsertRight={() => onAddColumn()}
                        onHide={() => onHideColumn?.(tableCol.id)}
                        onRunColumn={() => onRunColumn?.(tableCol.id)}
                        onRerunFailed={() => onRerunColumnFailed?.(tableCol.id)}
                        onDelete={() => onDeleteColumn(tableCol.id)}
                      >
                        <div>
                          <TableColumnHeader
                            column={tableCol}
                            progress={columnProgress[tableCol.id]}
                            onDelete={() => onDeleteColumn(tableCol.id)}
                            onEditConfig={onEditColumnConfig ? () => onEditColumnConfig(tableCol) : undefined}
                            onRename={onRenameColumn ? (name) => onRenameColumn(tableCol.id, name) : undefined}
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
                        </div>
                      </ColumnContextMenu>
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
                  className={`flex items-center justify-center w-6 h-6 rounded hover:bg-zinc-700 text-zinc-500 hover:text-kiln-teal transition-colors ${
                    rows.length > 0 &&
                    table.columns.every(
                      (c) => c.column_type === "input" || c.column_type === "static",
                    )
                      ? "animate-pulse ring-1 ring-kiln-teal/30 text-kiln-teal"
                      : ""
                  }`}
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
            const isExpanded = expandedRowId === rowId;

            return (
              <tr
                key={rowId}
                className={`border-b border-zinc-800/50 hover:bg-zinc-800/30 ${
                  rowSelection[rowId] ? "bg-kiln-teal/5" : ""
                }`}
              >
                {row.getVisibleCells().map((cell) => {
                  const tableCol = visibleColumns.find(
                    (c) => c.id === cell.column.id,
                  );
                  const isSystem =
                    cell.column.id === "_select" ||
                    cell.column.id === "_row_num";
                  const isRowNum = cell.column.id === "_row_num";
                  const isSelected =
                    selectedCell?.rowId === rowId &&
                    selectedCell?.columnId === cell.column.id;
                  const isEditing =
                    editingCell?.rowId === rowId &&
                    editingCell?.columnId === cell.column.id;
                  const isEditable =
                    tableCol &&
                    (tableCol.column_type === "input" || tableCol.column_type === "static");

                  return (
                    <td
                      key={cell.id}
                      className={`px-3 py-1.5 ${
                        isSelected ? "ring-1 ring-kiln-teal ring-inset" : ""
                      } ${isSystem ? "bg-zinc-950" : ""} ${
                        isEditable ? "cursor-text" : ""
                      }`}
                      style={{
                        width: cell.column.getSize(),
                        maxWidth: cell.column.getSize(),
                        position:
                          isSystem || tableCol?.frozen ? "sticky" : undefined,
                        left:
                          isSystem || tableCol?.frozen ? 0 : undefined,
                        zIndex: isSystem || tableCol?.frozen ? 5 : undefined,
                        height: 36,
                      }}
                      onClick={() => {
                        if (isRowNum && onToggleExpandRow) {
                          onToggleExpandRow(rowId);
                        } else if (!isSystem && tableCol) {
                          onCellClick({ rowId, columnId: tableCol.id });
                        }
                      }}
                      onDoubleClick={() => {
                        if (tableCol && isEditable) {
                          handleDoubleClick(rowId, tableCol);
                        }
                      }}
                    >
                      {/* Row number with expand toggle */}
                      {isRowNum ? (
                        <span className="flex items-center gap-0.5 text-zinc-500 text-xs cursor-pointer hover:text-zinc-300">
                          {onToggleExpandRow && (
                            isExpanded
                              ? <ChevronDown className="w-3 h-3" />
                              : <ChevronRight className="w-3 h-3" />
                          )}
                          {virtualRow.index + 1}
                        </span>
                      ) : isEditing ? (
                        /* Inline editing input */
                        <input
                          value={editValue}
                          onChange={(e) => setEditValue(e.target.value)}
                          onBlur={commitEdit}
                          onKeyDown={(e) => {
                            if (e.key === "Enter") commitEdit();
                            if (e.key === "Escape") setEditingCell(null);
                            if (e.key === "Tab") {
                              e.preventDefault();
                              commitEdit();
                            }
                          }}
                          autoFocus
                          className="w-full bg-transparent text-white text-xs outline-none border-b border-kiln-teal"
                        />
                      ) : tableCol &&
                        tableCol.column_type !== "input" &&
                        tableCol.column_type !== "static" ? (
                        <EnrichmentCell
                          value={getCellValue(row.original, tableCol.id)}
                          status={getCellStatus(row.original, tableCol.id)}
                        />
                      ) : (
                        <span className="truncate text-xs">
                          {flexRender(
                            cell.column.columnDef.cell,
                            cell.getContext(),
                          )}
                        </span>
                      )}
                    </td>
                  );
                })}
                {/* Empty cell for add-column column */}
                <td className="w-10" style={{ height: 36 }} />
              </tr>
            );
          })}

          {/* Expanded row detail */}
          {expandedRowId && (() => {
            const expandedRow = rows.find((r) => r._row_id === expandedRowId);
            if (!expandedRow) return null;
            return (
              <tr className="bg-zinc-900/50 border-b border-zinc-700">
                <td colSpan={columns.length + 1} className="p-4">
                  <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-3">
                    {visibleColumns.map((col) => {
                      const val = getCellValue(expandedRow, col.id);
                      const status = getCellStatus(expandedRow, col.id);
                      return (
                        <div key={col.id} className="min-w-0">
                          <div className="text-[10px] text-zinc-500 mb-0.5 truncate">
                            {col.name}
                          </div>
                          <div className="text-xs text-zinc-300 truncate">
                            {val !== null && val !== undefined
                              ? typeof val === "object"
                                ? JSON.stringify(val).slice(0, 100)
                                : String(val)
                              : <span className="text-zinc-600">—</span>}
                          </div>
                        </div>
                      );
                    })}
                  </div>
                </td>
              </tr>
            );
          })()}

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
