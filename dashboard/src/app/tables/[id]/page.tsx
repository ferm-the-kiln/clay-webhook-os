"use client";

import { use, useState, useCallback } from "react";
import { useTableBuilder } from "@/hooks/use-table-builder";
import { TableToolbar } from "@/components/table-builder/table-toolbar";
import { TableGrid } from "@/components/table-builder/table-grid";
import { ColumnCommandPalette } from "@/components/table-builder/column-command-palette";
import { ColumnConfigPanel } from "@/components/table-builder/column-config-panel";
import { ColumnSuggestionsBar } from "@/components/table-builder/column-suggestions-bar";
import { CellDetailPanel } from "@/components/table-builder/cell-detail-panel";
import { CsvImportDialog } from "@/components/table-builder/csv-import-dialog";
import { Loader2 } from "lucide-react";
import type { ToolDefinition, TableColumn } from "@/lib/types";
import { fetchTools } from "@/lib/api";
import { autoMapInputs } from "@/lib/auto-map-inputs";

export default function TableBuilderPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = use(params);
  const tb = useTableBuilder(id);

  // Import dialog state
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importDialogOpen, setImportDialogOpen] = useState(false);

  // Column palette state
  const [paletteOpen, setPaletteOpen] = useState(false);

  // Column config panel state
  const [configOpen, setConfigOpen] = useState(false);
  const [editingColumn, setEditingColumn] = useState<TableColumn | null>(null);
  const [selectedTool, setSelectedTool] = useState<ToolDefinition | null>(null);
  const [initialType, setInitialType] = useState<string | null>(null);
  const [initialParams, setInitialParams] = useState<Record<string, string> | undefined>(undefined);

  // Open command palette from "+" button
  const handleAddColumnClick = useCallback(() => {
    setPaletteOpen(true);
  }, []);

  // Handle palette selections
  const handleSelectEnrichment = useCallback((tool: ToolDefinition) => {
    setSelectedTool(tool);
    setInitialType("enrichment");
    setEditingColumn(null);
    setInitialParams(undefined);
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

  // Handle suggestion from the suggestions bar
  const handleAddSuggestion = useCallback(
    async (toolId: string, name: string) => {
      try {
        const res = await fetchTools();
        const tool = res.tools.find((t: ToolDefinition) => t.id === toolId);
        if (!tool) return;

        // Auto-map inputs from available columns
        const cols = tb.table?.columns.filter((c) => !c.hidden) || [];
        const mapped = tool.inputs ? autoMapInputs(tool.inputs, cols) : {};

        setSelectedTool(tool);
        setInitialType("enrichment");
        setEditingColumn(null);
        setInitialParams(mapped);
        setConfigOpen(true);
      } catch {
        // Fallback: just open the palette
        setPaletteOpen(true);
      }
    },
    [tb.table?.columns],
  );

  // Save column config — returns new column ID for child column creation
  const handleSaveColumn = useCallback(
    async (config: Record<string, unknown>): Promise<string | void> => {
      if (editingColumn) {
        await tb.editColumn(editingColumn.id, config);
        return;
      }
      return await tb.addColumn(config);
    },
    [tb, editingColumn],
  );

  // Edit column config — opens config panel pre-filled with existing column
  const handleEditColumnConfig = useCallback(
    async (column: TableColumn) => {
      setEditingColumn(column);
      setInitialParams(undefined);

      if (column.column_type === "enrichment" && column.tool) {
        // Fetch the tool definition so the config panel can show inputs/outputs
        try {
          const res = await fetchTools();
          const tool = res.tools.find((t: ToolDefinition) => t.id === column.tool);
          setSelectedTool(tool || null);
        } catch {
          setSelectedTool(null);
        }
      } else {
        setSelectedTool(null);
      }

      setInitialType(column.column_type);
      setConfigOpen(true);
    },
    [],
  );

  // Duplicate a column
  const handleDuplicateColumn = useCallback(
    async (columnId: string) => {
      const col = tb.table?.columns.find((c) => c.id === columnId);
      if (!col) return;
      const config: Record<string, unknown> = {
        name: `${col.name} (copy)`,
        column_type: col.column_type,
      };
      if (col.tool) config.tool = col.tool;
      if (col.params) config.params = col.params;
      if (col.output_key) config.output_key = col.output_key;
      if (col.ai_prompt) config.ai_prompt = col.ai_prompt;
      if (col.ai_model) config.ai_model = col.ai_model;
      if (col.formula) config.formula = col.formula;
      if (col.condition) config.condition = col.condition;
      if (col.condition_label) config.condition_label = col.condition_label;
      await tb.addColumn(config);
    },
    [tb],
  );

  // Hide a column
  const handleHideColumn = useCallback(
    async (columnId: string) => {
      await tb.editColumn(columnId, { hidden: true });
    },
    [tb],
  );

  // Run a single column
  const handleRunColumn = useCallback(
    (columnId: string) => {
      tb.executeTable({ columnIds: [columnId] });
    },
    [tb],
  );

  // Re-run failed rows for a column
  const handleRerunColumnFailed = useCallback(
    (columnId: string) => {
      tb.executeTable({ columnIds: [columnId] });
    },
    [tb],
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
        onImportCsv={async (file) => {
          setImportFile(file);
          setImportDialogOpen(true);
        }}
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

      <ColumnSuggestionsBar
        table={tb.table}
        onAddSuggestion={handleAddSuggestion}
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
          onRenameColumn={(colId, name) => tb.editColumn(colId, { name })}
          onEditColumnConfig={handleEditColumnConfig}
          onDuplicateColumn={handleDuplicateColumn}
          onHideColumn={handleHideColumn}
          onRunColumn={handleRunColumn}
          onRerunColumnFailed={handleRerunColumnFailed}
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
        initialParams={initialParams}
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

      {/* CSV Import dialog */}
      <CsvImportDialog
        open={importDialogOpen}
        onClose={() => {
          setImportDialogOpen(false);
          setImportFile(null);
        }}
        onImport={tb.importCsv}
        table={tb.table}
        file={importFile}
      />
    </div>
  );
}
