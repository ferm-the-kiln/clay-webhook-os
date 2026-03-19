"use client";

import { useState, useEffect, useCallback, useRef, Suspense } from "react";
import { useSearchParams } from "next/navigation";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import {
  fetchFunctions,
  fetchFunction,
} from "@/lib/api";
import type { FunctionDefinition } from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  Upload,
  FileSpreadsheet,
  ArrowRight,
  Play,
  Download,
  RefreshCw,
  Check,
  X,
  Loader2,
  AlertCircle,
  ChevronDown,
  Blocks,
} from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { toast } from "sonner";
import Papa from "papaparse";

type WorkbenchStep = "upload" | "map" | "run" | "results";
type RowStatus = "pending" | "running" | "done" | "error";

interface CsvData {
  fileName: string;
  headers: string[];
  rows: Record<string, string>[];
  totalRows: number;
}

interface ColumnMapping {
  csvColumn: string;
  functionInput: string;
}

interface ResultRow {
  rowIndex: number;
  status: RowStatus;
  input: Record<string, unknown>;
  output: Record<string, unknown> | null;
  error: string | null;
}

export default function WorkbenchPageWrapper() {
  return (
    <Suspense fallback={
      <div className="flex flex-col h-full">
        <Header title="Workbench" />
        <div className="flex-1 flex items-center justify-center text-clay-300">Loading...</div>
      </div>
    }>
      <WorkbenchPage />
    </Suspense>
  );
}

function WorkbenchPage() {
  const searchParams = useSearchParams();
  const preselectedFunc = searchParams.get("function");

  const [step, setStep] = useState<WorkbenchStep>("upload");
  const [csvData, setCsvData] = useState<CsvData | null>(null);
  const [selectedFunction, setSelectedFunction] = useState<FunctionDefinition | null>(null);
  const [functions, setFunctions] = useState<FunctionDefinition[]>([]);
  const [mappings, setMappings] = useState<ColumnMapping[]>([]);
  const [results, setResults] = useState<ResultRow[]>([]);
  const [running, setRunning] = useState(false);
  const [progress, setProgress] = useState({ done: 0, total: 0 });
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [expandedCell, setExpandedCell] = useState<{ row: number; col: string } | null>(null);
  const [sortColumn, setSortColumn] = useState<string | null>(null);
  const [sortDir, setSortDir] = useState<"asc" | "desc">("asc");
  const [statusFilter, setStatusFilter] = useState<RowStatus | "all">("all");

  // Load functions for picker
  useEffect(() => {
    fetchFunctions().then(res => setFunctions(res.functions)).catch(() => {});
  }, []);

  // Pre-select function from URL param
  useEffect(() => {
    if (preselectedFunc && !selectedFunction) {
      fetchFunction(preselectedFunc)
        .then(f => setSelectedFunction(f))
        .catch(() => {});
    }
  }, [preselectedFunc, selectedFunction]);

  // Handle CSV upload
  const handleFileUpload = (file: File) => {
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

        // Auto-map columns if a function is selected
        if (selectedFunction) {
          autoMapColumns(headers, selectedFunction);
        }

        toast.success(`Loaded ${rows.length} rows from ${file.name}`);
      },
      error: () => {
        toast.error("Failed to parse CSV file");
      },
    });
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    const file = e.dataTransfer.files[0];
    if (file && file.name.endsWith(".csv")) {
      handleFileUpload(file);
    } else {
      toast.error("Please upload a .csv file");
    }
  };

  // Auto-map columns by name similarity
  const autoMapColumns = (csvHeaders: string[], func: FunctionDefinition) => {
    const newMappings: ColumnMapping[] = [];
    for (const input of func.inputs) {
      const exactMatch = csvHeaders.find(h => h.toLowerCase() === input.name.toLowerCase());
      const fuzzyMatch = csvHeaders.find(h =>
        h.toLowerCase().includes(input.name.toLowerCase()) ||
        input.name.toLowerCase().includes(h.toLowerCase())
      );
      const match = exactMatch || fuzzyMatch;
      if (match) {
        newMappings.push({ csvColumn: match, functionInput: input.name });
      }
    }
    setMappings(newMappings);
  };

  const handleSelectFunction = (func: FunctionDefinition) => {
    setSelectedFunction(func);
    if (csvData) {
      autoMapColumns(csvData.headers, func);
    }
  };

  const handleMapColumn = (csvCol: string, funcInput: string) => {
    setMappings(prev => {
      const filtered = prev.filter(m => m.functionInput !== funcInput);
      return [...filtered, { csvColumn: csvCol, functionInput: funcInput }];
    });
  };

  const canRun = csvData && selectedFunction && mappings.length > 0;

  // Execute function against rows
  const handleRun = async () => {
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

    // Process rows sequentially (could be batched later)
    for (let i = 0; i < totalRows; i++) {
      const row = csvData.rows[i];
      // Build input from mappings
      const input: Record<string, unknown> = {};
      for (const mapping of mappings) {
        input[mapping.functionInput] = row[mapping.csvColumn];
      }

      newResults[i].status = "running";
      newResults[i].input = input;
      setResults([...newResults]);

      try {
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://clay.nomynoms.com";
        const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";
        const res = await fetch(`${API_URL}/webhook`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
          body: JSON.stringify({
            function: selectedFunction.id,
            data: input,
          }),
        });
        const result = await res.json();

        if (result.error) {
          newResults[i].status = "error";
          newResults[i].error = result.error_message || "Unknown error";
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
  };

  // Retry failed rows
  const handleRetryFailed = async () => {
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
        const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://clay.nomynoms.com";
        const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";
        const res = await fetch(`${API_URL}/webhook`, {
          method: "POST",
          headers: { "Content-Type": "application/json", "X-API-Key": API_KEY },
          body: JSON.stringify({
            function: selectedFunction.id,
            data: input,
          }),
        });
        const result = await res.json();
        if (result.error) {
          newResults[i].status = "error";
          newResults[i].error = result.error_message || "Unknown error";
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
  };

  // Export results
  const handleExport = (selectedOnly?: boolean) => {
    const rowsToExport = selectedOnly
      ? results.filter(r => r.status === "done")
      : results;

    if (rowsToExport.length === 0) {
      toast.error("No rows to export");
      return;
    }

    // Build export data
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
  };

  // Get sorted/filtered results
  const getDisplayResults = () => {
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
  };

  // Detect column types
  const detectColumnType = (header: string, values: string[]) => {
    const sample = values.filter(v => v).slice(0, 10);
    if (sample.every(v => /^[\w.+-]+@[\w.-]+\.\w+$/.test(v))) return "email";
    if (sample.every(v => /^https?:\/\//.test(v))) return "url";
    if (sample.every(v => !isNaN(Number(v)))) return "number";
    return "string";
  };

  return (
    <div className="flex flex-col h-full">
      <Header title="Workbench" />
      <div className="flex-1 overflow-auto p-4 md:p-6 pb-20 md:pb-6">

        {/* Step 1: Upload */}
        {step === "upload" && (
          <div className="space-y-6">
            {/* Function picker */}
            <div>
              <label className="text-xs font-medium text-clay-300 mb-2 block">Function</label>
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button
                    variant="outline"
                    className="w-full sm:w-auto justify-between border-clay-600 text-clay-100 bg-clay-800"
                  >
                    <span className="flex items-center gap-2">
                      <Blocks className="h-4 w-4 text-clay-400" />
                      {selectedFunction ? selectedFunction.name : "Select a function..."}
                    </span>
                    <ChevronDown className="h-4 w-4 text-clay-400" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent className="bg-clay-800 border-clay-600 max-h-64 overflow-auto">
                  {functions.map(f => (
                    <DropdownMenuItem
                      key={f.id}
                      onClick={() => handleSelectFunction(f)}
                      className={cn(
                        "cursor-pointer",
                        selectedFunction?.id === f.id && "bg-kiln-teal/10 text-kiln-teal"
                      )}
                    >
                      <div>
                        <div className="text-sm">{f.name}</div>
                        {f.description && <div className="text-xs text-clay-400 line-clamp-1">{f.description}</div>}
                      </div>
                    </DropdownMenuItem>
                  ))}
                  {functions.length === 0 && (
                    <div className="px-3 py-2 text-xs text-clay-400">No functions available</div>
                  )}
                </DropdownMenuContent>
              </DropdownMenu>
            </div>

            {/* CSV Upload Zone */}
            <div
              onDrop={handleDrop}
              onDragOver={(e) => e.preventDefault()}
              onClick={() => fileInputRef.current?.click()}
              className={cn(
                "border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors",
                csvData
                  ? "border-kiln-teal/30 bg-kiln-teal/5"
                  : "border-clay-600 hover:border-clay-500 hover:bg-clay-800/50"
              )}
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={(e) => {
                  const file = e.target.files?.[0];
                  if (file) handleFileUpload(file);
                }}
              />
              {csvData ? (
                <div className="space-y-2">
                  <FileSpreadsheet className="h-10 w-10 text-kiln-teal mx-auto" />
                  <div className="text-sm font-medium text-clay-100">{csvData.fileName}</div>
                  <div className="text-xs text-clay-300">
                    {csvData.totalRows} rows, {csvData.headers.length} columns
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); setCsvData(null); setMappings([]); }}
                    className="text-xs text-clay-400 hover:text-clay-200 underline"
                  >
                    Upload different file
                  </button>
                </div>
              ) : (
                <div className="space-y-2">
                  <Upload className="h-10 w-10 text-clay-400 mx-auto" />
                  <div className="text-sm text-clay-200">Drag and drop a CSV file here</div>
                  <div className="text-xs text-clay-400">or click to browse</div>
                </div>
              )}
            </div>

            {/* Preview table */}
            {csvData && (
              <div>
                <h3 className="text-sm font-medium text-clay-200 mb-2">Preview (first 5 rows)</h3>
                <div className="overflow-x-auto rounded-lg border border-clay-600">
                  <table className="w-full text-xs">
                    <thead>
                      <tr className="bg-clay-800">
                        {csvData.headers.map(h => (
                          <th key={h} className="px-3 py-2 text-left text-clay-300 font-medium whitespace-nowrap">
                            <div>{h}</div>
                            <div className="text-[10px] text-clay-500 font-normal">
                              {detectColumnType(h, csvData.rows.map(r => r[h]))}
                            </div>
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {csvData.rows.slice(0, 5).map((row, i) => (
                        <tr key={i} className="border-t border-clay-700">
                          {csvData.headers.map(h => (
                            <td key={h} className="px-3 py-1.5 text-clay-200 whitespace-nowrap max-w-[200px] truncate">
                              {row[h]}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Column mapping */}
            {csvData && selectedFunction && (
              <div>
                <h3 className="text-sm font-medium text-clay-200 mb-3">Column Mapping</h3>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  {/* CSV columns */}
                  <div>
                    <div className="text-xs text-clay-400 mb-2 uppercase tracking-wider">CSV Columns</div>
                    <div className="space-y-1">
                      {csvData.headers.map(h => {
                        const mapped = mappings.find(m => m.csvColumn === h);
                        return (
                          <div
                            key={h}
                            className={cn(
                              "px-3 py-2 rounded-md text-xs border",
                              mapped
                                ? "border-kiln-teal/30 bg-kiln-teal/5 text-kiln-teal"
                                : "border-clay-600 text-clay-300"
                            )}
                          >
                            {h}
                            {mapped && (
                              <span className="ml-2 text-clay-400">
                                <ArrowRight className="h-3 w-3 inline" /> {mapped.functionInput}
                              </span>
                            )}
                          </div>
                        );
                      })}
                    </div>
                  </div>

                  {/* Function inputs */}
                  <div>
                    <div className="text-xs text-clay-400 mb-2 uppercase tracking-wider">Function Inputs</div>
                    <div className="space-y-1">
                      {selectedFunction.inputs.map(input => {
                        const mapped = mappings.find(m => m.functionInput === input.name);
                        return (
                          <div key={input.name}>
                            <DropdownMenu>
                              <DropdownMenuTrigger asChild>
                                <button
                                  className={cn(
                                    "w-full text-left px-3 py-2 rounded-md text-xs border transition-colors",
                                    !mapped && input.required
                                      ? "border-red-500/30 bg-red-500/5 text-red-400"
                                      : mapped
                                        ? "border-kiln-teal/30 bg-kiln-teal/5 text-kiln-teal"
                                        : "border-clay-600 text-clay-400"
                                  )}
                                >
                                  <span className="font-medium">{input.name}</span>
                                  {input.required && !mapped && <span className="ml-1 text-red-400">*</span>}
                                  {mapped && <span className="ml-2 text-clay-400">({mapped.csvColumn})</span>}
                                  {!mapped && <span className="ml-2 text-clay-500">Click to map</span>}
                                </button>
                              </DropdownMenuTrigger>
                              <DropdownMenuContent className="bg-clay-800 border-clay-600 max-h-48 overflow-auto">
                                {csvData.headers.map(h => (
                                  <DropdownMenuItem
                                    key={h}
                                    onClick={() => handleMapColumn(h, input.name)}
                                    className="text-xs"
                                  >
                                    {h}
                                  </DropdownMenuItem>
                                ))}
                              </DropdownMenuContent>
                            </DropdownMenu>
                          </div>
                        );
                      })}
                    </div>
                  </div>
                </div>
              </div>
            )}

            {/* Run button */}
            {canRun && (
              <div className="flex justify-end">
                <Button
                  onClick={handleRun}
                  className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
                >
                  <Play className="h-4 w-4 mr-2" />
                  Run ({csvData!.totalRows} rows)
                </Button>
              </div>
            )}
          </div>
        )}

        {/* Step 2: Running */}
        {step === "run" && running && (
          <div className="flex flex-col items-center justify-center py-20 gap-4">
            <Loader2 className="h-10 w-10 text-kiln-teal animate-spin" />
            <div className="text-lg font-semibold text-clay-100">
              Processing...
            </div>
            <div className="text-sm text-clay-300">
              {progress.done}/{progress.total} rows processed
            </div>
            <div className="w-64 h-2 bg-clay-700 rounded-full overflow-hidden">
              <div
                className="h-full bg-kiln-teal rounded-full transition-all duration-300"
                style={{ width: `${(progress.done / progress.total) * 100}%` }}
              />
            </div>
          </div>
        )}

        {/* Step 3: Results */}
        {(step === "results" || (step === "run" && !running)) && results.length > 0 && (
          <div className="space-y-4">
            {/* Results toolbar */}
            <div className="flex items-center justify-between flex-wrap gap-2">
              <div className="flex items-center gap-3 text-xs text-clay-300">
                <span className="flex items-center gap-1">
                  <Check className="h-3 w-3 text-green-400" />
                  {results.filter(r => r.status === "done").length} done
                </span>
                <span className="flex items-center gap-1">
                  <X className="h-3 w-3 text-red-400" />
                  {results.filter(r => r.status === "error").length} errors
                </span>
                {results.some(r => r.status === "pending" || r.status === "running") && (
                  <span className="flex items-center gap-1">
                    <Loader2 className="h-3 w-3 animate-spin text-clay-400" />
                    {results.filter(r => r.status === "pending" || r.status === "running").length} pending
                  </span>
                )}
              </div>
              <div className="flex items-center gap-2">
                {/* Status filter */}
                <DropdownMenu>
                  <DropdownMenuTrigger asChild>
                    <Button variant="outline" size="sm" className="border-clay-600 text-clay-300 text-xs">
                      Filter: {statusFilter === "all" ? "All" : statusFilter}
                    </Button>
                  </DropdownMenuTrigger>
                  <DropdownMenuContent className="bg-clay-800 border-clay-600">
                    {(["all", "done", "error", "pending", "running"] as const).map(s => (
                      <DropdownMenuItem key={s} onClick={() => setStatusFilter(s)} className="text-xs">
                        {s === "all" ? "All" : s}
                      </DropdownMenuItem>
                    ))}
                  </DropdownMenuContent>
                </DropdownMenu>

                {results.some(r => r.status === "error") && (
                  <Button
                    variant="outline"
                    size="sm"
                    onClick={handleRetryFailed}
                    disabled={running}
                    className="border-clay-600 text-clay-300 text-xs"
                  >
                    <RefreshCw className="h-3 w-3 mr-1" />
                    Retry Failed
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleExport()}
                  className="border-clay-600 text-clay-300 text-xs"
                >
                  <Download className="h-3 w-3 mr-1" />
                  Export All
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => handleExport(true)}
                  className="border-clay-600 text-clay-300 text-xs"
                >
                  Export Successful
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => { setStep("upload"); setResults([]); setCsvData(null); setMappings([]); setSelectedFunction(null); }}
                  className="border-clay-600 text-clay-300 text-xs"
                >
                  New Run
                </Button>
              </div>
            </div>

            {/* Results table */}
            <div className="overflow-x-auto rounded-lg border border-clay-600">
              <table className="w-full text-xs">
                <thead>
                  <tr className="bg-clay-800">
                    <th className="px-3 py-2 text-left text-clay-300 font-medium w-12">#</th>
                    <th className="px-3 py-2 text-left text-clay-300 font-medium w-16">Status</th>
                    {/* Input columns */}
                    {mappings.map(m => (
                      <th
                        key={`in-${m.functionInput}`}
                        className="px-3 py-2 text-left text-clay-300 font-medium whitespace-nowrap cursor-pointer hover:text-clay-100"
                        onClick={() => {
                          if (sortColumn === m.functionInput) {
                            setSortDir(d => d === "asc" ? "desc" : "asc");
                          } else {
                            setSortColumn(m.functionInput);
                            setSortDir("asc");
                          }
                        }}
                      >
                        {m.functionInput}
                        {sortColumn === m.functionInput && (sortDir === "asc" ? " ↑" : " ↓")}
                      </th>
                    ))}
                    {/* Output columns */}
                    {selectedFunction?.outputs.map(o => (
                      <th
                        key={`out-${o.key}`}
                        className="px-3 py-2 text-left text-kiln-teal font-medium whitespace-nowrap cursor-pointer hover:text-kiln-teal-light"
                        onClick={() => {
                          if (sortColumn === o.key) {
                            setSortDir(d => d === "asc" ? "desc" : "asc");
                          } else {
                            setSortColumn(o.key);
                            setSortDir("asc");
                          }
                        }}
                      >
                        {o.key}
                        {sortColumn === o.key && (sortDir === "asc" ? " ↑" : " ↓")}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {getDisplayResults().map(row => (
                    <tr key={row.rowIndex} className="border-t border-clay-700 hover:bg-clay-800/50">
                      <td className="px-3 py-1.5 text-clay-400">{row.rowIndex + 1}</td>
                      <td className="px-3 py-1.5">
                        {row.status === "done" && <Check className="h-3.5 w-3.5 text-green-400" />}
                        {row.status === "error" && (
                          <span className="flex items-center gap-1 text-red-400" title={row.error || ""}>
                            <AlertCircle className="h-3.5 w-3.5" />
                          </span>
                        )}
                        {row.status === "running" && <Loader2 className="h-3.5 w-3.5 text-kiln-teal animate-spin" />}
                        {row.status === "pending" && <span className="h-2 w-2 rounded-full bg-clay-500 inline-block" />}
                      </td>
                      {/* Input values */}
                      {mappings.map(m => (
                        <td
                          key={`in-${m.functionInput}`}
                          className="px-3 py-1.5 text-clay-200 max-w-[200px] truncate cursor-pointer"
                          onClick={() => setExpandedCell(
                            expandedCell?.row === row.rowIndex && expandedCell?.col === m.functionInput
                              ? null
                              : { row: row.rowIndex, col: m.functionInput }
                          )}
                        >
                          {expandedCell?.row === row.rowIndex && expandedCell?.col === m.functionInput ? (
                            <div className="whitespace-pre-wrap break-words max-w-md">
                              {String(row.input[m.functionInput] ?? "")}
                            </div>
                          ) : (
                            String(row.input[m.functionInput] ?? "")
                          )}
                        </td>
                      ))}
                      {/* Output values */}
                      {selectedFunction?.outputs.map(o => (
                        <td
                          key={`out-${o.key}`}
                          className={cn(
                            "px-3 py-1.5 max-w-[200px] truncate cursor-pointer",
                            row.status === "error" ? "text-red-400" : "text-clay-100"
                          )}
                          onClick={() => setExpandedCell(
                            expandedCell?.row === row.rowIndex && expandedCell?.col === o.key
                              ? null
                              : { row: row.rowIndex, col: o.key }
                          )}
                        >
                          {row.status === "error" ? (
                            row.error
                          ) : expandedCell?.row === row.rowIndex && expandedCell?.col === o.key ? (
                            <div className="whitespace-pre-wrap break-words max-w-md">
                              {typeof row.output?.[o.key] === "object"
                                ? JSON.stringify(row.output?.[o.key], null, 2)
                                : String(row.output?.[o.key] ?? "")}
                            </div>
                          ) : (
                            typeof row.output?.[o.key] === "object"
                              ? JSON.stringify(row.output?.[o.key])
                              : String(row.output?.[o.key] ?? "")
                          )}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
