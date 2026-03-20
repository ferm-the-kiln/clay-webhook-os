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
} from "lucide-react";
import { toast } from "sonner";
import { cn } from "@/lib/utils";
import type { FunctionInput, StepTrace, PreviewStep } from "@/lib/types";
import { ExecutionTrace } from "./execution-trace";
import { ExecutionHistoryPanel } from "./execution-history";
import { OutputView } from "./output-view";

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
            className="text-clay-400 h-6 w-6 p-0"
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
              <div className="text-sm text-clay-500">
                No inputs defined — will run with empty data.
              </div>
            ) : (
              <div className="space-y-3">
                {inputs.map((inp) => (
                  <div key={inp.name}>
                    <label className="text-xs text-clay-400 mb-1 block">
                      {inp.name}{" "}
                      <span className="text-clay-500">({inp.type})</span>
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
              {testResult && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    setTestInputs({});
                  }}
                  className="text-clay-400 text-xs"
                >
                  Clear
                </Button>
              )}
              <span className="text-xs text-clay-500 ml-auto">
                <kbd className="px-1 py-0.5 rounded bg-clay-800 border border-clay-600 text-[10px]">
                  {"\u2318"}+Enter
                </kbd>{" "}
                to run
              </span>
            </div>

            {/* Preview panel */}
            {preview && !testResult && (
              <div className="space-y-2">
                <div className="text-xs text-clay-500 font-medium uppercase tracking-wide">
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
                    return (
                      <div
                        key={step.step_index}
                        className="flex items-center gap-2 p-2 rounded bg-clay-900/50 border border-clay-700"
                      >
                        <span className="text-xs text-clay-500 w-4">
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
                          <span className="text-xs text-amber-400 ml-auto">
                            {step.unresolved_variables.length} unresolved
                          </span>
                        )}
                      </div>
                    );
                  })}
                </div>
                <div className="flex items-center gap-2 text-xs text-clay-500">
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
                    <span className="text-clay-500 truncate">
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
                    className="ml-auto text-clay-400 hover:text-clay-200 p-1 rounded hover:bg-clay-800 transition-colors"
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
                    <OutputView result={testResult} />
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
              <div className="flex flex-col items-center justify-center h-full min-h-[200px] text-clay-500">
                <FlaskConical className="h-8 w-8 mb-2 opacity-30" />
                <span className="text-sm">Run to see results</span>
                {functionId && (
                  <button
                    onClick={() => setActiveTab("history")}
                    className="mt-2 text-xs text-clay-500 hover:text-kiln-teal transition-colors flex items-center gap-1"
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
