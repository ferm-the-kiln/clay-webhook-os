"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import { useSearchParams } from "next/navigation";
import {
  fetchFunctions,
  fetchFunction,
  fetchSheetsStatus,
  exportRunToSheets,
  executeFunction,
  executeFunctionBatch,
  isLocalExecutionMode,
} from "@/lib/api";
import type { FunctionDefinition } from "@/lib/types";
import type { SpreadsheetRow } from "@/components/shared/spreadsheet";
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
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  autoMapConfidence: Record<string, MatchConfidence>;
  spreadsheetRows: SpreadsheetRow[];
  sheetsAvailable: boolean;
  exportingSheet: boolean;

  // Actions
  handleFileUpload: (file: File) => void;
  handleDrop: (e: React.DragEvent) => void;
  handleSelectFunction: (func: FunctionDefinition) => void;
  handleMapColumn: (csvCol: string, funcInput: string) => void;
  handleClearMapping: (funcInput: string) => void;
  handleRun: () => Promise<void>;
  handleRetryFailed: () => Promise<void>;
  handleRetrySelected: (rowIds: string[]) => Promise<void>;
  handleExport: (selectedOnly?: boolean) => void;
  handleExportToSheets: () => Promise<void>;
  detectColumnType: (header: string, values: string[]) => string;
  resetWorkbench: () => void;
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
  const abortRef = useRef<AbortController | null>(null);
  const [autoMapConfidence, setAutoMapConfidence] = useState<Record<string, MatchConfidence>>({});
  const [sheetsAvailable, setSheetsAvailable] = useState(false);
  const [exportingSheet, setExportingSheet] = useState(false);

  // Load functions + check sheets availability
  useEffect(() => {
    fetchFunctions().then(res => {
      setFunctions(res.functions);
      setFunctionsByFolder(res.by_folder);
    }).catch(() => {});
    fetchSheetsStatus()
      .then(res => setSheetsAvailable(res.available))
      .catch(() => setSheetsAvailable(false));
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

    const abort = new AbortController();
    abortRef.current = abort;

    setStep("run");
    setRunning(true);
    const totalRows = csvData.rows.length;
    setProgress({ done: 0, total: totalRows });

    const initialResults: ResultRow[] = csvData.rows.map((_, i) => ({
      rowIndex: i,
      status: "pending" as RowStatus,
      input: {},
      output: null,
      error: null,
    }));
    setResults(initialResults);

    // Build all inputs
    const allInputs: Record<string, unknown>[] = csvData.rows.map((row) => {
      const input: Record<string, unknown> = {};
      for (const mapping of mappings) {
        input[mapping.functionInput] = row[mapping.csvColumn];
      }
      return input;
    });

    // Local mode: use batch execution (N rows per claude --print call)
    if (isLocalExecutionMode()) {
      // Mark all as running
      setResults(prev => prev.map((r, i) => ({
        ...r, status: "running" as RowStatus, input: allInputs[i],
      })));

      const BATCH_SIZE = 5;
      let completedCount = 0;

      for (let batchStart = 0; batchStart < allInputs.length; batchStart += BATCH_SIZE) {
        if (abort.signal.aborted) break;

        const batchRows = allInputs.slice(batchStart, batchStart + BATCH_SIZE);

        try {
          const batchResult = await executeFunctionBatch(
            selectedFunction.id,
            batchRows,
            { batchSize: BATCH_SIZE },
          );

          for (const br of batchResult.results) {
            const globalIdx = batchStart + br.rowIndex;
            if (br.error || !br.output) {
              setResults(prev => prev.map((r, idx) =>
                idx === globalIdx ? { ...r, status: "error" as RowStatus, error: br.error || "No output" } : r
              ));
            } else {
              setResults(prev => prev.map((r, idx) =>
                idx === globalIdx ? { ...r, status: "done" as RowStatus, output: br.output } : r
              ));
            }
            completedCount++;
            setProgress({ done: completedCount, total: totalRows });
          }
        } catch (e) {
          // Entire batch failed — mark all rows in batch as error
          for (let i = 0; i < batchRows.length; i++) {
            const globalIdx = batchStart + i;
            setResults(prev => prev.map((r, idx) =>
              idx === globalIdx ? { ...r, status: "error" as RowStatus, error: e instanceof Error ? e.message : "Batch failed" } : r
            ));
            completedCount++;
            setProgress({ done: completedCount, total: totalRows });
          }
        }
      }

      abortRef.current = null;
      setRunning(false);
      setStep("results");
      return;
    }

    // Remote mode: individual calls with concurrency control
    let completedCount = 0;
    const MAX_CONCURRENT = 5;
    let active = 0;
    const waiting: (() => void)[] = [];
    const limit = async <T,>(fn: () => Promise<T>): Promise<T> => {
      if (active >= MAX_CONCURRENT) {
        await new Promise<void>(resolve => waiting.push(resolve));
      }
      active++;
      try { return await fn(); }
      finally { active--; waiting.shift()?.(); }
    };

    const promises = allInputs.map((input, i) =>
      limit(async () => {
        if (abort.signal.aborted) return;

        setResults(prev => prev.map((r, idx) =>
          idx === i ? { ...r, status: "running" as RowStatus, input } : r
        ));

        try {
          const result = await executeFunction(selectedFunction.id, input, { signal: abort.signal });
          if (result.error) {
            setResults(prev => prev.map((r, idx) =>
              idx === i ? { ...r, status: "error" as RowStatus, error: String(result.error_message || "Unknown error") } : r
            ));
          } else {
            setResults(prev => prev.map((r, idx) =>
              idx === i ? { ...r, status: "done" as RowStatus, output: result } : r
            ));
          }
        } catch (e) {
          if (abort.signal.aborted) return;
          setResults(prev => prev.map((r, idx) =>
            idx === i ? { ...r, status: "error" as RowStatus, error: e instanceof Error ? e.message : "Network error" } : r
          ));
        }

        completedCount++;
        setProgress({ done: completedCount, total: totalRows });
      })
    );

    await Promise.all(promises);
    abortRef.current = null;
    setRunning(false);
    setStep("results");
  }, [csvData, selectedFunction, mappings]);

  const handleRetryFailed = useCallback(async () => {
    if (!csvData || !selectedFunction) return;

    const abort = new AbortController();
    abortRef.current = abort;
    setRunning(true);

    const failedIndices = results.filter(r => r.status === "error").map(r => r.rowIndex);

    const MAX_CONCURRENT = 5;
    let active = 0;
    const waiting: (() => void)[] = [];
    const limit = async <T,>(fn: () => Promise<T>): Promise<T> => {
      if (active >= MAX_CONCURRENT) {
        await new Promise<void>(resolve => waiting.push(resolve));
      }
      active++;
      try { return await fn(); }
      finally { active--; waiting.shift()?.(); }
    };

    const promises = failedIndices.map(i =>
      limit(async () => {
        if (abort.signal.aborted) return;

        const row = csvData.rows[i];
        const input: Record<string, unknown> = {};
        for (const mapping of mappings) {
          input[mapping.functionInput] = row[mapping.csvColumn];
        }

        setResults(prev => prev.map((r, idx) =>
          idx === i ? { ...r, status: "running" as RowStatus, input } : r
        ));

        try {
          const result = await executeFunction(selectedFunction.id, input, { signal: abort.signal });
          if (result.error) {
            setResults(prev => prev.map((r, idx) =>
              idx === i ? { ...r, status: "error" as RowStatus, error: String(result.error_message || "Unknown error") } : r
            ));
          } else {
            setResults(prev => prev.map((r, idx) =>
              idx === i ? { ...r, status: "done" as RowStatus, output: result } : r
            ));
          }
        } catch (e) {
          if (abort.signal.aborted) return;
          setResults(prev => prev.map((r, idx) =>
            idx === i ? { ...r, status: "error" as RowStatus, error: e instanceof Error ? e.message : "Network error" } : r
          ));
        }
      })
    );

    await Promise.all(promises);
    abortRef.current = null;
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

  // Convert ResultRow[] → SpreadsheetRow[] for the shared spreadsheet component
  const spreadsheetRows: SpreadsheetRow[] = useMemo(() => {
    return results.map((r) => ({
      _id: String(r.rowIndex),
      _status: r.status,
      _error: r.error,
      _original: csvData?.rows[r.rowIndex] || {},
      _result: r.output,
    }));
  }, [results, csvData]);

  // Retry specific rows by their spreadsheet IDs (row indices as strings)
  const handleRetrySelected = useCallback(async (rowIds: string[]) => {
    if (!csvData || !selectedFunction) return;

    const abort = new AbortController();
    abortRef.current = abort;
    setRunning(true);

    const indices = rowIds.map(Number);
    const MAX_CONCURRENT = 5;
    let active = 0;
    const waiting: (() => void)[] = [];
    const limit = async <T,>(fn: () => Promise<T>): Promise<T> => {
      if (active >= MAX_CONCURRENT) {
        await new Promise<void>(resolve => waiting.push(resolve));
      }
      active++;
      try { return await fn(); }
      finally { active--; waiting.shift()?.(); }
    };

    const promises = indices.map(i =>
      limit(async () => {
        if (abort.signal.aborted) return;

        const row = csvData.rows[i];
        const input: Record<string, unknown> = {};
        for (const mapping of mappings) {
          input[mapping.functionInput] = row[mapping.csvColumn];
        }

        setResults(prev => prev.map((r, idx) =>
          idx === i ? { ...r, status: "running" as RowStatus, input } : r
        ));

        try {
          const result = await executeFunction(selectedFunction.id, input, { signal: abort.signal });
          if (result.error) {
            setResults(prev => prev.map((r, idx) =>
              idx === i ? { ...r, status: "error" as RowStatus, error: String(result.error_message || "Unknown error") } : r
            ));
          } else {
            setResults(prev => prev.map((r, idx) =>
              idx === i ? { ...r, status: "done" as RowStatus, output: result } : r
            ));
          }
        } catch (e) {
          if (abort.signal.aborted) return;
          setResults(prev => prev.map((r, idx) =>
            idx === i ? { ...r, status: "error" as RowStatus, error: e instanceof Error ? e.message : "Network error" } : r
          ));
        }
      })
    );

    await Promise.all(promises);
    abortRef.current = null;
    setRunning(false);
  }, [csvData, selectedFunction, mappings]);

  const handleExportToSheets = useCallback(async () => {
    if (!selectedFunction || results.length === 0) return;

    const doneRows = results.filter(r => r.status === "done" && r.output);
    if (doneRows.length === 0) {
      toast.error("No successful rows to export");
      return;
    }

    setExportingSheet(true);
    try {
      const inputs = doneRows.map(r => r.input);
      const outputs = doneRows.map(r => r.output as Record<string, unknown>);
      const res = await exportRunToSheets(selectedFunction.id, {
        inputs,
        outputs,
        description: `Batch run: ${doneRows.length} rows`,
      });
      toast.success("Sheet created", {
        action: {
          label: "Open",
          onClick: () => window.open(res.url, "_blank"),
        },
      });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to export to Google Sheets");
    } finally {
      setExportingSheet(false);
    }
  }, [selectedFunction, results]);

  const detectColumnType = useCallback((header: string, values: string[]) => {
    const sample = values.filter(v => v).slice(0, 10);
    if (sample.every(v => /^[\w.+-]+@[\w.-]+\.\w+$/.test(v))) return "email";
    if (sample.every(v => /^https?:\/\//.test(v))) return "url";
    if (sample.every(v => !isNaN(Number(v)))) return "number";
    return "string";
  }, []);

  const resetWorkbench = useCallback(() => {
    abortRef.current?.abort();
    abortRef.current = null;
    setRunning(false);
    setStep("upload");
    setResults([]);
    setCsvData(null);
    setMappings([]);
    setSelectedFunction(null);
    setAutoMapConfidence({});
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
    fileInputRef,
    autoMapConfidence,
    spreadsheetRows,
    sheetsAvailable,
    exportingSheet,
    handleFileUpload,
    handleDrop,
    handleSelectFunction,
    handleMapColumn,
    handleClearMapping,
    handleRun,
    handleRetryFailed,
    handleRetrySelected,
    handleExport,
    handleExportToSheets,
    detectColumnType,
    resetWorkbench,
    canRun,
    successRate,
    errorCount,
    doneCount,
  };
}
