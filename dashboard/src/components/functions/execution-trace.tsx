"use client";

import { useState } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ChevronDown,
  ChevronRight,
  CheckCircle2,
  XCircle,
  SkipForward,
  Clock,
  Code2,
  Zap,
  Bot,
  Globe,
  Cpu,
  AlertTriangle,
  Eye,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { StepTrace } from "@/lib/types";

const EXECUTOR_CONFIG: Record<
  string,
  { label: string; color: string; icon: typeof Zap }
> = {
  native_api: {
    label: "Native API",
    color: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
    icon: Zap,
  },
  skill: {
    label: "Skill",
    color: "bg-blue-500/15 text-blue-400 border-blue-500/30",
    icon: Cpu,
  },
  call_ai: {
    label: "AI Analysis",
    color: "bg-blue-500/15 text-blue-400 border-blue-500/30",
    icon: Bot,
  },
  ai_agent: {
    label: "AI Agent",
    color: "bg-purple-500/15 text-purple-400 border-purple-500/30",
    icon: Globe,
  },
  ai_fallback: {
    label: "AI Fallback",
    color: "bg-amber-500/15 text-amber-400 border-amber-500/30",
    icon: Bot,
  },
  unknown: {
    label: "Unknown",
    color: "bg-clay-500/15 text-clay-300 border-clay-500/30",
    icon: Code2,
  },
};

const STATUS_ICON = {
  success: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />,
  error: <XCircle className="h-3.5 w-3.5 text-red-400" />,
  skipped: <SkipForward className="h-3.5 w-3.5 text-clay-300" />,
};

interface ExecutionTraceProps {
  trace: StepTrace[];
  totalDurationMs: number;
  stepsTotal: number;
  warnings?: string[];
  isStreaming?: boolean;
  currentStepName?: string;
}

export function ExecutionTrace({
  trace,
  totalDurationMs,
  stepsTotal,
  warnings,
  isStreaming,
  currentStepName,
}: ExecutionTraceProps) {
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());
  const [showPrompt, setShowPrompt] = useState<Set<number>>(new Set());
  const [showRawResponse, setShowRawResponse] = useState<Set<number>>(new Set());

  const toggleRawResponse = (idx: number) => {
    setShowRawResponse((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const toggleExpanded = (idx: number) => {
    setExpandedSteps((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const togglePrompt = (idx: number) => {
    setShowPrompt((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  const completedSteps = trace.filter((t) => t.status === "success").length;
  const errorSteps = trace.filter((t) => t.status === "error").length;

  return (
    <div className="space-y-3">
      {/* Summary header */}
      <div className="flex items-center gap-3 text-sm">
        <span className="flex items-center gap-1.5 text-clay-300">
          <Clock className="h-3.5 w-3.5" />
          {(totalDurationMs / 1000).toFixed(1)}s total
        </span>
        <span className="text-clay-300">|</span>
        <span className="text-clay-300">
          {completedSteps}/{stepsTotal} steps
        </span>
        {errorSteps > 0 && (
          <>
            <span className="text-clay-300">|</span>
            <span className="text-red-400">{errorSteps} failed</span>
          </>
        )}
      </div>

      {/* Warnings banner */}
      {warnings && warnings.length > 0 && (
        <div className="rounded bg-amber-500/10 border border-amber-500/30 px-3 py-2 space-y-1">
          <div className="flex items-center gap-1.5 text-amber-400 text-xs font-medium">
            <AlertTriangle className="h-3 w-3" />
            {warnings.length === 1 ? "Warning" : `${warnings.length} Warnings`}
          </div>
          {warnings.map((w, i) => (
            <div key={i} className="text-[11px] text-amber-300/80 pl-4">
              {w}
            </div>
          ))}
        </div>
      )}

      {/* Step timeline */}
      <div className="relative space-y-0">
        {trace.map((step, i) => {
          const config = EXECUTOR_CONFIG[step.executor] || EXECUTOR_CONFIG.unknown;
          const Icon = config.icon;
          const isExpanded = expandedSteps.has(i);
          const isPromptShown = showPrompt.has(i);
          const isRawResponseShown = showRawResponse.has(i);
          const hasDetails =
            Object.keys(step.resolved_params).length > 0 ||
            step.output_keys.length > 0 ||
            step.ai_prompt ||
            step.ai_raw_response;
          const isLastStep = i === trace.length - 1;

          return (
            <div key={i} className="relative">
              {/* Connecting line */}
              {(!isLastStep || isStreaming) && (
                <div className="absolute left-[11px] top-8 bottom-0 w-px bg-clay-700" />
              )}

              <div className="rounded bg-clay-900/50 border border-clay-700 mb-2">
                {/* Step header */}
                <button
                  onClick={() => hasDetails && toggleExpanded(i)}
                  className={cn(
                    "flex items-center gap-2 p-2 w-full text-left",
                    hasDetails && "cursor-pointer hover:bg-clay-800/50"
                  )}
                >
                  {/* Step number dot */}
                  <span className="flex items-center justify-center h-6 w-6 rounded-full bg-clay-800 border border-clay-600 text-xs text-clay-300 shrink-0">
                    {step.step_index + 1}
                  </span>

                  {/* Status icon */}
                  {STATUS_ICON[step.status] || STATUS_ICON.success}

                  {/* Tool name */}
                  <span className="text-sm font-medium text-clay-100 truncate">
                    {step.tool_name || step.tool}
                  </span>

                  {/* Executor badge */}
                  <Badge
                    variant="outline"
                    className={cn(
                      "text-[10px] px-1.5 py-0 h-5 shrink-0 border",
                      config.color
                    )}
                  >
                    <Icon className="h-2.5 w-2.5 mr-0.5" />
                    {config.label}
                  </Badge>

                  {/* Parse error badge */}
                  {step.parse_error && (
                    <Badge
                      variant="outline"
                      className="text-[10px] px-1.5 py-0 h-5 shrink-0 border bg-red-500/15 text-red-400 border-red-500/30"
                    >
                      <AlertTriangle className="h-2.5 w-2.5 mr-0.5" />
                      Parse Failed
                    </Badge>
                  )}

                  {/* Duration pill */}
                  <span className="text-xs text-clay-300 ml-auto shrink-0">
                    {step.duration_ms >= 1000
                      ? `${(step.duration_ms / 1000).toFixed(1)}s`
                      : `${step.duration_ms}ms`}
                  </span>

                  {/* Expand indicator */}
                  {hasDetails && (
                    <span className="text-clay-300 shrink-0">
                      {isExpanded ? (
                        <ChevronDown className="h-3 w-3" />
                      ) : (
                        <ChevronRight className="h-3 w-3" />
                      )}
                    </span>
                  )}
                </button>

                {/* Error message */}
                {step.error_message && (
                  <div className="px-3 pb-2 text-[11px] text-red-400">
                    {step.error_message}
                  </div>
                )}

                {/* Expanded details */}
                {isExpanded && (
                  <div className="border-t border-clay-700 px-3 py-2 space-y-2">
                    {/* Resolved params */}
                    {Object.keys(step.resolved_params).length > 0 && (
                      <div>
                        <div className="text-xs text-clay-300 mb-1 font-medium uppercase tracking-wide">
                          Parameters
                        </div>
                        <div className="space-y-0.5">
                          {Object.entries(step.resolved_params).map(
                            ([key, val]) => (
                              <div
                                key={key}
                                className="flex items-baseline gap-2 text-xs"
                              >
                                <span className="text-clay-300 font-mono shrink-0">
                                  {key}
                                </span>
                                <span className="text-clay-300">=</span>
                                <span className="text-clay-200 break-all">
                                  {val}
                                </span>
                              </div>
                            )
                          )}
                        </div>
                      </div>
                    )}

                    {/* Output keys */}
                    {step.output_keys.length > 0 && (
                      <div>
                        <div className="text-xs text-clay-300 mb-1 font-medium uppercase tracking-wide">
                          Output
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {step.output_keys.map((key) => (
                            <Badge
                              key={key}
                              variant="outline"
                              className="text-[10px] px-1.5 py-0 h-5 text-kiln-teal border-kiln-teal/30"
                            >
                              {key}
                            </Badge>
                          ))}
                        </div>
                      </div>
                    )}

                    {/* AI Prompt accordion */}
                    {step.ai_prompt && (
                      <div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            togglePrompt(i);
                          }}
                          className="h-6 px-1 text-xs text-clay-300 hover:text-clay-200"
                        >
                          <Code2 className="h-3 w-3 mr-1" />
                          {isPromptShown ? "Hide Prompt" : "Show Prompt"}
                        </Button>
                        {isPromptShown && (
                          <pre className="mt-1 text-xs text-clay-300 bg-clay-950 p-3 rounded border border-clay-800 overflow-auto max-h-48 whitespace-pre-wrap">
                            {step.ai_prompt}
                          </pre>
                        )}
                      </div>
                    )}

                    {/* AI Raw Response accordion */}
                    {step.ai_raw_response && (
                      <div>
                        <Button
                          variant="ghost"
                          size="sm"
                          onClick={(e) => {
                            e.stopPropagation();
                            toggleRawResponse(i);
                          }}
                          className={cn(
                            "h-6 px-1 text-xs hover:text-clay-200",
                            step.parse_error
                              ? "text-red-400"
                              : "text-clay-300"
                          )}
                        >
                          <Eye className="h-3 w-3 mr-1" />
                          {isRawResponseShown ? "Hide AI Response" : "Show AI Response"}
                        </Button>
                        {isRawResponseShown && (
                          <pre className={cn(
                            "mt-1 text-xs p-3 rounded border overflow-auto max-h-48 whitespace-pre-wrap",
                            step.parse_error
                              ? "text-red-300 bg-red-950/30 border-red-800/50"
                              : "text-clay-300 bg-clay-950 border-clay-800"
                          )}>
                            {step.ai_raw_response}
                          </pre>
                        )}
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
          );
        })}

        {/* Streaming skeleton — pulsing indicator for the step currently running */}
        {isStreaming && (
          <div className="relative">
            <div className="rounded bg-clay-900/50 border border-clay-700 border-dashed mb-2 animate-pulse">
              <div className="flex items-center gap-2 p-2">
                <span className="flex items-center justify-center h-6 w-6 rounded-full bg-clay-800 border border-clay-600 text-xs text-clay-300 shrink-0">
                  {trace.length + 1}
                </span>
                <div className="h-3.5 w-3.5 rounded-full border-2 border-kiln-teal border-t-transparent animate-spin" />
                <span className="text-sm text-clay-300">
                  Running{currentStepName ? ` ${currentStepName}` : ""}...
                </span>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
