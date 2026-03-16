"use client";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { Play, Loader2, CheckCircle2, AlertCircle } from "lucide-react";
import type { StageStatus } from "@/lib/types";

interface ActionCardProps {
  title: string;
  description: string;
  icon: React.ElementType;
  onRun: () => void;
  disabled?: boolean;
  running?: boolean;
  stageStatus?: StageStatus | null;
  children?: React.ReactNode;
}

export function ActionCard({
  title,
  description,
  icon: Icon,
  onRun,
  disabled,
  running,
  stageStatus,
  children,
}: ActionCardProps) {
  const isDone = stageStatus?.status === "completed";
  const isFailed = stageStatus?.status === "failed";
  const isRunning = running || stageStatus?.status === "running";
  const progress =
    stageStatus && stageStatus.total > 0
      ? ((stageStatus.completed + stageStatus.failed) / stageStatus.total) * 100
      : 0;

  return (
    <div
      className={cn(
        "border rounded-lg p-3 transition-colors",
        isDone
          ? "border-kiln-teal/30 bg-kiln-teal/5"
          : isRunning
            ? "border-kiln-teal/20 bg-clay-800"
            : "border-clay-600 bg-clay-800/50 hover:border-clay-500"
      )}
    >
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-start gap-2.5 min-w-0">
          <Icon className={cn("h-4 w-4 mt-0.5 shrink-0", isDone ? "text-kiln-teal" : "text-clay-300")} />
          <div className="min-w-0">
            <h4 className="text-sm font-medium text-clay-100">{title}</h4>
            <p className="text-xs text-clay-300 mt-0.5">{description}</p>
          </div>
        </div>
        <Button
          size="sm"
          onClick={onRun}
          disabled={disabled || isRunning}
          className={cn(
            "shrink-0 h-7 px-2.5 text-xs",
            isDone
              ? "bg-clay-700 text-clay-200 hover:bg-clay-600"
              : "bg-kiln-teal text-clay-900 hover:bg-kiln-teal/90"
          )}
        >
          {isRunning ? (
            <Loader2 className="h-3 w-3 animate-spin" />
          ) : isDone ? (
            <>
              <CheckCircle2 className="h-3 w-3 mr-1" />
              Done
            </>
          ) : (
            <>
              <Play className="h-3 w-3 mr-1" />
              Run
            </>
          )}
        </Button>
      </div>

      {/* Inline config */}
      {children && <div className="mt-2.5 pl-6.5">{children}</div>}

      {/* Progress bar */}
      {isRunning && stageStatus && (
        <div className="mt-2.5">
          <div className="flex items-center justify-between text-[10px] text-clay-300 mb-1">
            <span>
              {stageStatus.completed}/{stageStatus.total} processed
            </span>
            {stageStatus.failed > 0 && (
              <span className="text-kiln-coral flex items-center gap-0.5">
                <AlertCircle className="h-2.5 w-2.5" />
                {stageStatus.failed} failed
              </span>
            )}
          </div>
          <div className="w-full bg-clay-700 rounded-full h-1.5">
            <div
              className="bg-kiln-teal h-1.5 rounded-full transition-all duration-300"
              style={{ width: `${progress}%` }}
            />
          </div>
        </div>
      )}

      {/* Completion stats */}
      {isDone && stageStatus && (
        <div className="mt-2 flex items-center gap-2 text-[10px]">
          <span className="px-1.5 py-0.5 rounded bg-kiln-teal/10 text-kiln-teal">
            {stageStatus.completed} done
          </span>
          {stageStatus.failed > 0 && (
            <span className="px-1.5 py-0.5 rounded bg-kiln-coral/10 text-kiln-coral">
              {stageStatus.failed} failed
            </span>
          )}
        </div>
      )}
    </div>
  );
}
