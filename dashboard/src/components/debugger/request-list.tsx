"use client";

import { useEffect, useRef } from "react";
import type { JobListItem } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { cn, formatDuration, formatRelativeTime } from "@/lib/utils";
import { Clock, Cpu, AlertCircle } from "lucide-react";

interface RequestListProps {
  jobs: JobListItem[];
  selectedJobId: string | null;
  onSelectJob: (id: string) => void;
  autoScroll: boolean;
}

const STATUS_CONFIG: Record<
  string,
  { bg: string; text: string; dot: string; label: string }
> = {
  completed: {
    bg: "bg-status-success/15",
    text: "text-status-success",
    dot: "bg-status-success",
    label: "Done",
  },
  failed: {
    bg: "bg-kiln-coral/15",
    text: "text-kiln-coral",
    dot: "bg-kiln-coral",
    label: "Failed",
  },
  processing: {
    bg: "bg-kiln-mustard/15",
    text: "text-kiln-mustard",
    dot: "bg-kiln-mustard animate-pulse",
    label: "Running",
  },
  queued: {
    bg: "bg-clay-500/15",
    text: "text-clay-300",
    dot: "bg-clay-400",
    label: "Queued",
  },
  retrying: {
    bg: "bg-kiln-mustard/15",
    text: "text-kiln-mustard",
    dot: "bg-kiln-mustard animate-pulse",
    label: "Retry",
  },
  dead_letter: {
    bg: "bg-kiln-coral/15",
    text: "text-kiln-coral",
    dot: "bg-kiln-coral",
    label: "Dead",
  },
};

export function RequestList({
  jobs,
  selectedJobId,
  onSelectJob,
  autoScroll,
}: RequestListProps) {
  const listRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && listRef.current) {
      listRef.current.scrollTop = 0;
    }
  }, [jobs.length, autoScroll]);

  if (jobs.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-clay-300">
        <AlertCircle className="h-8 w-8 mb-3 opacity-50" />
        <p className="text-sm">No requests yet</p>
        <p className="text-xs text-clay-300 mt-1">
          Requests will appear here in real time
        </p>
      </div>
    );
  }

  return (
    <div
      ref={listRef}
      className="flex-1 overflow-y-auto divide-y divide-clay-700/50"
    >
      {jobs.map((job) => {
        const status =
          STATUS_CONFIG[job.status] || STATUS_CONFIG.queued;
        const isSelected = job.id === selectedJobId;

        return (
          <button
            key={job.id}
            onClick={() => onSelectJob(job.id)}
            className={cn(
              "w-full text-left px-4 py-3 transition-colors duration-100 hover:bg-clay-800/60",
              isSelected && "bg-clay-800 border-l-2 border-kiln-teal"
            )}
          >
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2.5 min-w-0">
                {/* Status dot */}
                <span
                  className={cn(
                    "h-2 w-2 rounded-full shrink-0",
                    status.dot
                  )}
                />
                {/* Skill name */}
                <span className="text-sm font-medium text-clay-100 truncate">
                  {job.skill}
                </span>
                {/* Status badge */}
                <Badge
                  className={cn(
                    "text-[10px] px-1.5 py-0 h-4 border-transparent",
                    status.bg,
                    status.text
                  )}
                >
                  {status.label}
                </Badge>
              </div>
              <div className="flex items-center gap-3 shrink-0">
                {/* Duration */}
                {job.duration_ms > 0 && (
                  <span className="flex items-center gap-1 text-xs text-clay-300 font-mono tabular-nums">
                    <Clock className="h-3 w-3" />
                    {formatDuration(job.duration_ms)}
                  </span>
                )}
                {/* Timestamp */}
                <span className="text-xs text-clay-300 font-mono tabular-nums whitespace-nowrap">
                  {formatRelativeTime(job.created_at)}
                </span>
              </div>
            </div>
            {/* Second row: Job ID + priority */}
            <div className="flex items-center gap-2 mt-1 ml-[18px]">
              <code className="text-[11px] text-clay-300 font-mono truncate">
                {job.id}
              </code>
              {job.priority && job.priority !== "normal" && (
                <Badge
                  variant="outline"
                  className="text-[10px] px-1 py-0 h-3.5 border-clay-600 text-clay-300"
                >
                  {job.priority}
                </Badge>
              )}
              {(job.retry_count ?? 0) > 0 && (
                <span className="flex items-center gap-0.5 text-[10px] text-kiln-mustard">
                  <Cpu className="h-2.5 w-2.5" />
                  retry {job.retry_count}
                </span>
              )}
            </div>
          </button>
        );
      })}
    </div>
  );
}
