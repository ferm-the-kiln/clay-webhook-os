"use client";

import { useState, useEffect, useRef } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Play,
  Clipboard,
  ClipboardPaste,
  Loader2,
  CheckCircle2,
  XCircle,
  Copy,
  Check,
  Clock,
  Zap,
  AlertTriangle,
  Upload,
  FileSpreadsheet,
  X,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import Papa from "papaparse";
import type { FunctionDefinition, FunctionInput, StepTrace, LogEntry, FunnelStage } from "@/lib/types";
import { OutputRenderer } from "@/components/output/output-renderer";
import { ExecutionTrace } from "./execution-trace";
import { ExecutionHistoryPanel } from "./execution-history";
import {
  prepareConsolidatedPrompt,
  queueLocalJob,
  submitLocalResult,
  fetchLocalJob,
  fetchExecution,
  fetchJobLogs,
  streamFunctionExecution,
  streamBatchExecution,
} from "@/lib/api";

interface FunctionRunPanelProps {
  func: FunctionDefinition;
  inputs: FunctionInput[];
}

export function FunctionRunPanel({ func, inputs }: FunctionRunPanelProps) {
  // Input state
  const [testInputs, setTestInputs] = useState<Record<string, string>>({});
  const testInputsRef = useRef<Record<string, string>>({});
  testInputsRef.current = testInputs;

  // Execution state
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [streamingTrace, setStreamingTrace] = useState<StepTrace[]>([]);
  const abortRef = useRef<AbortController | null>(null);

  // Local execution state
  const [copyingPrompt, setCopyingPrompt] = useState(false);
  const [localJobId, setLocalJobId] = useState<string | null>(null);
  const [localWaiting, setLocalWaiting] = useState(false);
  const [pasteMode, setPasteMode] = useState(false);
  const [pastedJson, setPastedJson] = useState("");
  const [executionLogs, setExecutionLogs] = useState<LogEntry[]>([]);
  const [elapsed, setElapsed] = useState(0);
  const logScrollRef = useRef<HTMLDivElement | null>(null);

  // Batch state
  const [csvRows, setCsvRows] = useState<Record<string, string>[] | null>(null);
  const [csvFileName, setCsvFileName] = useState("");
  const [batchRunning, setBatchRunning] = useState(false);
  const [batchProgress, setBatchProgress] = useState({ done: 0, total: 0, errors: 0 });
  const [batchResults, setBatchResults] = useState<Array<{ input: Record<string, string>; output: Record<string, unknown> | null; error: string | null }>>([]);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  // Funnel state (for batch pipeline with gates)
  const [funnelStages, setFunnelStages] = useState<FunnelStage[]>([]);
  const hasGates = func.steps.some((s) => s.tool === "gate");

  // UI state
  const [activeTab, setActiveTab] = useState<"output" | "trace" | "raw" | "history" | "funnel">("output");
  const [copied, setCopied] = useState(false);

  // Auto-switch to output when result arrives
  useEffect(() => {
    if (result) setActiveTab("output");
  }, [result]);

  // Poll for logs + job status (combined into one poll)
  useEffect(() => {
    if (!localJobId || !localWaiting) return;
    let logIndex = 0;
    let lastLogTime = Date.now();
    const interval = setInterval(async () => {
      try {
        const { logs, status } = await fetchJobLogs(localJobId, logIndex);
        if (logs.length > 0) {
          setExecutionLogs((prev) => [...prev, ...logs]);
          logIndex += logs.length;
          lastLogTime = Date.now();
          // Auto-scroll
          setTimeout(() => logScrollRef.current?.scrollTo({ top: logScrollRef.current.scrollHeight, behavior: "smooth" }), 50);
        }

        if (status === "completed" || status === "failed") {
          setLocalWaiting(false);
          if (status === "completed") {
            // Fetch result from execution history
            try {
              const job = await fetchLocalJob(localJobId);
              if (job.exec_id) {
                const exec = await fetchExecution(func.id, job.exec_id);
                if (exec?.outputs) {
                  setResult(exec.outputs as Record<string, unknown>);
                  toast.success(`Done in ${((exec.duration_ms || 0) / 1000).toFixed(1)}s`);
                } else {
                  setActiveTab("history");
                }
              } else {
                setActiveTab("history");
              }
            } catch {
              setActiveTab("history");
            }
          } else {
            toast.error("Local execution failed");
          }
          setLocalJobId(null);
          clearInterval(interval);
          return;
        }

        // Stall detection: no logs for 90s while still "running"
        if (status === "running" && Date.now() - lastLogTime > 90000) {
          setExecutionLogs((prev) => [
            ...prev,
            { elapsed_ms: 0, type: "error" as const, message: "No activity for 90s — execution may have stalled. Check daemon logs." },
          ]);
          lastLogTime = Date.now(); // Reset so warning doesn't spam
        }
      } catch {
        // keep polling
      }
    }, 1000);
    return () => clearInterval(interval);
  }, [localJobId, localWaiting, func.id]);

  // Elapsed timer while executing
  useEffect(() => {
    if (!localWaiting) { setElapsed(0); return; }
    const start = Date.now();
    const tick = setInterval(() => setElapsed(Math.floor((Date.now() - start) / 1000)), 1000);
    return () => clearInterval(tick);
  }, [localWaiting]);

  // Keyboard shortcut: Cmd+Enter to run locally
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter" && !running && !localWaiting) {
        e.preventDefault();
        handleRunLocally();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [running, localWaiting, func]);

  // ── Handlers ──────────────────────────────────────────

  const handleCopyPrompt = async () => {
    setCopyingPrompt(true);
    try {
      const res = await prepareConsolidatedPrompt(func.id, testInputs);
      await navigator.clipboard.writeText(res.prompt);
      toast.success(`Prompt copied (${(res.prompt.length / 1000).toFixed(1)}k chars) — paste into Claude Code`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to copy prompt");
    } finally {
      setCopyingPrompt(false);
    }
  };

  const handleRunLocally = async () => {
    setLocalWaiting(true);
    setResult(null);
    setExecutionLogs([]);
    try {
      const job = await queueLocalJob(func.id, testInputs);
      setLocalJobId(job.job_id);
      toast.success("Executing locally via Claude Code...");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to queue job");
      setLocalWaiting(false);
    }
  };

  const handleSubmitPasted = async () => {
    if (!localJobId) return;
    try {
      const parsed = JSON.parse(pastedJson);
      const response = await submitLocalResult(func.id, localJobId, parsed);
      toast.success(`Result saved: ${response.exec_id}`);
      setResult(parsed);
      setPasteMode(false);
      setPastedJson("");
      setLocalJobId(null);
      setLocalWaiting(false);
    } catch (e) {
      if (e instanceof SyntaxError) {
        toast.error("Invalid JSON — check your pasted result");
      } else {
        toast.error(e instanceof Error ? e.message : "Failed to submit result");
      }
    }
  };

  const handleCopyResult = async () => {
    if (!cleanOutput) return;
    await navigator.clipboard.writeText(JSON.stringify(cleanOutput, null, 2));
    setCopied(true);
    toast.success("Copied");
    setTimeout(() => setCopied(false), 2000);
  };

  // ── Batch handlers ────────────────────────────────────

  const handleCsvUpload = (file: File) => {
    Papa.parse(file, {
      header: true,
      skipEmptyLines: true,
      complete: (results) => {
        const rows = results.data as Record<string, string>[];
        if (rows.length === 0) {
          toast.error("CSV is empty");
          return;
        }
        setCsvRows(rows);
        setCsvFileName(file.name);
        toast.success(`Loaded ${rows.length} rows from ${file.name}`);
      },
      error: (err) => toast.error(`CSV parse error: ${err.message}`),
    });
  };

  const handleBatchRun = async () => {
    if (!csvRows || csvRows.length === 0) return;
    setBatchRunning(true);
    setBatchResults([]);
    setFunnelStages([]);
    setBatchProgress({ done: 0, total: csvRows.length, errors: 0 });

    // If function has gates, use batch pipeline execution (server-side with funnel)
    if (hasGates) {
      await new Promise<void>((resolve) => {
        const controller = streamBatchExecution(
          func.id,
          csvRows,
          (event) => {
            if (event.type === "batch_start") {
              setBatchProgress({ done: 0, total: event.total_rows as number, errors: 0 });
            } else if (event.type === "stage_complete" || event.type === "gate_result") {
              setFunnelStages((prev) => [...prev, event as unknown as FunnelStage]);
            } else if (event.type === "chunk_complete") {
              setBatchProgress((prev) => ({ ...prev, done: event.processed as number }));
            } else if (event.type === "result") {
              const rows = (event.rows as Record<string, unknown>[]) || [];
              const results = rows.map((row) => ({
                input: row as Record<string, string>,
                output: row,
                error: (row._error as string) || null,
              }));
              setBatchResults(results);
              setBatchProgress({
                done: event.total_rows_input as number,
                total: event.total_rows_input as number,
                errors: rows.filter((r) => r._error).length,
              });
              setActiveTab("funnel");
              resolve();
            }
          },
          (err) => {
            toast.error(err);
            resolve();
          },
        );
        abortRef.current = controller;
      });
      setBatchRunning(false);
      return;
    }

    // Standard batch: process rows one by one
    const results: typeof batchResults = [];
    let errors = 0;

    for (let i = 0; i < csvRows.length; i++) {
      const row = csvRows[i];
      try {
        const output = await new Promise<Record<string, unknown>>((resolve, reject) => {
          streamFunctionExecution(
            func.id,
            row,
            () => {}, // ignore step traces for batch
            (res) => resolve(res),
            (err) => reject(new Error(err)),
          );
        });
        results.push({ input: row, output, error: null });
      } catch (e) {
        errors++;
        results.push({ input: row, output: null, error: e instanceof Error ? e.message : "Failed" });
      }
      setBatchProgress({ done: i + 1, total: csvRows.length, errors });
      setBatchResults([...results]);
    }

    setBatchRunning(false);
    toast.success(`Batch complete: ${csvRows.length - errors} success, ${errors} errors`);
  };

  const handleBatchDownload = () => {
    if (batchResults.length === 0) return;
    // Collect all keys from inputs + outputs
    const allKeys: string[] = [];
    for (const r of batchResults) {
      for (const k of Object.keys(r.input)) if (!allKeys.includes(k)) allKeys.push(k);
      if (r.output) {
        for (const k of Object.keys(r.output)) {
          if (!k.startsWith("_") && !allKeys.includes(k)) allKeys.push(k);
        }
      }
    }
    allKeys.push("_status", "_error");

    const csvContent = Papa.unparse(
      batchResults.map((r) => {
        const row: Record<string, unknown> = { ...r.input };
        if (r.output) {
          for (const [k, v] of Object.entries(r.output)) {
            if (!k.startsWith("_")) row[k] = typeof v === "object" ? JSON.stringify(v) : v;
          }
        }
        row._status = r.error ? "error" : "success";
        row._error = r.error || "";
        return row;
      }),
    );

    const blob = new Blob([csvContent], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = csvFileName.replace(".csv", "_output.csv");
    a.click();
    URL.revokeObjectURL(url);
  };

  // ── Derived state ─────────────────────────────────────

  const meta = result?._meta as Record<string, unknown> | undefined;
  const trace = meta?.trace as StepTrace[] | undefined;
  const totalDurationMs = (meta?.duration_ms as number) || 0;
  const hasTrace = trace && trace.length > 0;
  const hasError = result?.error === true;

  const cleanOutput = result
    ? Object.fromEntries(Object.entries(result).filter(([k]) => !k.startsWith("_")))
    : null;
  const fieldCount = cleanOutput ? Object.keys(cleanOutput).length : 0;
  const nullCount = cleanOutput
    ? Object.values(cleanOutput).filter((v) => v === null).length
    : 0;

  const rawWarnings = result?._warnings as string[] | undefined;
  const warnings: string[] = rawWarnings ? [...rawWarnings] : [];
  if (result && !rawWarnings) {
    const nullKeys = Object.entries(result)
      .filter(([k, v]) => v === null && !k.startsWith("_"))
      .map(([k]) => k);
    if (nullKeys.length > 0) {
      warnings.push(`${nullKeys.length} field${nullKeys.length > 1 ? "s" : ""} returned null: ${nullKeys.join(", ")}`);
    }
  }

  const hasResult = result !== null;
  const isStreaming = running && streamingTrace.length > 0;

  return (
    <Card className="border-clay-700 bg-clay-900/30">
      <CardHeader className="pb-3">
        <CardTitle className="text-base text-clay-200 flex items-center gap-2">
          <Play className="h-4 w-4 text-kiln-teal" />
          Run
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-4">
        {/* Inputs */}
        {inputs.length > 0 && (
          <div className="space-y-2.5">
            {inputs.map((inp) => (
              <div key={inp.name}>
                <label className="text-xs text-clay-400 mb-1 block">
                  {inp.name}{" "}
                  <span className="text-clay-600">({inp.type})</span>
                  {inp.required && <span className="text-red-400 ml-0.5">*</span>}
                </label>
                <Input
                  value={testInputs[inp.name] || ""}
                  onChange={(e) =>
                    setTestInputs((prev) => ({ ...prev, [inp.name]: e.target.value }))
                  }
                  placeholder={inp.description || `Enter ${inp.name}...`}
                  className="bg-clay-900 border-clay-700 text-clay-100 text-sm h-9"
                />
              </div>
            ))}
          </div>
        )}

        {/* Action buttons */}
        <div className="flex items-center gap-2 flex-wrap">
          <Button
            onClick={handleRunLocally}
            disabled={running || localWaiting}
            className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light"
            size="sm"
          >
            {localWaiting ? (
              <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
            ) : (
              <Play className="h-3.5 w-3.5 mr-1.5" />
            )}
            {localWaiting ? "Running..." : "Run"}
          </Button>

          <div className="h-5 w-px bg-clay-700" />

          <Button
            onClick={handleCopyPrompt}
            disabled={copyingPrompt}
            variant="outline"
            size="sm"
            className="border-clay-700 text-clay-400 hover:text-clay-100"
            title="Copy assembled prompt to clipboard — paste into Claude Code"
          >
            <Clipboard className="h-3.5 w-3.5 mr-1.5" />
            {copyingPrompt ? "Copying..." : "Copy Prompt"}
          </Button>

          <span className="text-[10px] text-clay-600 ml-auto hidden sm:block">
            <kbd className="px-1 py-0.5 rounded bg-clay-800 border border-clay-700 text-[10px]">
              {"\u2318"}+Enter
            </kbd>{" "}
            to run
          </span>
        </div>

        {/* Live execution trace */}
        {localJobId && (localWaiting || executionLogs.length > 0) && (
          <div className="rounded-lg border border-clay-700/50 bg-clay-950/50 overflow-hidden">
            {/* Header */}
            <div className="flex items-center gap-2 px-3 py-2 border-b border-clay-800/50 bg-clay-900/30">
              {localWaiting ? (
                <Loader2 className="h-3.5 w-3.5 animate-spin text-kiln-teal shrink-0" />
              ) : (
                <CheckCircle2 className="h-3.5 w-3.5 text-green-400 shrink-0" />
              )}
              <span className="text-xs text-clay-200 font-medium">
                {localWaiting ? "Executing locally..." : "Execution complete"}
              </span>
              {localWaiting && elapsed > 0 && (
                <span className="text-[10px] text-clay-500 font-mono">{elapsed}s</span>
              )}
              <div className="ml-auto">
                {localWaiting ? (
                  <Button
                    onClick={() => { setLocalJobId(null); setLocalWaiting(false); }}
                    variant="ghost"
                    size="sm"
                    className="text-clay-500 h-6 text-[10px] px-2"
                  >
                    Cancel
                  </Button>
                ) : (
                  <Button
                    onClick={() => setExecutionLogs([])}
                    variant="ghost"
                    size="sm"
                    className="text-clay-500 h-6 text-[10px] px-2"
                  >
                    Clear
                  </Button>
                )}
              </div>
            </div>
            {/* Log entries */}
            <div
              ref={logScrollRef}
              className="max-h-48 overflow-y-auto px-3 py-2 space-y-0.5 font-mono text-[11px]"
            >
              {executionLogs.length === 0 && localWaiting && (
                <div className="text-clay-600 text-[10px]">Waiting for daemon to pick up job...</div>
              )}
              {executionLogs.map((log, i) => (
                <div key={i} className="flex gap-2 leading-relaxed">
                  <span className="text-clay-600 shrink-0 w-12 text-right">
                    {(log.elapsed_ms / 1000).toFixed(1)}s
                  </span>
                  <span className={cn(
                    "break-all",
                    log.type === "init" && "text-clay-500",
                    log.type === "tool_use" && "text-cyan-400",
                    log.type === "tool_result" && "text-clay-400",
                    log.type === "text" && "text-clay-300",
                    log.type === "result" && "text-green-400",
                    log.type === "error" && "text-red-400",
                  )}>
                    {log.type === "tool_use" && "→ "}
                    {log.type === "tool_result" && "← "}
                    {log.type === "error" && "✗ "}
                    {log.type === "result" && "✓ "}
                    {log.message}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Batch CSV section */}
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <span className="text-xs text-clay-500 font-medium uppercase tracking-wide">Batch</span>
            <div className="flex-1 h-px bg-clay-800" />
          </div>

          {!csvRows ? (
            <div
              onDrop={(e) => { e.preventDefault(); const file = e.dataTransfer.files[0]; if (file) handleCsvUpload(file); }}
              onDragOver={(e) => e.preventDefault()}
              onClick={() => fileInputRef.current?.click()}
              className="border border-dashed border-clay-700 rounded-lg p-4 text-center cursor-pointer hover:border-clay-600 hover:bg-clay-800/30 transition-colors"
            >
              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                className="hidden"
                onChange={(e) => { const file = e.target.files?.[0]; if (file) handleCsvUpload(file); }}
              />
              <Upload className="h-5 w-5 text-clay-500 mx-auto mb-1" />
              <div className="text-xs text-clay-400">Drop CSV or click to upload</div>
            </div>
          ) : (
            <div className="space-y-2">
              <div className="flex items-center gap-2 p-2 rounded bg-clay-800/50 border border-clay-700">
                <FileSpreadsheet className="h-4 w-4 text-kiln-teal shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-clay-200 truncate">{csvFileName}</div>
                  <div className="text-[10px] text-clay-500">{csvRows.length} rows</div>
                </div>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => { setCsvRows(null); setCsvFileName(""); setBatchResults([]); }}
                  className="h-6 w-6 p-0 text-clay-500 hover:text-clay-300"
                >
                  <X className="h-3 w-3" />
                </Button>
              </div>

              {/* Preview first 3 rows */}
              <div className="overflow-x-auto rounded border border-clay-800">
                <table className="w-full text-[10px]">
                  <thead>
                    <tr className="border-b border-clay-800 bg-clay-900">
                      {Object.keys(csvRows[0]).slice(0, 5).map((h) => (
                        <th key={h} className="text-left text-clay-500 px-2 py-1 font-medium">{h}</th>
                      ))}
                      {Object.keys(csvRows[0]).length > 5 && (
                        <th className="text-clay-600 px-2 py-1">+{Object.keys(csvRows[0]).length - 5}</th>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {csvRows.slice(0, 3).map((row, i) => (
                      <tr key={i} className="border-b border-clay-800/50">
                        {Object.values(row).slice(0, 5).map((v, j) => (
                          <td key={j} className="text-clay-300 px-2 py-1 truncate max-w-[120px]">{v}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>

              <div className="flex items-center gap-2">
                <Button
                  onClick={handleBatchRun}
                  disabled={batchRunning}
                  size="sm"
                  className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light"
                >
                  {batchRunning ? (
                    <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                  ) : (
                    <Play className="h-3.5 w-3.5 mr-1.5" />
                  )}
                  {batchRunning ? `${batchProgress.done}/${batchProgress.total}` : `Run ${csvRows.length} Rows`}
                </Button>
                {batchResults.length > 0 && (
                  <Button
                    onClick={handleBatchDownload}
                    variant="outline"
                    size="sm"
                    className="border-clay-700 text-clay-400 hover:text-clay-100"
                  >
                    Download CSV
                  </Button>
                )}
              </div>

              {/* Batch progress */}
              {batchRunning && (
                <div className="space-y-1">
                  <div className="w-full bg-clay-800 rounded-full h-1.5">
                    <div
                      className="bg-kiln-teal h-1.5 rounded-full transition-all"
                      style={{ width: `${(batchProgress.done / Math.max(batchProgress.total, 1)) * 100}%` }}
                    />
                  </div>
                  <div className="text-[10px] text-clay-500">
                    {batchProgress.done}/{batchProgress.total} complete
                    {batchProgress.errors > 0 && (
                      <span className="text-red-400 ml-2">{batchProgress.errors} errors</span>
                    )}
                  </div>
                </div>
              )}

              {/* Batch results summary */}
              {!batchRunning && batchResults.length > 0 && (
                <div className="flex items-center gap-2 text-xs">
                  <Badge variant="outline" className="border-emerald-500/30 text-emerald-400 text-[10px]">
                    <CheckCircle2 className="h-3 w-3 mr-1" />
                    {batchResults.filter((r) => !r.error).length} success
                  </Badge>
                  {batchResults.some((r) => r.error) && (
                    <Badge variant="outline" className="border-red-500/30 text-red-400 text-[10px]">
                      <XCircle className="h-3 w-3 mr-1" />
                      {batchResults.filter((r) => r.error).length} errors
                    </Badge>
                  )}
                </div>
              )}
            </div>
          )}
        </div>

        {/* Streaming progress */}
        {isStreaming && (
          <div className="space-y-1.5">
            <div className="text-xs text-clay-500 font-medium uppercase tracking-wide flex items-center gap-2">
              <Loader2 className="h-3 w-3 animate-spin text-kiln-teal" />
              Executing ({streamingTrace.length} step{streamingTrace.length !== 1 ? "s" : ""} complete)
            </div>
            <div className="w-full bg-clay-800 rounded-full h-1.5">
              <div
                className="bg-kiln-teal h-1.5 rounded-full transition-all"
                style={{ width: `${Math.min((streamingTrace.length / Math.max(func.steps.length, 1)) * 100, 100)}%` }}
              />
            </div>
          </div>
        )}

        {/* Results */}
        {hasResult && (
          <div className="space-y-3">
            {/* Metrics badges */}
            <div className="flex items-center gap-2 flex-wrap">
              <Badge
                variant="outline"
                className={cn(
                  "text-[10px]",
                  hasError
                    ? "border-red-500/30 text-red-400"
                    : "border-emerald-500/30 text-emerald-400"
                )}
              >
                {hasError ? (
                  <XCircle className="h-3 w-3 mr-1" />
                ) : (
                  <CheckCircle2 className="h-3 w-3 mr-1" />
                )}
                {hasError ? "Error" : "Success"}
              </Badge>
              {fieldCount > 0 && (
                <Badge variant="outline" className="text-[10px] border-clay-600 text-clay-400">
                  <Zap className="h-3 w-3 mr-1" />
                  {fieldCount} field{fieldCount !== 1 ? "s" : ""}
                  {nullCount > 0 && ` (${nullCount} null)`}
                </Badge>
              )}
              {totalDurationMs > 0 && (
                <Badge variant="outline" className="text-[10px] border-clay-600 text-clay-400">
                  <Clock className="h-3 w-3 mr-1" />
                  {(totalDurationMs / 1000).toFixed(1)}s
                </Badge>
              )}
              <button onClick={handleCopyResult} className="ml-auto text-clay-500 hover:text-clay-300">
                {copied ? <Check className="h-3.5 w-3.5" /> : <Copy className="h-3.5 w-3.5" />}
              </button>
            </div>

            {/* Warnings */}
            {warnings.length > 0 && (
              <div className="flex items-start gap-2 text-xs text-amber-400 bg-amber-500/5 border border-amber-500/20 rounded p-2">
                <AlertTriangle className="h-3.5 w-3.5 shrink-0 mt-0.5" />
                <div>{warnings.join("; ")}</div>
              </div>
            )}

            {/* Tabs: Output / Trace / Raw / History */}
            <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)}>
              <TabsList className="bg-clay-800/50 h-8">
                <TabsTrigger value="output" className="text-xs h-6 data-[state=active]:bg-clay-700">
                  Output
                </TabsTrigger>
                {hasTrace && (
                  <TabsTrigger value="trace" className="text-xs h-6 data-[state=active]:bg-clay-700">
                    Trace
                  </TabsTrigger>
                )}
                <TabsTrigger value="raw" className="text-xs h-6 data-[state=active]:bg-clay-700">
                  Raw
                </TabsTrigger>
                <TabsTrigger value="history" className="text-xs h-6 data-[state=active]:bg-clay-700">
                  History
                </TabsTrigger>
                {funnelStages.length > 0 && (
                  <TabsTrigger value="funnel" className="text-xs h-6 data-[state=active]:bg-clay-700">
                    Funnel
                  </TabsTrigger>
                )}
              </TabsList>

              <TabsContent value="output" className="mt-2">
                {cleanOutput && <OutputRenderer result={cleanOutput} />}
              </TabsContent>

              {hasTrace && (
                <TabsContent value="trace" className="mt-2">
                  <ExecutionTrace trace={trace} totalDurationMs={totalDurationMs} stepsTotal={func.steps.length} />
                </TabsContent>
              )}

              <TabsContent value="raw" className="mt-2">
                <pre className="text-xs text-clay-300 bg-clay-900 rounded p-3 overflow-auto max-h-80 font-mono">
                  {JSON.stringify(cleanOutput, null, 2)}
                </pre>
              </TabsContent>

              <TabsContent value="history" className="mt-2">
                <ExecutionHistoryPanel functionId={func.id} />
              </TabsContent>

              {funnelStages.length > 0 && (
                <TabsContent value="funnel" className="mt-2">
                  <div className="space-y-1">
                    {funnelStages.map((stage, i) => {
                      const barWidth = funnelStages[0]?.rows_in
                        ? Math.max(5, (stage.rows_out / funnelStages[0].rows_in) * 100)
                        : 100;
                      const passColor =
                        stage.pass_rate > 0.5
                          ? "bg-emerald-500/40"
                          : stage.pass_rate > 0.25
                            ? "bg-amber-500/40"
                            : "bg-red-500/40";
                      const isGate = stage.step_type === "gate";

                      return (
                        <div key={i} className="space-y-0.5">
                          <div className="flex items-center justify-between text-[10px]">
                            <span className={cn(
                              "font-medium",
                              isGate ? "text-amber-400" : "text-clay-200"
                            )}>
                              {isGate ? `Gate: ${stage.name}` : stage.name}
                            </span>
                            <span className="text-clay-400">
                              {stage.rows_in} → {stage.rows_out}
                              {isGate && ` (${(stage.pass_rate * 100).toFixed(0)}%)`}
                              {!isGate && stage.duration_ms > 0 && ` · ${(stage.duration_ms / 1000).toFixed(1)}s`}
                            </span>
                          </div>
                          <div className="h-2 rounded-full bg-clay-800 overflow-hidden">
                            <div
                              className={cn("h-full rounded-full transition-all", isGate ? passColor : "bg-indigo-500/50")}
                              style={{ width: `${barWidth}%` }}
                            />
                          </div>
                        </div>
                      );
                    })}
                    <div className="flex items-center justify-between text-xs text-clay-300 pt-2 border-t border-clay-700 mt-2">
                      <span>Total: {funnelStages[0]?.rows_in ?? 0} in → {funnelStages[funnelStages.length - 1]?.rows_out ?? 0} out</span>
                      <span>{((funnelStages.reduce((sum, s) => sum + s.duration_ms, 0)) / 1000).toFixed(1)}s</span>
                    </div>
                  </div>
                </TabsContent>
              )}
            </Tabs>
          </div>
        )}

        {/* Show history tab when no result yet */}
        {!hasResult && !isStreaming && !pasteMode && (
          <ExecutionHistoryPanel functionId={func.id} />
        )}
      </CardContent>
    </Card>
  );
}
