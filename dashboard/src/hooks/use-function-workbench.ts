"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useSearchParams } from "next/navigation";
import {
  fetchFunctions,
  fetchFunction,
  runFunction,
} from "@/lib/api";
import type { FunctionDefinition } from "@/lib/types";
import { toast } from "sonner";
import Papa from "papaparse";

export type WorkbenchStep = "upload" | "map" | "run" | "results";
export type RowStatus = "pending" | "running" | "done" | "error";
export type MatchConfidence = "exact" | "fuzzy" | "manual";

export interface CsvData {
  fileName: string;
  headers: string[];
  rows: Record<string, string>[];
  totalRows: number;
}

export interface ColumnMapping {
  csvColumn: string;
  functionInput: string;
}

export interface ResultRow {
  rowIndex: number;
  status: RowStatus;
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  error: string | null;
}

export interface UseFunctionWorkbenchReturn {
  // State
  step: WorkbenchStep;
  csvData: CsvData | null;
  selectedFunction: FunctionDefinition | null;
  functions: FunctionDefinition[];
  functionsByFolder: Record<string, FunctionDefinition[]>;
  mappings: ColumnMapping[];
  results: ResultRow[];
  running: boolean;
  progress: { done: number; total: number };
  expandedCell: { row: number; col: string } | null;
  sortColumn: string | null;
  sortDir: "asc" | "desc";
  statusFilter: RowStatus | "all";
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  autoMapConfidence: Record<string, MatchConfidence>;
  expandedError: number | null;

  // Actions
  handleFileUpload: (file: File) => void;
  handleDrop: (e: React.DragEvent) => void;
  handleSelectFunction: (func: FunctionDefinition) => void;
  handleMapColumn: (csvCol: string, funcInput: string) => void;
  handleClearMapping: (funcInput: string) => void;
  handleRun: () => Promise<void>;
  handleRetryFailed: () => Promise<void>;
  handleExport: (selectedOnly?: boolean) => void;
  getDisplayResults: () => ResultRow[];
  detectColumnType: (header: string, values: string[]) => string;
  resetWorkbench: () => void;
  setExpandedCell: (cell: { row: number; col: string } | null) => void;
  setSortColumn: (col: string | null) => void;
  setSortDir: (dir: "asc" | "desc") => void;
  setStatusFilter: (filter: RowStatus | "all") => void;
  setExpandedError: (row: number | null) => void;
  canRun: boolean;
  successRate: number;
  errorCount: number;
  doneCount: number;
}

export function useFunctionWorkbench(): UseFunctionWorkbenchReturn {
  const searchParams = useSearchParams();
  const preselectedFunc = searchParams.get("function");

  const [step, setStep] = useState<WorkbenchStep>("upload");
  const [csvData, setCsvData] = useState<CsvData | null>(null);
  const [selectedFunction, setSelectedFunction] = useState<FunctionDefinition | null>(null);
  const [functions, setFunctions] = useState<FunctionDefinition[]>([]);
  const [functionsByFolder, setFunctionsByFolder] = useState<Record<string, FunctionDefinition[]>>({});
  const [mappings, setMappings] = useState<ColumnMapping[]>([]);
  const [results, setResults] = useState<ResultRow[]>([]);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [expandedCell, setExpandedCell] = useState<{ row: number; col: string } | null>(null);
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [statusFilter, setStatusFilter] = useState<RowStatus | "all">("all");
  const [autoMapConfidence, setAutoMapConfidence] = useState<Record<string, MatchConfidence>>({});
  const [expandedError, setExpandedError] = useState<number | null>(null);

  // Load functions
  useEffect(() => {
    fetchFunctions().then(res => {
      setFunctions(res.functions);
      setFunctionsByFolder(res.by_folder);
    }).catch(() => {});
  }, []);

  // Pre-select function from URL param
  useEffect(() => {
    if (preselectedFunc && !selectedFunction) {
      fetchFunction(preselectedFunc)
        .then(f => setSelectedFunction(f))
        .catch(() => {});
    }
  }, [preselectedFunc, selectedFunction]);

  // Auto-map columns by name similarity
  const autoMapColumns = useCallback((csvHeaders: string[], func: FunctionDefinition) => {
    const newMappings: ColumnMapping[] = [];
    const confidence: Record<string, MatchConfidence> = {};

    for (const input of func.inputs) {
      const exactMatch = csvHeaders.find(h => h.toLowerCase() === input.name.toLowerCase());
      const fuzzyMatch = csvHeaders.find(h =>
        h.toLowerCase().includes(input.name.toLowerCase()) ||
        input.name.toLowerCase().includes(h.toLowerCase())
      );
      const match = exactMatch || fuzzyMatch;
      if (match) {
        newMappings.push({ csvColumn: match, functionInput: input.name });
        confidence[input.name] = exactMatch ? "exact" : "fuzzy";
      }
    }
    setMappings(newMappings);
    setAutoMapConfidence(confidence);
  }, []);

  const handleFileUpload = useCallback((file: File) => {
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (result) => {
        const headers = result.meta.fields || [];
        const rows = result.data as Record<string, string>[];
        setCsvData({
          fileName: file.name,
          headers,
          rows,
          totalRows: rows.length,
        });

        if (selectedFunction) {
          autoMapColumns(headers, selectedFunction);
        }

        toast.success(`Loaded ${rows.length} rows from ${file.name}`);
      },
      error: () => {
        toast.error("Failed to parse CSV file");
      },
    });
  }, [selectedFunction, autoMapColumns]);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith(".csv")) {
      handleFileUpload(file);
    } else {
      toast.error("Please upload a .csv file");
    }
  }, [handleFileUpload]);

  const handleSelectFunction = useCallback((func: FunctionDefinition) => {
    setSelectedFunction(func);
    if (csvData) {
      autoMapColumns(csvData.headers, func);
    }
  }, [csvData, autoMapColumns]);

  const handleMapColumn = useCallback((csvCol: string, funcInput: string) => {
    setMappings(prev => {
      const filtered = prev.filter(m => m.functionInput !== funcInput);
      return [...filtered, { csvColumn: csvCol, functionInput: funcInput }];
    });
    setAutoMapConfidence(prev => ({ ...prev, [funcInput]: "manual" }));
  }, []);

  const handleClearMapping = useCallback((funcInput: string) => {
    setMappings(prev => prev.filter(m => m.functionInput !== funcInput));
    setAutoMapConfidence(prev => {
      const next = { ...prev };
      delete next[funcInput];
      return next;
    });
  }, []);

  const canRun = !!(csvData && selectedFunction && mappings.length > 0);

  const handleRun = useCallback(async () => {
    if (!csvData || !selectedFunction) return;

    setStep("run");
    setRunning(true);
    const totalRows = csvData.rows.length;
    setProgress({ done: 0, total: totalRows });

    const newResults: ResultRow[] = csvData.rows.map((_, i) => ({
      rowIndex: i,
      status: "pending" as RowStatus,
      input: {},
      output: null,
      error: null,
    }));
    setResults(newResults);

    for (let i = 0; i < totalRows; i++) {
      const row = csvData.rows[i];
      const input: Record<string, unknown> = {};
      for (const mapping of mappings) {
        input[mapping.functionInput] = row[mapping.csvColumn];
      }

      newResults[i].status = "running";
      newResults[i].input = input;
      setResults([...newResults]);

      try {
        const result = await runFunction(selectedFunction.id, input);
        if (result.error) {
          newResults[i].status = "error";
          newResults[i].error = String(result.error_message || "Unknown error");
        } else {
          newResults[i].status = "done";
          newResults[i].output = result;
        }
      } catch (e) {
        newResults[i].status = "error";
        newResults[i].error = e instanceof Error ? e.message : "Network error";
      }

      setProgress({ done: i + 1, total: totalRows });
      setResults([...newResults]);
    }

    setRunning(false);
    setStep("results");
  }, [csvData, selectedFunction, mappings]);

  const handleRetryFailed = useCallback(async () => {
    if (!csvData || !selectedFunction) return;
    setRunning(true);
    const failedIndices = results.filter(r => r.status === "error").map(r => r.rowIndex);
    const newResults = [...results];

    for (const i of failedIndices) {
      const row = csvData.rows[i];
      const input: Record<string, unknown> = {};
      for (const mapping of mappings) {
        input[mapping.functionInput] = row[mapping.csvColumn];
      }

      newResults[i].status = "running";
      setResults([...newResults]);

      try {
        const result = await runFunction(selectedFunction.id, input);
        if (result.error) {
          newResults[i].status = "error";
          newResults[i].error = String(result.error_message || "Unknown error");
        } else {
          newResults[i].status = "done";
          newResults[i].output = result;
        }
      } catch (e) {
        newResults[i].status = "error";
        newResults[i].error = e instanceof Error ? e.message : "Network error";
      }
      setResults([...newResults]);
    }
    setRunning(false);
  }, [csvData, selectedFunction, mappings, results]);

  const handleExport = useCallback((selectedOnly?: boolean) => {
    const rowsToExport = selectedOnly
      ? results.filter(r => r.status === "done")
      : results;

    if (rowsToExport.length === 0) {
      toast.error("No rows to export");
      return;
    }

    const exportRows = rowsToExport.map(r => {
      const inputRow = csvData?.rows[r.rowIndex] || {};
      return { ...inputRow, ...r.output, _status: r.status, _error: r.error || "" };
    });

    const csv = Papa.unparse(exportRows);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `results-${selectedFunction?.id || "export"}.csv`;
    a.click();
    URL.revokeObjectURL(url);
    toast.success("Exported CSV");
  }, [results, csvData, selectedFunction]);

  const getDisplayResults = useCallback(() => {
    let display = [...results];
    if (statusFilter !== "all") {
      display = display.filter(r => r.status === statusFilter);
    }
    if (sortColumn) {
      display.sort((a, b) => {
        const aVal = String(a.output?.[sortColumn] ?? a.input?.[sortColumn] ?? "");
        const bVal = String(b.output?.[sortColumn] ?? b.input?.[sortColumn] ?? "");
        return sortDir === "asc" ? aVal.localeCompare(bVal) : bVal.localeCompare(aVal);
      });
    }
    return display;
  }, [results, statusFilter, sortColumn, sortDir]);

  const detectColumnType = useCallback((header: string, values: string[]) => {
    const sample = values.filter(v => v).slice(0, 10);
    if (sample.every(v => /^[\w.+-]+@[\w.-]+\.\w+$/.test(v))) return "email";
    if (sample.every(v => /^https?:\/\//.test(v))) return "url";
    if (sample.every(v => !isNaN(Number(v)))) return "number";
    return "string";
  }, []);

  const resetWorkbench = useCallback(() => {
    setStep("upload");
    setResults([]);
    setCsvData(null);
    setMappings([]);
    setSelectedFunction(null);
    setAutoMapConfidence({});
    setExpandedError(null);
  }, []);

  const doneCount = results.filter(r => r.status === "done").length;
  const errorCount = results.filter(r => r.status === "error").length;
  const successRate = results.length > 0 ? (doneCount / results.length) * 100 : 0;

  return {
    step,
    csvData,
    selectedFunction,
    functions,
    functionsByFolder,
    mappings,
    results,
    running,
    progress,
    expandedCell,
    sortColumn,
    sortDir,
    statusFilter,
    fileInputRef,
    autoMapConfidence,
    expandedError,
    handleFileUpload,
    handleDrop,
    handleSelectFunction,
    handleMapColumn,
    handleClearMapping,
    handleRun,
    handleRetryFailed,
    handleExport,
    getDisplayResults,
    detectColumnType,
    resetWorkbench,
    setExpandedCell,
    setSortColumn,
    setSortDir,
    setStatusFilter,
    setExpandedError,
    canRun,
    successRate,
    errorCount,
    doneCount,
  };
}
