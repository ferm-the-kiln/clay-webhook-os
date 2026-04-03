"use client";

import { useState, useCallback, useEffect } from "react";
import { toast } from "sonner";
import { TableToolbar } from "@/components/table-builder/table-toolbar";
import { TableGrid } from "@/components/table-builder/table-grid";
import { ColumnCommandPalette } from "@/components/table-builder/column-command-palette";
import { ColumnConfigPanel } from "@/components/table-builder/column-config-panel";
import { CellDetailPanel } from "@/components/table-builder/cell-detail-panel";
import { TableStatusBar } from "@/components/table-builder/table-status-bar";
import { TableFormulaBar } from "@/components/table-builder/table-formula-bar";
import { TableSearchOverlay } from "@/components/table-builder/table-search-overlay";
import { ColumnSuggestionsBar } from "@/components/table-builder/column-suggestions-bar";
import { KeyboardShortcutsHelp } from "@/components/table-builder/keyboard-shortcuts-help";
import { CostEstimatePopover } from "@/components/table-builder/cost-estimate-popover";
import { FunctionSettingsPanel } from "./function-settings-panel";
import { useBrowserNotification } from "@/hooks/use-browser-notification";
import type { UseFunctionTableReturn } from "@/hooks/use-function-table";
import type { ToolDefinition, TableColumn, TableExecutionEvent } from "@/lib/types";
import { fetchTools } from "@/lib/api";
import { autoMapInputs } from "@/lib/auto-map-inputs";
import { CsvImportDialog } from "@/components/table-builder/csv-import-dialog";

interface FunctionSpreadsheetProps {
  ft: UseFunctionTableReturn;
}

export function FunctionSpreadsheet({ ft }: FunctionSpreadsheetProps) {
  // Column palette state
  const [paletteOpen, setPaletteOpen] = useState(false);

  // Column config panel state
  const [configOpen, setConfigOpen] = useState(false);
  const [editingColumn, setEditingColumn] = useState<TableColumn | null>(null);
  const [selectedTool, setSelectedTool] = useState<ToolDefinition | null>(null);
  const [initialType, setInitialType] = useState<string | null>(null);
  const [initialParams, setInitialParams] = useState<Record<string, string> | undefined>(undefined);

  // Import dialog state
  const [importFile, setImportFile] = useState<File | null>(null);
  const [importDialogOpen, setImportDialogOpen] = useState(false);

  // Search state
  const [searchOpen, setSearchOpen] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [searchMatches, setSearchMatches] = useState(0);
  const [currentMatch, setCurrentMatch] = useState(0);

  // Browser notifications
  const { notify } = useBrowserNotification();

  // Notify on execution complete when tab is backgrounded
  useEffect(() => {
    if (!ft.executing) return;
    // Watch for execution to complete
    const checkComplete = () => {
      if (!ft.executing) {
        const done = Object.values(ft.columnProgress).reduce((s, p) => s + p.done, 0);
        const errors = Object.values(ft.columnProgress).reduce((s, p) => s + p.errors, 0);
        const total = Object.values(ft.columnProgress).reduce((s, p) => s + p.total, 0);
        if (total > 0) {
          notify(
            "Enrichment Complete",
            `${done}/${total} cells succeeded${errors > 0 ? ` (${errors} errors)` : ""}`,
          );
        }
      }
    };
    return checkComplete;
  }, [ft.executing, ft.columnProgress, notify]);

  // Cmd+F to open search
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "f") {
        e.preventDefault();
        setSearchOpen(true);
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, []);

  // Search logic
  const handleSearch = useCallback(
    (query: string) => {
      setSearchQuery(query);
      if (!query) {
        setSearchMatches(0);
        setCurrentMatch(0);
        return;
      }
      const q = query.toLowerCase();
      let count = 0;
      for (const row of ft.rows) {
        for (const key of Object.keys(row)) {
          if (key.endsWith("__value")) {
            const val = row[key];
            if (val !== null && val !== undefined && String(val).toLowerCase().includes(q)) {
              count++;
            }
          }
        }
      }
      setSearchMatches(count);
      setCurrentMatch(0);
    },
    [ft.rows],
  );

  // Open command palette from "+" button
  const handleAddColumnClick = useCallback(() => {
    setPaletteOpen(true);
  }, []);

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
    await ft.addColumn({ name: "New Column", column_type: "static" });
  }, [ft]);

  const handleSaveColumn = useCallback(
    async (config: Record<string, unknown>): Promise<string | void> => {
      if (editingColumn) {
        await ft.editColumn(editingColumn.id, config);
        return;
      }
      return await ft.addColumn(config);
    },
    [ft, editingColumn],
  );

  // Edit column config — opens config panel pre-filled with existing column
  const handleEditColumnConfig = useCallback(
    async (column: TableColumn) => {
      setEditingColumn(column);
      setInitialParams(undefined);

      if (column.column_type === "enrichment" && column.tool) {
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
      const col = ft.table?.columns.find((c) => c.id === columnId);
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
      await ft.addColumn(config);
    },
    [ft],
  );

  // Hide a column
  const handleHideColumn = useCallback(
    async (columnId: string) => {
      await ft.editColumn(columnId, { hidden: true });
    },
    [ft],
  );

  // Run a single column
  const handleRunColumn = useCallback(
    (columnId: string) => {
      ft.executeTable({ columnIds: [columnId] });
    },
    [ft],
  );

  // Re-run failed rows for a column
  const handleRerunColumnFailed = useCallback(
    (columnId: string) => {
      ft.executeTable({ columnIds: [columnId] });
    },
    [ft],
  );

  const handleAddAsColumn = useCallback(
    async (path: string, _value: unknown) => {
      if (!ft.selectedCell) return;
      await ft.addColumn({
        name: path.split(".").pop() || path,
        column_type: "formula",
        parent_column_id: ft.selectedCell.columnId,
        extract_path: path,
        formula: `{{${ft.selectedCell.columnId}}}`,
      });
    },
    [ft],
  );

  // Smart suggestion handler
  const handleAddSuggestion = useCallback(
    async (toolId: string, name: string) => {
      // Find a domain/company input column for auto-wiring params
      const inputCols = ft.table?.columns.filter((c) => c.column_type === "input") || [];
      const domainCol = inputCols.find((c) => c.id === "domain" || c.id === "website" || c.name.toLowerCase().includes("domain"));
      const companyCol = inputCols.find((c) => c.id === "company" || c.id === "company_name" || c.name.toLowerCase().includes("company"));

      const params: Record<string, string> = {};
      if (toolId === "findymail" && domainCol) params.domain = `{{${domainCol.id}}}`;
      else if (toolId === "web_search" && (domainCol || companyCol)) params.query = `{{${(domainCol || companyCol)!.id}}} company info`;
      else if (toolId === "apollo_people" && companyCol) params.company = `{{${companyCol.id}}}`;
      else if (toolId === "apollo_org" && (domainCol || companyCol)) params.domain = `{{${(domainCol || companyCol)!.id}}}`;

      await ft.addColumn({
        name,
        column_type: "enrichment",
        tool: toolId,
        params,
      });
      toast.success(`Added ${name} column`);
    },
    [ft],
  );

  const availableColumns = ft.table?.columns.filter((c) => !c.hidden) || [];

  const selectedRow = ft.selectedCell
    ? ft.rows.find((r) => r._row_id === ft.selectedCell!.rowId) || null
    : null;

  if (!ft.table) return null;

  return (
    <>
      <TableToolbar
        table={ft.table}
        totalRows={ft.totalRows}
        executing={ft.executing}
        onRename={ft.rename}
        onImportCsv={async (file) => {
          setImportFile(file);
          setImportDialogOpen(true);
        }}
        onAddRow={() => ft.addRow({})}
        onRefresh={ft.refresh}
        selectedCount={Object.keys(ft.rowSelection).length}
        onDeleteSelected={() => {
          const ids = Object.keys(ft.rowSelection);
          if (ids.length > 0) ft.removeRows(ids);
        }}
        onExecute={(options) => ft.executeTable(options)}
        onStop={ft.stopExecution}
        onSettings={() => ft.setSettingsOpen(true)}
      />

      {/* Smart suggestions (shows when no enrichment columns yet) */}
      <ColumnSuggestionsBar
        table={ft.table}
        onAddSuggestion={handleAddSuggestion}
      />

      {/* Formula bar */}
      <TableFormulaBar
        table={ft.table}
        selectedCell={ft.selectedCell}
        rows={ft.rows}
      />

      {/* Main grid */}
      <div className="flex-1 overflow-hidden relative">
        <TableGrid
          table={ft.table}
          rows={ft.rows}
          columns={ft.tanstackColumns}
          sorting={ft.sorting}
          onSortingChange={ft.setSorting}
          rowSelection={ft.rowSelection}
          onRowSelectionChange={ft.setRowSelection}
          columnSizing={ft.columnSizing}
          onColumnSizingChange={ft.setColumnSizing}
          globalFilter={ft.globalFilter}
          columnProgress={ft.columnProgress}
          cellStates={ft.cellStates}
          selectedCell={ft.selectedCell}
          onCellClick={ft.setSelectedCell}
          onAddColumn={handleAddColumnClick}
          onDeleteColumn={ft.deleteColumn}
          onRenameColumn={async (colId, name) => ft.editColumn(colId, { name })}
          onEditColumnConfig={handleEditColumnConfig}
          onDuplicateColumn={handleDuplicateColumn}
          onHideColumn={handleHideColumn}
          onRunColumn={handleRunColumn}
          onRerunColumnFailed={handleRerunColumnFailed}
          onUpdateCell={ft.updateCell}
          expandedRowId={ft.expandedRowId}
          onToggleExpandRow={(id) =>
            ft.setExpandedRowId(ft.expandedRowId === id ? null : id)
          }
        />

        {/* Search overlay */}
        <TableSearchOverlay
          open={searchOpen}
          onClose={() => {
            setSearchOpen(false);
            setSearchQuery("");
            setSearchMatches(0);
          }}
          onSearch={handleSearch}
          matchCount={searchMatches}
          currentMatch={currentMatch}
          onNavigate={(dir) => {
            if (searchMatches === 0) return;
            setCurrentMatch((prev) =>
              dir === "down"
                ? (prev + 1) % searchMatches
                : (prev - 1 + searchMatches) % searchMatches,
            );
          }}
        />
      </div>

      {/* Status bar */}
      <TableStatusBar
        table={ft.table}
        rows={ft.rows}
        executing={ft.executing}
      />

      {/* Keyboard shortcuts help */}
      <KeyboardShortcutsHelp />

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
        open={ft.selectedCell !== null}
        onClose={() => ft.setSelectedCell(null)}
        table={ft.table}
        row={selectedRow}
        columnId={ft.selectedCell?.columnId || null}
        onAddAsColumn={handleAddAsColumn}
      />

      {/* Function settings panel */}
      {ft.func && (
        <FunctionSettingsPanel
          open={ft.settingsOpen}
          onClose={() => ft.setSettingsOpen(false)}
          func={ft.func}
          onSave={ft.updateFunctionMeta}
          onDelete={ft.deleteFn}
          onDuplicate={ft.duplicateFn}
        />
      )}

      {/* CSV Import dialog */}
      <CsvImportDialog
        open={importDialogOpen}
        onClose={() => {
          setImportDialogOpen(false);
          setImportFile(null);
        }}
        onImport={ft.importCsv}
        table={ft.table}
        file={importFile}
      />
    </>
  );
}
