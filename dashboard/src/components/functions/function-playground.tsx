"use client";

import { useState, useEffect } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import {
  Play,
  FlaskConical,
  X,
  Eye,
  Code2,
  AlertTriangle,
  History,
  CheckCircle2,
  XCircle,
  Copy,
  Check,
  Loader2,
  Clock,
  Zap,
  Terminal,
  Clipboard,
  ClipboardPaste,
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import type { FunctionInput, StepTrace, PreviewStep } from "@/lib/types";
import { ExecutionTrace } from "./execution-trace";
import { ExecutionHistoryPanel } from "./execution-history";
import { OutputRenderer } from "@/components/output/output-renderer";
import { testFunctionStep, prepareConsolidatedPrompt, queueLocalJob, submitLocalResult, fetchLocalJob } from "@/lib/api";

interface FunctionPlaygroundProps {
  inputs: FunctionInput[];
  testInputs: Record<string, string>;
  setTestInputs: React.Dispatch<React.SetStateAction<Record<string, string>>>;
  testResult: Record<string, unknown> | null;
  testing: boolean;
  onRun: () => void;
  onClose: () => void;
  preview: {
    steps: PreviewStep[];
    unresolved_variables: string[];
    summary: Record<string, number>;
  } | null;
  previewing: boolean;
  onPreview: () => void;
  streamingTrace?: StepTrace[];
  functionId?: string;
}

const EXECUTOR_BADGE: Record<string, { label: string; color: string }> = {
  native_api: {
    label: "Native API",
    color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  },
  skill: {
    label: "Skill",
    color: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  },
  call_ai: {
    label: "AI Analysis",
    color: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  },
  ai_agent: {
    label: "AI Agent",
    color: "bg-purple-500/15 text-purple-400 border-purple-500/30",
  },
  ai_single: {
    label: "AI Single",
    color: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  },
  ai_fallback: {
    label: "AI Fallback",
    color: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  },
};

export function FunctionPlayground({
  inputs,
  testInputs,
  setTestInputs,
  testResult,
  testing,
  onRun,
  onClose,
  preview,
  previewing,
  onPreview,
  streamingTrace,
  functionId,
}: FunctionPlaygroundProps) {
  const [activeTab, setActiveTab] = useState<"output" | "trace" | "raw" | "history">("output");
  const [copied, setCopied] = useState(false);

  // Local execution state
  const [copyingPrompt, setCopyingPrompt] = useState(false);
  const [localJobId, setLocalJobId] = useState<string | null>(null);
  const [localWaiting, setLocalWaiting] = useState(false);
  const [pasteMode, setPasteMode] = useState(false);
  const [pastedJson, setPastedJson] = useState("");

  const handleCopyPrompt = async () => {
    if (!functionId) return;
    setCopyingPrompt(true);
    try {
      const result = await prepareConsolidatedPrompt(functionId, testInputs);
      await navigator.clipboard.writeText(result.prompt);
      toast.success(`Prompt copied (${(result.prompt.length / 1000).toFixed(1)}k chars)`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to copy prompt");
    } finally {
      setCopyingPrompt(false);
    }
  };

  const handleRunLocally = async () => {
    if (!functionId) return;
    setLocalWaiting(true);
    try {
      const job = await queueLocalJob(functionId, testInputs);
      setLocalJobId(job.job_id);
      toast.success(`Job queued: ${job.job_id}. Run clay-run --watch to pick it up.`);
      setPasteMode(true);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to queue job");
      setLocalWaiting(false);
    }
  };

  const handleSubmitPastedResult = async () => {
    if (!functionId || !localJobId) return;
    try {
      const parsed = JSON.parse(pastedJson);
      const response = await submitLocalResult(functionId, localJobId, parsed);
      toast.success(`Result saved: ${response.exec_id}`);
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

  // Poll for local job completion (when waiting)
  useEffect(() => {
    if (!localJobId || !localWaiting) return;
    const interval = setInterval(async () => {
      try {
        const job = await fetchLocalJob(localJobId);
        if (job.status === "completed" || job.status === "failed") {
          setLocalWaiting(false);
          if (job.status === "completed") {
            toast.success("Local execution complete — check execution history");
          } else {
            toast.error("Local execution failed");
          }
          clearInterval(interval);
        }
      } catch {
        // Job might not exist yet, keep polling
      }
    }, 3000);
    return () => clearInterval(interval);
  }, [localJobId, localWaiting]);

  // Step-level testing
  const [testingStepIdx, setTestingStepIdx] = useState<number | null>(null);
  const [stepResult, setStepResult] = useState<{
    step_index: number;
    tool: string;
    executor: string;
    status: string;
    output?: Record<string, unknown>;
    error_message?: string;
    duration_ms: number;
  } | null>(null);

  const handleTestStep = async (stepIndex: number) => {
    if (!functionId) return;
    setTestingStepIdx(stepIndex);
    setStepResult(null);
    try {
      const result = await testFunctionStep(functionId, stepIndex, testInputs);
      setStepResult(result);
      if (result.status === "success") {
        toast.success(`Step ${stepIndex + 1} completed in ${(result.duration_ms / 1000).toFixed(1)}s`);
      } else {
        toast.error(`Step ${stepIndex + 1} failed: ${result.error_message}`);
      }
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Step test failed");
    } finally {
      setTestingStepIdx(null);
    }
  };

  // Auto-switch to output tab when result arrives
  useEffect(() => {
    if (testResult) {
      setActiveTab("output");
    }
  }, [testResult]);

  // Extract trace from test result _meta
  const meta = testResult?._meta as Record<string, unknown> | undefined;
  const trace = meta?.trace as StepTrace[] | undefined;
  const totalDurationMs = (meta?.duration_ms as number) || 0;
  const stepsTotal = (meta?.steps as number) || 0;
  const hasTrace = trace && trace.length > 0;

  // Extract warnings — from _warnings field or auto-detect null outputs
  const rawWarnings = testResult?._warnings as string[] | undefined;
  const warnings: string[] = rawWarnings ? [...rawWarnings] : [];
  if (testResult && !rawWarnings) {
    const nullKeys = Object.entries(testResult)
      .filter(([k, v]) => v === null && !k.startsWith("_"))
      .map(([k]) => k);
    if (nullKeys.length > 0) {
      warnings.push(`${nullKeys.length} output field${nullKeys.length > 1 ? "s" : ""} returned null: ${nullKeys.join(", ")}`);
    }
  }

  // Clean output: strip _-prefixed keys for display & copy
  const getCleanOutput = () => {
    if (!testResult) return {};
    return Object.fromEntries(
      Object.entries(testResult).filter(([k]) => !k.startsWith("_"))
    );
  };

  const cleanOutput = testResult ? getCleanOutput() : null;
  const fieldCount = cleanOutput ? Object.keys(cleanOutput).length : 0;
  const nullCount = cleanOutput
    ? Object.values(cleanOutput).filter((v) => v === null).length
    : 0;
  const hasError = testResult?.error === true;

  const handleCopy = async () => {
    if (!cleanOutput) return;
    await navigator.clipboard.writeText(JSON.stringify(cleanOutput, null, 2));
    setCopied(true);
    toast.success("Copied");
    setTimeout(() => setCopied(false), 2000);
  };

  // Determine if the right pane has content
  const hasRightContent = testResult || (testing && streamingTrace && streamingTrace.length > 0) || (preview && !testResult);

  return (
    <Card className="border-clay-600 border-kiln-teal/30">
      <CardHeader className="pb-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base text-clay-200 flex items-center gap-2">
            <FlaskConical className="h-5 w-5 text-kiln-teal" />
            Quick Test
          </CardTitle>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClose}
            className="text-clay-300 h-6 w-6 p-0"
          >
            <X className="h-3.5 w-3.5" />
          </Button>
        </div>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-0">
          {/* Left pane — Inputs + Actions + Preview + Streaming */}
          <div className="lg:border-r lg:border-clay-700 pr-0 lg:pr-5 pb-4 lg:pb-0 space-y-4">
            {inputs.length === 0 ? (
              <div className="text-sm text-clay-300">
                No inputs defined — will run with empty data.
              </div>
            ) : (
              <div className="space-y-3">
                {inputs.map((inp) => (
                  <div key={inp.name}>
                    <label className="text-xs text-clay-300 mb-1 block">
                      {inp.name}{" "}
                      <span className="text-clay-300">({inp.type})</span>
                      {inp.required && (
                        <span className="text-red-400 ml-1">*</span>
                      )}
                    </label>
                    <Input
                      value={testInputs[inp.name] || ""}
                      onChange={(e) =>
                        setTestInputs((prev) => ({
                          ...prev,
                          [inp.name]: e.target.value,
                        }))
                      }
                      placeholder={`Enter ${inp.name}...`}
                      className="bg-clay-900 border-clay-600 text-clay-100 text-sm h-9"
                    />
                  </div>
                ))}
              </div>
            )}

            <div className="flex items-center gap-2">
              <Button
                onClick={onPreview}
                disabled={previewing || testing}
                variant="outline"
                className="border-clay-600 text-clay-300 hover:text-clay-100"
              >
                <Eye className="h-4 w-4 mr-1.5" />
                {previewing ? "..." : "Preview"}
              </Button>
              <Button
                onClick={onRun}
                disabled={testing}
                className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light"
              >
                <Play className="h-4 w-4 mr-1.5" />
                {testing ? "Running..." : "Run"}
              </Button>
              <div className="flex items-center gap-1 border-l border-clay-700 pl-2 ml-1">
                <Button
                  onClick={handleCopyPrompt}
                  disabled={copyingPrompt || !functionId}
                  variant="outline"
                  size="sm"
                  className="border-clay-600 text-clay-300 hover:text-clay-100 h-9 px-2"
                  title="Copy assembled prompt to clipboard"
                >
                  <Clipboard className="h-3.5 w-3.5 mr-1" />
                  {copyingPrompt ? "..." : "Prompt"}
                </Button>
                <Button
                  onClick={handleRunLocally}
                  disabled={localWaiting || !functionId}
                  variant="outline"
                  size="sm"
                  className="border-clay-600 text-clay-300 hover:text-clay-100 h-9 px-2"
                  title="Queue for local execution via clay-run"
                >
                  <Terminal className="h-3.5 w-3.5 mr-1" />
                  {localWaiting ? "Queued..." : "Local"}
                </Button>
              </div>
              {testResult && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setTestInputs({});
                  }}
                  className="text-clay-300 text-xs"
                >
                  Clear
                </Button>
              )}
              <span className="text-xs text-clay-300 ml-auto">
                <kbd className="px-1 py-0.5 rounded bg-clay-800 border border-clay-600 text-[10px]">
                  {"\u2318"}+Enter
                </kbd>{" "}
                to run
              </span>
            </div>

            {/* Paste Result (shown when local job is queued) */}
            {pasteMode && localJobId && (
              <div className="space-y-2 p-3 rounded-lg border border-amber-500/30 bg-amber-500/5">
                <div className="flex items-center gap-2 text-xs text-amber-400">
                  <ClipboardPaste className="h-3.5 w-3.5" />
                  <span className="font-medium">Paste Result</span>
                  {localWaiting && (
                    <span className="flex items-center gap-1 ml-auto text-clay-300">
                      <Loader2 className="h-3 w-3 animate-spin" />
                      Waiting for clay-run...
                    </span>
                  )}
                </div>
                <textarea
                  value={pastedJson}
                  onChange={(e) => setPastedJson(e.target.value)}
                  placeholder='Paste JSON result from Claude Code here...'
                  className="w-full h-24 bg-clay-900 border border-clay-600 rounded text-xs text-clay-200 p-2 font-mono resize-y focus:outline-none focus:border-amber-500/50"
                />
                <div className="flex items-center gap-2">
                  <Button
                    onClick={handleSubmitPastedResult}
                    disabled={!pastedJson.trim()}
                    size="sm"
                    className="bg-amber-600 text-white hover:bg-amber-500 h-7 text-xs"
                  >
                    Submit Result
                  </Button>
                  <Button
                    onClick={() => {
                      setPasteMode(false);
                      setPastedJson("");
                      setLocalJobId(null);
                      setLocalWaiting(false);
                    }}
                    variant="ghost"
                    size="sm"
                    className="text-clay-300 h-7 text-xs"
                  >
                    Cancel
                  </Button>
                  <span className="text-[10px] text-clay-300 ml-auto">
                    Job: {localJobId}
                  </span>
                </div>
              </div>
            )}

            {/* Preview panel */}
            {preview && !testResult && (
              <div className="space-y-2">
                <div className="text-xs text-clay-300 font-medium uppercase tracking-wide">
                  Execution Preview
                </div>
                {preview.unresolved_variables.length > 0 && (
                  <div className="flex items-center gap-1.5 text-xs text-amber-400 bg-amber-500/10 border border-amber-500/20 rounded px-2 py-1.5">
                    <AlertTriangle className="h-3 w-3 shrink-0" />
                    Unresolved: {preview.unresolved_variables.join(", ")}
                  </div>
                )}
                <div className="space-y-1.5">
                  {preview.steps.map((step) => {
                    const badge = EXECUTOR_BADGE[step.executor] || EXECUTOR_BADGE.ai_fallback;
                    const isTestingThis = testingStepIdx === step.step_index;
                    return (
                      <div
                        key={step.step_index}
                        className="flex items-center gap-2 p-2 rounded bg-clay-900/50 border border-clay-700"
                      >
                        <span className="text-xs text-clay-300 w-4">
                          {step.step_index + 1}
                        </span>
                        <span className="text-sm text-clay-100 font-medium truncate">
                          {step.tool_name || step.tool}
                        </span>
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-[10px] px-1.5 py-0 h-5 shrink-0 border",
                            badge.color
                          )}
                        >
                          {badge.label}
                        </Badge>
                        {step.unresolved_variables.length > 0 && (
                          <span className="text-xs text-amber-400">
                            {step.unresolved_variables.length} unresolved
                          </span>
                        )}
                        {functionId && (
                          <button
                            onClick={() => handleTestStep(step.step_index)}
                            disabled={isTestingThis || testingStepIdx !== null}
                            className="ml-auto flex items-center gap-1 text-[10px] text-clay-300 hover:text-kiln-teal transition-colors disabled:opacity-50"
                          >
                            {isTestingThis ? (
                              <Loader2 className="h-3 w-3 animate-spin" />
                            ) : (
                              <Zap className="h-3 w-3" />
                            )}
                            Test
                          </button>
                        )}
                      </div>
                    );
                  })}
                </div>

                {/* Step test result */}
                {stepResult && (
                  <div className={cn(
                    "rounded border p-2.5 text-xs",
                    stepResult.status === "success"
                      ? "bg-emerald-500/10 border-emerald-500/30"
                      : "bg-red-500/10 border-red-500/30"
                  )}>
                    <div className="flex items-center gap-2 mb-1.5">
                      {stepResult.status === "success" ? (
                        <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />
                      ) : (
                        <XCircle className="h-3.5 w-3.5 text-red-400" />
                      )}
                      <span className={stepResult.status === "success" ? "text-emerald-400" : "text-red-400"}>
                        Step {stepResult.step_index + 1}: {stepResult.tool}
                      </span>
                      <span className="text-clay-300 ml-auto">{(stepResult.duration_ms / 1000).toFixed(1)}s</span>
                    </div>
                    {stepResult.status === "success" && stepResult.output && (
                      <pre className="text-clay-300 bg-clay-900/50 rounded p-2 overflow-auto max-h-32 whitespace-pre-wrap">
                        {JSON.stringify(stepResult.output, null, 2)}
                      </pre>
                    )}
                    {stepResult.error_message && (
                      <div className="text-red-300">{stepResult.error_message}</div>
                    )}
                  </div>
                )}
                <div className="flex items-center gap-2 text-xs text-clay-300">
                  {Object.entries(preview.summary).map(([key, val]) => (
                    <span key={key}>
                      {val}x {key.replace("_", " ")}
                    </span>
                  ))}
                </div>
              </div>
            )}

            {/* Compact streaming indicator (during execution) */}
            {testing && streamingTrace && streamingTrace.length > 0 && !testResult && (
              <div className="space-y-1.5">
                <div className="flex items-center gap-2 text-sm text-clay-300">
                  <Loader2 className="h-4 w-4 text-kiln-teal animate-spin" />
                  <span>
                    Running step {streamingTrace.length}
                    {stepsTotal > 0 ? `/${stepsTotal}` : ""}...
                  </span>
                  {streamingTrace[streamingTrace.length - 1] && (
                    <span className="text-clay-300 truncate">
                      {streamingTrace[streamingTrace.length - 1].tool_name ||
                        streamingTrace[streamingTrace.length - 1].tool}
                    </span>
                  )}
                </div>
                {stepsTotal > 0 && (
                  <div className="h-1.5 rounded-full bg-clay-800 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-kiln-teal transition-all duration-300"
                      style={{
                        width: `${Math.min((streamingTrace.length / stepsTotal) * 100, 100)}%`,
                      }}
                    />
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Right pane — Results / Empty state */}
          <div className="pl-0 lg:pl-5 pt-4 lg:pt-0 border-t lg:border-t-0 border-clay-700 min-h-[200px]">
            {testResult ? (
              <div className="space-y-3">
                {/* Metrics bar — pill badges */}
                <div className="flex items-center gap-2 flex-wrap">
                  {hasError ? (
                    <Badge variant="outline" className="text-xs px-2.5 py-1 border bg-red-500/15 text-red-400 border-red-500/30">
                      <XCircle className="h-3.5 w-3.5 mr-1" />
                      Error
                    </Badge>
                  ) : (
                    <Badge variant="outline" className="text-xs px-2.5 py-1 border bg-emerald-500/15 text-emerald-400 border-emerald-500/30">
                      <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
                      Success
                    </Badge>
                  )}
                  {!hasError && (
                    <Badge variant="outline" className="text-xs px-2.5 py-1 border-clay-600 text-clay-300">
                      {fieldCount} field{fieldCount !== 1 ? "s" : ""}
                    </Badge>
                  )}
                  {nullCount > 0 && (
                    <Badge variant="outline" className="text-xs px-2.5 py-1 border bg-amber-500/15 text-amber-400 border-amber-500/30">
                      {nullCount} null
                    </Badge>
                  )}
                  {totalDurationMs > 0 && (
                    <Badge variant="outline" className="text-xs px-2.5 py-1 border-clay-600 text-clay-300">
                      <Clock className="h-3.5 w-3.5 mr-1" />
                      {(totalDurationMs / 1000).toFixed(1)}s
                    </Badge>
                  )}
                  {stepsTotal > 0 && (
                    <Badge variant="outline" className="text-xs px-2.5 py-1 border-clay-600 text-clay-300">
                      {stepsTotal} step{stepsTotal !== 1 ? "s" : ""}
                    </Badge>
                  )}
                  <button
                    onClick={handleCopy}
                    className="ml-auto text-clay-300 hover:text-clay-200 p-1 rounded hover:bg-clay-800 transition-colors"
                    title="Copy clean output"
                  >
                    {copied ? (
                      <Check className="h-4 w-4 text-emerald-400" />
                    ) : (
                      <Copy className="h-4 w-4" />
                    )}
                  </button>
                </div>

                {/* Tabs */}
                <Tabs value={activeTab} onValueChange={(v) => setActiveTab(v as typeof activeTab)}>
                  <TabsList variant="line">
                    <TabsTrigger value="output">Output</TabsTrigger>
                    {hasTrace && <TabsTrigger value="trace">Trace</TabsTrigger>}
                    <TabsTrigger value="raw">
                      <Code2 className="h-3.5 w-3.5 mr-1" />
                      Raw JSON
                    </TabsTrigger>
                    {functionId && (
                      <TabsTrigger value="history">
                        <History className="h-3.5 w-3.5 mr-1" />
                        History
                      </TabsTrigger>
                    )}
                  </TabsList>

                  <TabsContent value="output">
                    <OutputRenderer result={testResult} />
                  </TabsContent>

                  {hasTrace && (
                    <TabsContent value="trace">
                      <ExecutionTrace
                        trace={trace}
                        totalDurationMs={totalDurationMs}
                        stepsTotal={stepsTotal}
                        warnings={warnings.length > 0 ? warnings : undefined}
                      />
                    </TabsContent>
                  )}

                  <TabsContent value="raw">
                    <pre className="text-xs text-clay-300 bg-clay-900 p-3 rounded border border-clay-700 overflow-auto max-h-64 whitespace-pre-wrap">
                      {JSON.stringify(testResult, null, 2)}
                    </pre>
                  </TabsContent>

                  {functionId && (
                    <TabsContent value="history">
                      <ExecutionHistoryPanel functionId={functionId} />
                    </TabsContent>
                  )}
                </Tabs>
              </div>
            ) : !hasRightContent ? (
              /* Empty state */
              <div className="flex flex-col items-center justify-center h-full min-h-[200px] text-clay-300">
                <FlaskConical className="h-8 w-8 mb-2 opacity-30" />
                <span className="text-sm">Run to see results</span>
                {functionId && (
                  <button
                    onClick={() => setActiveTab("history")}
                    className="mt-2 text-xs text-clay-300 hover:text-kiln-teal transition-colors flex items-center gap-1"
                  >
                    <History className="h-3.5 w-3.5" />
                    View past runs
                  </button>
                )}
              </div>
            ) : null}

            {/* History panel when toggled from empty state */}
            {!testResult && activeTab === "history" && functionId && (
              <ExecutionHistoryPanel functionId={functionId} />
            )}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
