"use client";

import { use, useState, useCallback } from "react";
import { useTableBuilder } from "@/hooks/use-table-builder";
import { TableToolbar } from "@/components/table-builder/table-toolbar";
import { TableGrid } from "@/components/table-builder/table-grid";
import { ColumnCommandPalette } from "@/components/table-builder/column-command-palette";
import { ColumnConfigPanel } from "@/components/table-builder/column-config-panel";
import { CellDetailPanel } from "@/components/table-builder/cell-detail-panel";
import { Loader2 } from "lucide-react";
import type { ToolDefinition, TableColumn } from "@/lib/types";

export default function TableBuilderPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const tb = useTableBuilder(id);

  // Column palette state
  const [paletteOpen, setPaletteOpen] = useState(false);

  // Column config panel state
  const [configOpen, setConfigOpen] = useState(false);
  const [editingColumn, setEditingColumn] = useState<TableColumn | null>(null);
  const [selectedTool, setSelectedTool] = useState<ToolDefinition | null>(null);
  const [initialType, setInitialType] = useState<string | null>(null);

  // Open command palette from "+" button
  const handleAddColumnClick = useCallback(() => {
    setPaletteOpen(true);
  }, []);

  // Handle palette selections
  const handleSelectEnrichment = useCallback((tool: ToolDefinition) => {
    setSelectedTool(tool);
    setInitialType("enrichment");
    setEditingColumn(null);
    setConfigOpen(true);
  }, []);

  const handleSelectAI = useCallback(() => {
    setSelectedTool(null);
    setInitialType("ai");
    setEditingColumn(null);
    setConfigOpen(true);
  }, []);

  const handleSelectFormula = useCallback(() => {
    setSelectedTool(null);
    setInitialType("formula");
    setEditingColumn(null);
    setConfigOpen(true);
  }, []);

  const handleSelectGate = useCallback(() => {
    setSelectedTool(null);
    setInitialType("gate");
    setEditingColumn(null);
    setConfigOpen(true);
  }, []);

  const handleSelectStatic = useCallback(async () => {
    await tb.addColumn({ name: "New Column", column_type: "static" });
  }, [tb]);

  // Save column config
  const handleSaveColumn = useCallback(
    async (config: Record<string, unknown>) => {
      if (editingColumn) {
        await tb.editColumn(editingColumn.id, config);
      } else {
        await tb.addColumn(config);
      }
    },
    [tb, editingColumn],
  );

  // "Add as column" from cell detail panel
  const handleAddAsColumn = useCallback(
    async (path: string, value: unknown) => {
      if (!tb.selectedCell) return;
      await tb.addColumn({
        name: path.split(".").pop() || path,
        column_type: "formula",
        parent_column_id: tb.selectedCell.columnId,
        extract_path: path,
        formula: `{{${tb.selectedCell.columnId}}}`,
      });
    },
    [tb],
  );

  // Available columns for "/" references (all columns to the left of the target)
  const availableColumns = tb.table?.columns.filter((c) => !c.hidden) || [];

  // Find the selected row
  const selectedRow = tb.selectedCell
    ? tb.rows.find((r) => r._row_id === tb.selectedCell!.rowId) || null
    : null;

  if (tb.loading) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <Loader2 className="w-6 h-6 text-zinc-500 animate-spin" />
      </div>
    );
  }

  if (tb.error || !tb.table) {
    return (
      <div className="min-h-screen bg-zinc-950 flex items-center justify-center">
        <p className="text-red-400">{tb.error || "Table not found"}</p>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-zinc-950 text-white flex flex-col">
      <TableToolbar
        table={tb.table}
        totalRows={tb.totalRows}
        executing={tb.executing}
        onRename={tb.rename}
        onImportCsv={tb.importCsv}
        onAddRow={() => tb.addRow({})}
        onRefresh={tb.refresh}
        selectedCount={Object.keys(tb.rowSelection).length}
        onDeleteSelected={() => {
          const ids = Object.keys(tb.rowSelection);
          if (ids.length > 0) tb.removeRows(ids);
        }}
        onExecute={(options) => tb.executeTable(options)}
        onStop={tb.stopExecution}
      />

      <div className="flex-1 overflow-hidden">
        <TableGrid
          table={tb.table}
          rows={tb.rows}
          columns={tb.tanstackColumns}
          sorting={tb.sorting}
          onSortingChange={tb.setSorting}
          rowSelection={tb.rowSelection}
          onRowSelectionChange={tb.setRowSelection}
          columnSizing={tb.columnSizing}
          onColumnSizingChange={tb.setColumnSizing}
          globalFilter={tb.globalFilter}
          columnProgress={tb.columnProgress}
          cellStates={tb.cellStates}
          selectedCell={tb.selectedCell}
          onCellClick={tb.setSelectedCell}
          onAddColumn={handleAddColumnClick}
          onDeleteColumn={tb.deleteColumn}
        />
      </div>

      {/* Column command palette */}
      <ColumnCommandPalette
        open={paletteOpen}
        onClose={() => setPaletteOpen(false)}
        onSelectEnrichment={handleSelectEnrichment}
        onSelectAI={handleSelectAI}
        onSelectFormula={handleSelectFormula}
        onSelectGate={handleSelectGate}
        onSelectStatic={handleSelectStatic}
      />

      {/* Column config panel */}
      <ColumnConfigPanel
        open={configOpen}
        onClose={() => setConfigOpen(false)}
        onSave={handleSaveColumn}
        editingColumn={editingColumn}
        selectedTool={selectedTool}
        initialType={initialType}
        availableColumns={availableColumns}
      />

      {/* Cell detail panel */}
      <CellDetailPanel
        open={tb.selectedCell !== null}
        onClose={() => tb.setSelectedCell(null)}
        table={tb.table}
        row={selectedRow}
        columnId={tb.selectedCell?.columnId || null}
        onAddAsColumn={handleAddAsColumn}
      />
    </div>
  );
}
