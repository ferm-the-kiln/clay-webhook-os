"use client";

import { useState, useEffect, useRef, useCallback, useMemo } from "react";
import {
  Download, ExternalLink, RotateCcw, CheckCircle2, XCircle, Loader2, Square,
  Search, Brain, Calculator, Filter, RefreshCw, X, Copy, Clock,
  ChevronUp, ChevronDown, CheckSquare, Search as SearchIcon,
  FileSpreadsheet, FolderUp,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import Papa from "papaparse";
import {
  createTable, importTableCsv, addTableColumn, streamTableExecution,
  exportTableCsv, fetchTableRows, fetchTable, exportTableToSheet, exportTableToDrive,
  getLocalRunnerStatus,
} from "@/lib/api";
import type { WorkflowTemplate, TableExecutionEvent, TableColumn, TableRow, CellState } from "@/lib/types";
import { EnrichmentCell } from "@/components/table-builder/enrichment-cell";
import { RunnerRequiredModal } from "@/components/runner/runner-required-modal";
import { useRunnerGate } from "@/hooks/use-runner-gate";
import type { CsvPreview } from "./step-upload";

type Phase = "creating" | "importing" | "configuring" | "enriching" | "done" | "error";
type RowFilter = "all" | "success" | "errors";
type RowQuality = "complete" | "partial" | "error";

interface StepProgressProps {
  csvPreview: CsvPreview;
  selectedRecipes: WorkflowTemplate[];
  columnMapping: Record<string, string>;
  onStartOver: () => void;
  rowLimit?: number;
}

interface ColumnProgressData { done: number; total: number; errors: number; }

const COLUMN_TYPE_STYLES: Record<string, { icon: typeof Search; color: string }> = {
  enrichment: { icon: Search, color: "border-l-blue-500" },
  ai: { icon: Brain, color: "border-l-purple-500" },
  formula: { icon: Calculator, color: "border-l-teal-500" },
  gate: { icon: Filter, color: "border-l-amber-500" },
};

function formatEta(ms: number): string {
  const s = Math.round(ms / 1000);
  if (s < 60) return `~${s}s`;
  const m = Math.round(s / 60);
  if (m < 60) return `~${m}m`;
  return `~${Math.floor(m / 60)}h ${m % 60}m`;
}

export function StepProgress({
  csvPreview, selectedRecipes, columnMapping, onStartOver, rowLimit,
}: StepProgressProps) {
  // ── Core state ──
  const [phase, setPhase] = useState<Phase>("creating");
  const [tableId, setTableId] = useState<string | null>(null);
  const [tableName, setTableName] = useState("");
  const [errorMsg, setErrorMsg] = useState("");
  const [progress, setProgress] = useState({ done: 0, total: 0, errors: 0 });
  const [columns, setColumns] = useState<TableColumn[]>([]);
  const [rows, setRows] = useState<TableRow[]>([]);
  const [columnProgress, setColumnProgress] = useState<Record<string, ColumnProgressData>>({});
  const [showConfetti, setShowConfetti] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [enrichStartTime, setEnrichStartTime] = useState(0);
  const abortRef = useRef<AbortController | null>(null);
  const startedRef = useRef(false);

  // ── Review state ──
  const [selectedCell, setSelectedCell] = useState<{ rowId: string; columnId: string } | null>(null);
  const [rowFilter, setRowFilter] = useState<RowFilter>("all");
  const [approvedRows, setApprovedRows] = useState<Set<string>>(new Set());
  const [editingCell, setEditingCell] = useState<{ rowId: string; columnId: string } | null>(null);
  const [editedCells, setEditedCells] = useState<Set<string>>(new Set());
  const [sortConfig, setSortConfig] = useState<{ columnId: string; direction: "asc" | "desc" } | null>(null);
  const [searchQuery, setSearchQuery] = useState("");
  const [exporting, setExporting] = useState<"sheets" | "drive" | null>(null);
  const [runnerConnected, setRunnerConnected] = useState<boolean | null>(null);
  const editInputRef = useRef<HTMLInputElement>(null);
  const { guardedRun, modalProps: runnerModalProps } = useRunnerGate();

  // Poll local runner status
  useEffect(() => {
    let active = true;
    const check = () => {
      getLocalRunnerStatus()
        .then((s) => { if (active) setRunnerConnected(s.connected); })
        .catch(() => { if (active) setRunnerConnected(false); });
    };
    check();
    const interval = setInterval(check, 10_000);
    return () => { active = false; clearInterval(interval); };
  }, []);

  // ── Derived ──
  const enrichmentCols = useMemo(() => columns.filter((c) => c.column_type !== "input"), [columns]);
  const isDone = phase === "done";

  function getRowQuality(row: TableRow): RowQuality {
    if (enrichmentCols.length === 0) return "complete";
    const statuses = enrichmentCols.map((c) => (row[`${c.id}__status`] as CellState) || "empty");
    const doneCount = statuses.filter((s) => s === "done").length;
    if (doneCount === enrichmentCols.length) return "complete";
    const errorCount = statuses.filter((s) => s === "error").length;
    if (errorCount === enrichmentCols.length) return "error";
    return "partial";
  }

  // Filter → search → sort pipeline
  const filteredRows = useMemo(() => {
    if (rowFilter === "all") return rows;
    return rows.filter((row) => {
      const hasError = enrichmentCols.some((col) => (row[`${col.id}__status`] as CellState) === "error");
      return rowFilter === "errors" ? hasError : !hasError;
    });
  }, [rows, rowFilter, enrichmentCols]);

  const displayRows = useMemo(() => {
    let result = filteredRows;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      result = result.filter((row) =>
        columns.some((col) => {
          const val = row[`${col.id}__value`];
          return val != null && String(val).toLowerCase().includes(q);
        }),
      );
    }
    if (sortConfig) {
      result = [...result].sort((a, b) => {
        const aVal = a[`${sortConfig.columnId}__value`];
        const bVal = b[`${sortConfig.columnId}__value`];
        if (aVal == null && bVal == null) return 0;
        if (aVal == null) return 1;
        if (bVal == null) return -1;
        const cmp = String(aVal).localeCompare(String(bVal), undefined, { numeric: true });
        return sortConfig.direction === "asc" ? cmp : -cmp;
      });
    }
    return result;
  }, [filteredRows, searchQuery, sortConfig, columns]);

  const errorRowCount = useMemo(() =>
    rows.filter((r) => enrichmentCols.some((c) => (r[`${c.id}__status`] as CellState) === "error")).length,
  [rows, enrichmentCols]);

  const completeCount = useMemo(() => rows.filter((r) => getRowQuality(r) === "complete").length, [rows, enrichmentCols]);
  const partialCount = useMemo(() => rows.filter((r) => getRowQuality(r) === "partial").length, [rows, enrichmentCols]);

  const eta = useMemo(() => {
    if (phase !== "enriching" || progress.done < 5 || enrichStartTime === 0) return null;
    const remaining = ((Date.now() - enrichStartTime) / progress.done) * (progress.total - progress.done);
    return remaining > 0 ? formatEta(remaining) : null;
  }, [phase, progress, enrichStartTime]);

  const pct = progress.total > 0 ? Math.min(100, Math.round((progress.done / progress.total) * 100)) : 0;
  const showGrid = columns.length > 0 && rows.length > 0;
  const isPreGrid = phase === "creating" || phase === "importing" || phase === "configuring";

  // ── Handlers ──
  const handleEvent = useCallback((event: TableExecutionEvent) => {
    if (event.type === "execute_start") {
      setProgress({ done: 0, total: event.total_rows, errors: 0 });
    } else if (event.type === "cell_update") {
      setRows((prev) => prev.map((r) =>
        r._row_id === event.row_id
          ? { ...r, [`${event.column_id}__value`]: event.value, [`${event.column_id}__status`]: event.status, [`${event.column_id}__error`]: event.error }
          : r,
      ));
    } else if (event.type === "column_progress") {
      setProgress((prev) => ({ ...prev, done: event.done, errors: event.errors }));
      setColumnProgress((prev) => ({ ...prev, [event.column_id]: { done: event.done, total: event.total, errors: event.errors } }));
    } else if (event.type === "execute_complete") {
      setProgress({ done: event.cells_done, total: event.cells_done + event.cells_errored, errors: event.cells_errored });
    }
  }, []);

  const handleStop = useCallback(() => { abortRef.current?.abort(); setPhase("done"); }, []);

  const handleRetry = useCallback(() => {
    if (!tableId) return;
    const ids = rows.filter((r) => enrichmentCols.some((c) => (r[`${c.id}__status`] as CellState) === "error")).map((r) => r._row_id);
    if (!ids.length) return;
    setRows((prev) => prev.map((r) => {
      if (!ids.includes(r._row_id)) return r;
      const u = { ...r };
      for (const c of enrichmentCols) { if ((u[`${c.id}__status`] as CellState) === "error") { u[`${c.id}__status`] = "pending"; u[`${c.id}__error`] = undefined; } }
      return u as TableRow;
    }));
    setRetrying(true); setPhase("enriching"); setEnrichStartTime(Date.now());
    const ctrl = streamTableExecution(tableId, (e) => { handleEvent(e); if (e.type === "execute_complete") { setPhase("done"); setRetrying(false); } },
      (err) => { setErrorMsg(err); setPhase("done"); setRetrying(false); }, { row_ids: ids });
    abortRef.current = ctrl;
  }, [tableId, rows, enrichmentCols, handleEvent]);

  const handleSort = useCallback((columnId: string) => {
    setSortConfig((prev) => {
      if (!prev || prev.columnId !== columnId) return { columnId, direction: "asc" };
      if (prev.direction === "asc") return { columnId, direction: "desc" };
      return null;
    });
  }, []);

  const handleToggleApprove = useCallback((rowId: string) => {
    setApprovedRows((prev) => { const next = new Set(prev); if (next.has(rowId)) next.delete(rowId); else next.add(rowId); return next; });
  }, []);

  const handleToggleAll = useCallback(() => {
    const visibleIds = displayRows.map((r) => r._row_id);
    const allChecked = visibleIds.every((id) => approvedRows.has(id));
    setApprovedRows((prev) => {
      const next = new Set(prev);
      if (allChecked) { for (const id of visibleIds) next.delete(id); }
      else { for (const id of visibleIds) next.add(id); }
      return next;
    });
  }, [displayRows, approvedRows]);

  const handleSelectAllSuccess = useCallback(() => {
    setApprovedRows((prev) => {
      const next = new Set(prev);
      for (const row of rows) { if (getRowQuality(row) === "complete") next.add(row._row_id); }
      return next;
    });
  }, [rows, enrichmentCols]);

  const handleClearSelection = useCallback(() => { setApprovedRows(new Set()); }, []);

  const handleCellEdit = useCallback((rowId: string, columnId: string, newValue: string) => {
    setRows((prev) => prev.map((r) => r._row_id === rowId ? { ...r, [`${columnId}__value`]: newValue } : r));
    setEditedCells((prev) => new Set(prev).add(`${rowId}:${columnId}`));
    setEditingCell(null);
  }, []);

  // Focus edit input when editing starts
  useEffect(() => { if (editingCell) editInputRef.current?.focus(); }, [editingCell]);

  // ── Download (respects filter + approval) ──
  const handleDownload = useCallback(async () => {
    if (!tableId) return;
    try {
      const rowsToExport = approvedRows.size > 0
        ? rows.filter((r) => approvedRows.has(r._row_id))
        : rowFilter !== "all" ? filteredRows : null;

      if (rowsToExport) {
        const headers = columns.map((c) => c.name);
        const data = rowsToExport.map((row) => columns.map((col) => {
          const val = row[`${col.id}__value`];
          return val == null ? "" : typeof val === "object" ? JSON.stringify(val) : String(val);
        }));
        const csv = Papa.unparse({ fields: headers, data });
        const blob = new Blob([csv], { type: "text/csv" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a"); a.href = url;
        a.download = `${tableName || "enriched"}${approvedRows.size > 0 ? "-approved" : `-${rowFilter}`}.csv`;
        a.click(); URL.revokeObjectURL(url);
      } else {
        const blob = await exportTableCsv(tableId);
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a"); a.href = url; a.download = `${tableName || "enriched"}.csv`; a.click(); URL.revokeObjectURL(url);
      }
    } catch { setErrorMsg("Failed to export CSV"); }
  }, [tableId, tableName, rowFilter, filteredRows, columns, rows, approvedRows]);

  const handleExportToSheets = useCallback(async () => {
    if (!tableId) return;
    setExporting("sheets");
    try {
      const result = await exportTableToSheet(tableId, tableName || undefined);
      window.open(result.url, "_blank");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to export to Sheets");
    } finally {
      setExporting(null);
    }
  }, [tableId, tableName]);

  const handleExportToDrive = useCallback(async () => {
    if (!tableId) return;
    setExporting("drive");
    try {
      const result = await exportTableToDrive(tableId);
      window.open(result.url, "_blank");
    } catch (err) {
      setErrorMsg(err instanceof Error ? err.message : "Failed to save to Drive");
    } finally {
      setExporting(null);
    }
  }, [tableId]);

  // ── Run ──
  const run = useCallback(async () => {
    if (startedRef.current) return;
    startedRef.current = true;
    if (typeof Notification !== "undefined" && Notification.permission === "default") Notification.requestPermission().catch(() => {});
    try {
      setPhase("creating");
      const name = `Enrichment - ${new Date().toLocaleDateString("en-US", { month: "short", day: "numeric", year: "numeric", hour: "numeric", minute: "2-digit" })}`;
      setTableName(name);
      const table = await createTable({ name }); setTableId(table.id);
      setPhase("importing");
      await importTableCsv(table.id, csvPreview.file, columnMapping);
      setPhase("configuring");
      for (const recipe of selectedRecipes) for (const col of recipe.columns) await addTableColumn(table.id, { name: col.name, column_type: col.column_type, tool: col.tool, params: col.params, ai_prompt: col.ai_prompt, ai_model: col.ai_model, output_key: col.output_key });
      const [tableDef, rowsData] = await Promise.all([fetchTable(table.id), fetchTableRows(table.id, 0, rowLimit ?? 1000)]);
      setColumns(tableDef.columns.filter((c) => !c.hidden)); setRows(rowsData.rows as TableRow[]);
      setPhase("enriching"); setEnrichStartTime(Date.now());
      await new Promise<void>((resolve, reject) => {
        const ctrl = streamTableExecution(table.id, (e) => { handleEvent(e); if (e.type === "execute_complete") resolve(); }, (err) => reject(new Error(err)), rowLimit ? { limit: rowLimit } : undefined);
        abortRef.current = ctrl;
      });
      setPhase("done"); setShowConfetti(true);
      if (typeof document !== "undefined" && document.hidden && typeof Notification !== "undefined" && Notification.permission === "granted") new Notification("Enrichment complete", { body: `${progress.done} cells enriched` });
      try { const entry = { id: table.id, name: csvPreview.file.name, rows: csvPreview.totalRows, recipes: selectedRecipes.map((r) => r.name), timestamp: Date.now() }; const h = JSON.parse(localStorage.getItem("enrich-history") || "[]"); h.unshift(entry); localStorage.setItem("enrich-history", JSON.stringify(h.slice(0, 10))); } catch {}
    } catch (err) {
      if ((err as Error)?.name === "AbortError") { setPhase("done"); return; }
      setErrorMsg(err instanceof Error ? err.message : "Something went wrong"); setPhase("error");
    }
  }, [csvPreview, selectedRecipes, columnMapping, rowLimit, handleEvent, progress.done]);

  useEffect(() => { guardedRun(() => run()); return () => { abortRef.current?.abort(); }; }, [run, guardedRun]);
  useEffect(() => { if (showConfetti) { const t = setTimeout(() => setShowConfetti(false), 2000); return () => clearTimeout(t); } }, [showConfetti]);
  useEffect(() => {
    if (phase === "done" && typeof document !== "undefined" && document.hidden && typeof Notification !== "undefined" && Notification.permission === "granted")
      new Notification("Enrichment complete", { body: `${progress.done} cells enriched` });
  }, [phase, progress.done]);

  // ── Cell detail ──
  const cellDetail = useMemo(() => {
    if (!selectedCell) return null;
    const row = rows.find((r) => r._row_id === selectedCell.rowId);
    const col = columns.find((c) => c.id === selectedCell.columnId);
    if (!row || !col) return null;
    return { colName: col.name, value: row[`${col.id}__value`], status: (row[`${col.id}__status`] as CellState) || "empty", error: row[`${col.id}__error`] as string | undefined };
  }, [selectedCell, rows, columns]);

  // Download button label
  const downloadLabel = approvedRows.size > 0
    ? `Download ${approvedRows.size} approved`
    : rowFilter !== "all" ? `Download (${rowFilter})` : "Download CSV";

  const allVisibleChecked = displayRows.length > 0 && displayRows.every((r) => approvedRows.has(r._row_id));

  return (
    <div className="space-y-3">
      {/* ── Runner required modal ── */}
      <RunnerRequiredModal {...runnerModalProps} />

      {/* ── Status bar ── */}
      {phase !== "error" && (
        <div className="flex items-center gap-3">
          {/* Runner status dot */}
          <div
            className={cn(
              "h-2 w-2 rounded-full shrink-0 transition-colors",
              runnerConnected === true ? "bg-emerald-500" : runnerConnected === false ? "bg-red-500" : "bg-clay-500",
            )}
            title={runnerConnected === true ? "Local runner connected" : runnerConnected === false ? "Local runner disconnected" : "Checking..."}
          />

          <div className="flex items-center gap-2 flex-1 min-w-0">
            {isPreGrid ? (
              <><Loader2 className="h-4 w-4 text-kiln-teal animate-spin shrink-0" /><span className="text-sm text-clay-200">{phase === "creating" ? "Creating table..." : phase === "importing" ? "Importing data..." : "Setting up enrichment..."}</span></>
            ) : phase === "enriching" ? (
              <>
                <Loader2 className="h-4 w-4 text-kiln-teal animate-spin shrink-0" />
                <span className="text-sm text-clay-200">{retrying ? "Retrying..." : "Enriching..."}</span>
                <div className="flex-1 h-1.5 rounded-full bg-clay-700 overflow-hidden max-w-xs"><div className="h-full rounded-full bg-kiln-teal transition-all duration-300" style={{ width: `${pct}%` }} /></div>
                <span className="text-xs text-clay-300 tabular-nums shrink-0">{progress.done}/{progress.total}</span>
                {progress.errors > 0 && <span className="text-xs text-amber-400 shrink-0">{progress.errors} err</span>}
                {eta && <span className="text-xs text-clay-300 shrink-0 flex items-center gap-1"><Clock className="h-3 w-3" />{eta}</span>}
              </>
            ) : (
              <>{showConfetti && <ConfettiBurst />}<CheckCircle2 className="h-4 w-4 text-kiln-teal shrink-0" /><span className="text-sm text-clay-200">Done — {progress.done} cells enriched{progress.errors > 0 && <span className="text-amber-400 ml-1">({progress.errors} errors)</span>}</span></>
            )}
          </div>
          <div className="flex items-center gap-2 shrink-0">
            {phase === "enriching" && <Button variant="outline" size="sm" className="h-7 border-red-500/30 text-red-400 hover:bg-red-500/10 hover:text-red-300" onClick={handleStop}><Square className="h-3 w-3 mr-1 fill-current" />Stop</Button>}
            {isDone && (
              <>
                {errorRowCount > 0 && <Button variant="outline" size="sm" className="h-7 border-amber-500/30 text-amber-400 hover:bg-amber-500/10" onClick={handleRetry}><RefreshCw className="h-3 w-3 mr-1" />Retry {errorRowCount}</Button>}
                <Button size="sm" className="h-7 bg-kiln-teal text-black hover:bg-kiln-teal/90" onClick={handleDownload}><Download className="h-3 w-3 mr-1" />{downloadLabel}</Button>
                {approvedRows.size > 0 && <button onClick={() => { setApprovedRows(new Set()); handleDownload(); }} className="text-[10px] text-clay-300 hover:text-clay-300 underline">all</button>}
                <Button variant="outline" size="sm" className="h-7 border-clay-600 text-clay-300" onClick={handleExportToSheets} disabled={exporting === "sheets"}>
                  {exporting === "sheets" ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <FileSpreadsheet className="h-3 w-3 mr-1" />}Sheets
                </Button>
                <Button variant="outline" size="sm" className="h-7 border-clay-600 text-clay-300" onClick={handleExportToDrive} disabled={exporting === "drive"}>
                  {exporting === "drive" ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <FolderUp className="h-3 w-3 mr-1" />}Drive
                </Button>
                {tableId && <Button variant="outline" size="sm" className="h-7 border-clay-600 text-clay-300" asChild><a href={`/tables/${tableId}`}><ExternalLink className="h-3 w-3 mr-1" />Table Builder</a></Button>}
                <button onClick={onStartOver} className="text-xs text-clay-300 hover:text-clay-300 ml-1"><RotateCcw className="h-3 w-3" /></button>
              </>
            )}
          </div>
        </div>
      )}

      {/* ── Review toolbar (done state) ── */}
      {isDone && showGrid && (
        <div className="flex items-center gap-2 flex-wrap">
          {/* Filter pills */}
          {(["all", "success", "errors"] as RowFilter[]).map((f) => {
            const count = f === "all" ? rows.length : f === "errors" ? errorRowCount : rows.length - errorRowCount;
            return (
              <button key={f} onClick={() => setRowFilter(f)} className={cn("px-2.5 py-1 rounded-md text-xs font-medium transition-colors",
                rowFilter === f ? (f === "errors" ? "bg-red-500/15 text-red-400" : "bg-kiln-teal/15 text-kiln-teal") : "text-clay-300 hover:text-clay-200 hover:bg-clay-800",
              )}>{f === "all" ? "All" : f === "success" ? "Success" : "Errors"} ({count})</button>
            );
          })}

          <div className="w-px h-4 bg-clay-700" />

          {/* Search */}
          <div className="flex items-center gap-1 px-2 py-1 rounded-md border border-clay-700 bg-clay-800/50 min-w-[160px]">
            <SearchIcon className="h-3 w-3 text-clay-300 shrink-0" />
            <input
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search..."
              className="bg-transparent text-xs text-clay-200 placeholder:text-clay-300 outline-none flex-1 min-w-0"
            />
            {searchQuery && <button onClick={() => setSearchQuery("")} className="text-clay-300 hover:text-clay-300"><X className="h-3 w-3" /></button>}
          </div>

          <div className="w-px h-4 bg-clay-700" />

          {/* Bulk actions */}
          <button onClick={handleSelectAllSuccess} className="text-xs text-clay-300 hover:text-clay-200 flex items-center gap-1">
            <CheckSquare className="h-3 w-3" />Select success
          </button>
          {approvedRows.size > 0 && (
            <>
              <button onClick={handleClearSelection} className="text-xs text-clay-300 hover:text-clay-300">Clear</button>
              <span className="text-xs text-kiln-teal font-medium">{approvedRows.size} selected</span>
            </>
          )}

          {/* Summary */}
          <div className="ml-auto text-[10px] text-clay-300 tabular-nums flex items-center gap-2">
            <span>{rows.length} rows</span>
            <span className="text-clay-600">|</span>
            <span className="text-emerald-500">{completeCount} complete</span>
            <span className="text-clay-600">|</span>
            <span className="text-amber-400">{partialCount} partial</span>
            {approvedRows.size > 0 && <><span className="text-clay-600">|</span><span className="text-kiln-teal">{approvedRows.size} approved</span></>}
          </div>
        </div>
      )}

      {/* ── Pre-grid loading ── */}
      {isPreGrid && !showGrid && (
        <div className="flex items-center justify-center py-24">
          <div className="text-center space-y-3">
            <div className="h-10 w-10 mx-auto rounded-full border-2 border-kiln-teal border-t-transparent animate-spin" />
            <p className="text-sm text-clay-300">Preparing your data...</p>
          </div>
        </div>
      )}

      {/* ── Spreadsheet grid ── */}
      {showGrid && (
        <div className="rounded-lg border border-clay-700 overflow-auto" style={{ maxHeight: "calc(100vh - 300px)" }}>
          <table className="w-full text-xs border-collapse">
            <thead className="sticky top-0 z-10">
              <tr>
                {/* Checkbox header */}
                {isDone && (
                  <th className="px-2 py-2 bg-clay-800 border-b border-clay-700 w-8">
                    <input type="checkbox" checked={allVisibleChecked} onChange={handleToggleAll}
                      className="h-3.5 w-3.5 rounded border-clay-600 bg-clay-800 text-kiln-teal focus:ring-kiln-teal/30 cursor-pointer" />
                  </th>
                )}
                {/* Row # header */}
                <th className="px-2 py-2 text-left text-clay-300 font-medium bg-clay-800 border-b border-clay-700 w-12 text-[10px]">#</th>
                {/* Column headers (sortable) */}
                {columns.map((col) => {
                  const typeStyle = COLUMN_TYPE_STYLES[col.column_type];
                  const cp = columnProgress[col.id];
                  const isSorted = sortConfig?.columnId === col.id;
                  return (
                    <th key={col.id}
                      onClick={isDone ? () => handleSort(col.id) : undefined}
                      className={cn(
                        "px-3 py-2 text-left font-medium border-b border-clay-700 bg-clay-800 whitespace-nowrap min-w-[140px]",
                        typeStyle ? `border-l-2 ${typeStyle.color}` : "border-l-2 border-l-clay-600",
                        isDone && "cursor-pointer hover:bg-clay-700/50 select-none",
                      )}
                    >
                      <div className="flex items-center gap-1.5">
                        {typeStyle && <typeStyle.icon className="h-3 w-3 text-clay-300 shrink-0" />}
                        <span className="text-clay-200 truncate">{col.name}</span>
                        {isSorted && (sortConfig.direction === "asc"
                          ? <ChevronUp className="h-3 w-3 text-kiln-teal shrink-0" />
                          : <ChevronDown className="h-3 w-3 text-kiln-teal shrink-0" />
                        )}
                      </div>
                      {col.column_type !== "input" && col.tool && <div className="text-[9px] text-clay-300 mt-0.5">{col.tool}</div>}
                      {phase === "enriching" && cp && cp.total > 0 && (
                        <div className="h-0.5 rounded-full bg-clay-700 mt-1 overflow-hidden flex">
                          <div className="h-full bg-emerald-500 transition-all duration-300" style={{ width: `${((cp.done - cp.errors) / cp.total) * 100}%` }} />
                          {cp.errors > 0 && <div className="h-full bg-red-500 transition-all duration-300" style={{ width: `${(cp.errors / cp.total) * 100}%` }} />}
                        </div>
                      )}
                    </th>
                  );
                })}
              </tr>
            </thead>
            <tbody>
              {displayRows.map((row, ri) => {
                const quality = getRowQuality(row);
                const isApproved = approvedRows.has(row._row_id);
                return (
                  <tr key={row._row_id} className={cn(
                    "border-b border-clay-800/50 last:border-0 hover:bg-clay-800/30 transition-colors",
                    isApproved && "bg-emerald-500/5 border-l-2 border-l-emerald-500/40",
                  )}>
                    {/* Checkbox */}
                    {isDone && (
                      <td className="px-2 py-1.5">
                        <input type="checkbox" checked={isApproved} onChange={() => handleToggleApprove(row._row_id)}
                          className="h-3.5 w-3.5 rounded border-clay-600 bg-clay-800 text-kiln-teal focus:ring-kiln-teal/30 cursor-pointer" />
                      </td>
                    )}
                    {/* Row # with quality dot */}
                    <td className="px-2 py-1.5 text-[10px] tabular-nums">
                      <div className="flex items-center gap-1">
                        <div className={cn("h-1.5 w-1.5 rounded-full shrink-0",
                          quality === "complete" ? "bg-emerald-500" : quality === "partial" ? "bg-amber-400" : "bg-red-500",
                        )} />
                        <span className="text-clay-600">{ri + 1}</span>
                      </div>
                    </td>
                    {/* Cells */}
                    {columns.map((col) => {
                      const value = row[`${col.id}__value`];
                      const status = (row[`${col.id}__status`] as CellState) || (col.column_type === "input" ? "done" : "empty");
                      const error = row[`${col.id}__error`] as string | undefined;
                      const isEnrichment = col.column_type !== "input";
                      const isSelected = selectedCell?.rowId === row._row_id && selectedCell?.columnId === col.id;
                      const isEditing = editingCell?.rowId === row._row_id && editingCell?.columnId === col.id;
                      const wasEdited = editedCells.has(`${row._row_id}:${col.id}`);

                      return (
                        <td key={col.id}
                          onClick={isEnrichment && !isEditing ? () => setSelectedCell({ rowId: row._row_id, columnId: col.id }) : undefined}
                          onDoubleClick={isDone && !isEditing ? () => setEditingCell({ rowId: row._row_id, columnId: col.id }) : undefined}
                          className={cn(
                            "px-3 py-1.5 max-w-[250px]",
                            isEnrichment && !isEditing && "cursor-pointer",
                            isSelected && "ring-1 ring-kiln-teal/50 bg-kiln-teal/5",
                          )}
                        >
                          {isEditing ? (
                            <input
                              ref={editInputRef}
                              defaultValue={value != null ? String(value) : ""}
                              onKeyDown={(e) => {
                                if (e.key === "Enter") handleCellEdit(row._row_id, col.id, (e.target as HTMLInputElement).value);
                                if (e.key === "Escape") setEditingCell(null);
                              }}
                              onBlur={(e) => handleCellEdit(row._row_id, col.id, e.target.value)}
                              className="w-full bg-clay-900 border border-kiln-teal/50 rounded px-1.5 py-0.5 text-xs text-clay-100 outline-none"
                            />
                          ) : !isEnrichment ? (
                            <span className="truncate block text-clay-300">
                              {wasEdited && <span className="inline-block h-1.5 w-1.5 rounded-full bg-blue-400 mr-1 align-middle" />}
                              {value != null ? String(value) : <span className="text-clay-600">&mdash;</span>}
                            </span>
                          ) : (
                            <span className="flex items-center gap-1">
                              {wasEdited && <span className="h-1.5 w-1.5 rounded-full bg-blue-400 shrink-0" />}
                              <EnrichmentCell value={value} status={status} error={error} />
                            </span>
                          )}
                        </td>
                      );
                    })}
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      )}

      {/* ── Cell detail panel ── */}
      {cellDetail && selectedCell && (
        <>
          <div className="fixed inset-0 z-30" onClick={() => setSelectedCell(null)} />
          <div className="fixed right-0 top-0 h-full w-80 bg-clay-800 border-l border-clay-700 z-40 flex flex-col shadow-2xl">
            <div className="flex items-center justify-between px-4 py-3 border-b border-clay-700">
              <div>
                <div className="text-sm font-medium text-clay-100">{cellDetail.colName}</div>
                <div className="flex items-center gap-1.5 mt-0.5">
                  <div className={cn("h-2 w-2 rounded-full", cellDetail.status === "done" ? "bg-emerald-500" : cellDetail.status === "error" ? "bg-red-500" : cellDetail.status === "running" ? "bg-blue-400" : "bg-clay-500")} />
                  <span className="text-[10px] text-clay-300 uppercase">{cellDetail.status}</span>
                </div>
              </div>
              <button onClick={() => setSelectedCell(null)} className="text-clay-300 hover:text-clay-300"><X className="h-4 w-4" /></button>
            </div>
            <div className="flex-1 overflow-auto p-4 space-y-3">
              {cellDetail.status === "error" && cellDetail.error && (
                <div className="rounded-md bg-red-500/10 border border-red-500/20 p-3">
                  <div className="text-[10px] text-red-400 uppercase font-medium mb-1">Error</div>
                  <div className="text-xs text-red-300 break-words">{cellDetail.error}</div>
                </div>
              )}
              {cellDetail.value != null && (
                <div>
                  <div className="text-[10px] text-clay-300 uppercase font-medium mb-1">Value</div>
                  <pre className="text-xs text-clay-200 bg-clay-900 rounded-md p-3 overflow-auto max-h-96 whitespace-pre-wrap break-words">
                    {typeof cellDetail.value === "object" ? JSON.stringify(cellDetail.value, null, 2) : String(cellDetail.value)}
                  </pre>
                </div>
              )}
              {cellDetail.value == null && cellDetail.status !== "error" && <div className="text-sm text-clay-300 text-center py-8">No value yet</div>}
            </div>
            {cellDetail.value != null && (
              <div className="px-4 py-3 border-t border-clay-700">
                <Button variant="outline" size="sm" className="w-full h-7 border-clay-600 text-clay-300" onClick={() => {
                  navigator.clipboard.writeText(typeof cellDetail.value === "object" ? JSON.stringify(cellDetail.value, null, 2) : String(cellDetail.value));
                }}><Copy className="h-3 w-3 mr-1" />Copy value</Button>
              </div>
            )}
          </div>
        </>
      )}

      {/* ── Error state ── */}
      {phase === "error" && (
        <div className="flex flex-col items-center gap-4 py-12">
          <div className="flex items-center gap-2 text-sm text-red-400"><XCircle className="h-4 w-4" />{errorMsg}</div>
          <Button variant="outline" className="border-clay-600 text-clay-300" onClick={onStartOver}><RotateCcw className="h-4 w-4 mr-2" />Start over</Button>
        </div>
      )}
    </div>
  );
}

function ConfettiBurst() {
  const [visible, setVisible] = useState(true);
  const colors = ["#4A9EAD", "#22c55e", "#eab308", "#f97316", "#a855f7"];
  useEffect(() => { const t = setTimeout(() => setVisible(false), 2000); return () => clearTimeout(t); }, []);
  if (!visible) return null;
  return (
    <span className="relative inline-flex pointer-events-none">
      {Array.from({ length: 12 }).map((_, i) => {
        const angle = (i / 12) * 360; const distance = 20 + Math.random() * 15;
        return <span key={i} className="absolute w-1.5 h-1.5 rounded-full" style={{ backgroundColor: colors[i % colors.length], animation: "confetti-burst 0.8s ease-out forwards", animationDelay: `${i * 25}ms`, ["--tx" as string]: `${Math.cos((angle * Math.PI) / 180) * distance}px`, ["--ty" as string]: `${Math.sin((angle * Math.PI) / 180) * distance}px` }} />;
      })}
      <style>{`@keyframes confetti-burst { 0% { transform: translate(0,0) scale(1); opacity: 1; } 100% { transform: translate(var(--tx),var(--ty)) scale(0); opacity: 0; } }`}</style>
    </span>
  );
}
