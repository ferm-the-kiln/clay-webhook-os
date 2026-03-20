"use client";

import { useState, useEffect } from "react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  ChevronDown,
  ChevronRight,
  Clock,
  CheckCircle2,
  XCircle,
  AlertTriangle,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { ExecutionRecord } from "@/lib/types";
import { fetchExecutions } from "@/lib/api";
import { ExecutionTrace } from "./execution-trace";

const STATUS_CONFIG = {
  success: {
    icon: <CheckCircle2 className="h-3.5 w-3.5 text-emerald-400" />,
    color: "bg-emerald-500",
    label: "Success",
  },
  error: {
    icon: <XCircle className="h-3.5 w-3.5 text-red-400" />,
    color: "bg-red-500",
    label: "Error",
  },
  partial: {
    icon: <AlertTriangle className="h-3.5 w-3.5 text-amber-400" />,
    color: "bg-amber-500",
    label: "Partial",
  },
};

interface ExecutionHistoryPanelProps {
  functionId: string;
}

export function ExecutionHistoryPanel({ functionId }: ExecutionHistoryPanelProps) {
  const [records, setRecords] = useState<ExecutionRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [expandedId, setExpandedId] = useState<string | null>(null);
  const [showInputs, setShowInputs] = useState<Set<string>>(new Set());
  const [showOutputs, setShowOutputs] = useState<Set<string>>(new Set());

  useEffect(() => {
    setLoading(true);
    fetchExecutions(functionId, 20)
      .then((res) => setRecords(res.executions))
      .catch(() => setRecords([]))
      .finally(() => setLoading(false));
  }, [functionId]);

  const toggleInputs = (id: string) => {
    setShowInputs((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const toggleOutputs = (id: string) => {
    setShowOutputs((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  if (loading) {
    return (
      <div className="text-sm text-clay-500 py-4 text-center">
        Loading history...
      </div>
    );
  }

  if (records.length === 0) {
    return (
      <div className="text-sm text-clay-500 py-4 text-center">
        No past runs yet. Run the function to see execution history.
      </div>
    );
  }

  return (
    <div className="space-y-2">
      {records.map((rec) => {
        const status = STATUS_CONFIG[rec.status] || STATUS_CONFIG.error;
        const isExpanded = expandedId === rec.id;
        const ts = new Date(rec.timestamp * 1000);
        const timeStr = ts.toLocaleString(undefined, {
          month: "short",
          day: "numeric",
          hour: "2-digit",
          minute: "2-digit",
        });

        return (
          <div
            key={rec.id}
            className="rounded bg-clay-900/50 border border-clay-700"
          >
            {/* Summary row */}
            <button
              onClick={() => setExpandedId(isExpanded ? null : rec.id)}
              className="flex items-center gap-2 p-2.5 w-full text-left hover:bg-clay-800/50 transition-colors"
            >
              {/* Status dot */}
              <span className={cn("h-2.5 w-2.5 rounded-full shrink-0", status.color)} />

              {/* Timestamp */}
              <span className="text-xs text-clay-400 shrink-0 w-28">
                {timeStr}
              </span>

              {/* Duration badge */}
              <Badge
                variant="outline"
                className="text-[10px] px-1.5 py-0 h-5 border-clay-600 text-clay-300 shrink-0"
              >
                <Clock className="h-2.5 w-2.5 mr-0.5" />
                {rec.duration_ms >= 1000
                  ? `${(rec.duration_ms / 1000).toFixed(1)}s`
                  : `${rec.duration_ms}ms`}
              </Badge>

              {/* Step count */}
              <span className="text-xs text-clay-500">
                {rec.step_count} step{rec.step_count !== 1 ? "s" : ""}
              </span>

              {/* Status */}
              <span className="flex items-center gap-1 ml-auto text-xs">
                {status.icon}
                <span className="text-clay-400">{status.label}</span>
              </span>

              {/* Expand indicator */}
              <span className="text-clay-500 shrink-0">
                {isExpanded ? (
                  <ChevronDown className="h-3 w-3" />
                ) : (
                  <ChevronRight className="h-3 w-3" />
                )}
              </span>
            </button>

            {/* Expanded content */}
            {isExpanded && (
              <div className="border-t border-clay-700 px-3 py-2 space-y-3">
                {/* Warnings */}
                {rec.warnings && rec.warnings.length > 0 && (
                  <div className="rounded bg-amber-500/10 border border-amber-500/30 px-2 py-1.5">
                    {rec.warnings.map((w, i) => (
                      <div key={i} className="text-[11px] text-amber-300/80">
                        {w}
                      </div>
                    ))}
                  </div>
                )}

                {/* Inputs collapsible */}
                <div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleInputs(rec.id);
                    }}
                    className="h-6 px-1 text-xs text-clay-400 hover:text-clay-200"
                  >
                    {showInputs.has(rec.id) ? "Hide Inputs" : "Show Inputs"}
                  </Button>
                  {showInputs.has(rec.id) && (
                    <pre className="mt-1 text-xs text-clay-400 bg-clay-950 p-3 rounded border border-clay-800 overflow-auto max-h-32 whitespace-pre-wrap">
                      {JSON.stringify(rec.inputs, null, 2)}
                    </pre>
                  )}
                </div>

                {/* Outputs collapsible */}
                <div>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={(e) => {
                      e.stopPropagation();
                      toggleOutputs(rec.id);
                    }}
                    className="h-6 px-1 text-xs text-clay-400 hover:text-clay-200"
                  >
                    {showOutputs.has(rec.id) ? "Hide Outputs" : "Show Outputs"}
                  </Button>
                  {showOutputs.has(rec.id) && (
                    <pre className="mt-1 text-xs text-clay-300 bg-clay-950 p-3 rounded border border-clay-800 overflow-auto max-h-32 whitespace-pre-wrap">
                      {JSON.stringify(rec.outputs, null, 2)}
                    </pre>
                  )}
                </div>

                {/* Execution trace */}
                {rec.trace && rec.trace.length > 0 && (
                  <ExecutionTrace
                    trace={rec.trace}
                    totalDurationMs={rec.duration_ms}
                    stepsTotal={rec.step_count}
                  />
                )}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
