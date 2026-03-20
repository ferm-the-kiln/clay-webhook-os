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
    color: "bg-clay-500/15 text-clay-400 border-clay-500/30",
    icon: Code2,
  },
};

const STATUS_ICON = {
  success: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />,
  error: <XCircle className="h-3.5 w-3.5 text-red-400" />,
  skipped: <SkipForward className="h-3.5 w-3.5 text-clay-500" />,
};

interface ExecutionTraceProps {
  trace: StepTrace[];
  totalDurationMs: number;
  stepsTotal: number;
}

export function ExecutionTrace({
  trace,
  totalDurationMs,
  stepsTotal,
}: ExecutionTraceProps) {
  const [expandedSteps, setExpandedSteps] = useState<Set<number>>(new Set());
  const [showPrompt, setShowPrompt] = useState<Set<number>>(new Set());

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
      <div className="flex items-center gap-3 text-xs">
        <span className="flex items-center gap-1.5 text-clay-300">
          <Clock className="h-3 w-3" />
          {(totalDurationMs / 1000).toFixed(1)}s total
        </span>
        <span className="text-clay-600">|</span>
        <span className="text-clay-300">
          {completedSteps}/{stepsTotal} steps
        </span>
        {errorSteps > 0 && (
          <>
            <span className="text-clay-600">|</span>
            <span className="text-red-400">{errorSteps} failed</span>
          </>
        )}
      </div>

      {/* Step timeline */}
      <div className="relative space-y-0">
        {trace.map((step, i) => {
          const config = EXECUTOR_CONFIG[step.executor] || EXECUTOR_CONFIG.unknown;
          const Icon = config.icon;
          const isExpanded = expandedSteps.has(i);
          const isPromptShown = showPrompt.has(i);
          const hasDetails =
            Object.keys(step.resolved_params).length > 0 ||
            step.output_keys.length > 0 ||
            step.ai_prompt;

          return (
            <div key={i} className="relative">
              {/* Connecting line */}
              {i < trace.length - 1 && (
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
                  <span className="flex items-center justify-center h-5 w-5 rounded-full bg-clay-800 border border-clay-600 text-[10px] text-clay-400 shrink-0">
                    {step.step_index + 1}
                  </span>

                  {/* Status icon */}
                  {STATUS_ICON[step.status] || STATUS_ICON.success}

                  {/* Tool name */}
                  <span className="text-xs font-medium text-clay-100 truncate">
                    {step.tool_name || step.tool}
                  </span>

                  {/* Executor badge */}
                  <Badge
                    variant="outline"
                    className={cn(
                      "text-[9px] px-1.5 py-0 h-4 shrink-0 border",
                      config.color
                    )}
                  >
                    <Icon className="h-2.5 w-2.5 mr-0.5" />
                    {config.label}
                  </Badge>

                  {/* Duration pill */}
                  <span className="text-[10px] text-clay-500 ml-auto shrink-0">
                    {step.duration_ms >= 1000
                      ? `${(step.duration_ms / 1000).toFixed(1)}s`
                      : `${step.duration_ms}ms`}
                  </span>

                  {/* Expand indicator */}
                  {hasDetails && (
                    <span className="text-clay-500 shrink-0">
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
                        <div className="text-[10px] text-clay-500 mb-1 font-medium uppercase tracking-wide">
                          Parameters
                        </div>
                        <div className="space-y-0.5">
                          {Object.entries(step.resolved_params).map(
                            ([key, val]) => (
                              <div
                                key={key}
                                className="flex items-baseline gap-2 text-[11px]"
                              >
                                <span className="text-clay-400 font-mono shrink-0">
                                  {key}
                                </span>
                                <span className="text-clay-600">=</span>
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
                        <div className="text-[10px] text-clay-500 mb-1 font-medium uppercase tracking-wide">
                          Output
                        </div>
                        <div className="flex flex-wrap gap-1">
                          {step.output_keys.map((key) => (
                            <Badge
                              key={key}
                              variant="outline"
                              className="text-[9px] px-1.5 py-0 h-4 text-kiln-teal border-kiln-teal/30"
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
                          className="h-5 px-1 text-[10px] text-clay-400 hover:text-clay-200"
                        >
                          <Code2 className="h-3 w-3 mr-1" />
                          {isPromptShown ? "Hide Prompt" : "Show Prompt"}
                        </Button>
                        {isPromptShown && (
                          <pre className="mt-1 text-[10px] text-clay-400 bg-clay-950 p-2 rounded border border-clay-800 overflow-auto max-h-48 whitespace-pre-wrap">
                            {step.ai_prompt}
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
      </div>
    </div>
  );
}
