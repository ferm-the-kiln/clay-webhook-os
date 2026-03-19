"use client";

import { useState, useEffect } from "react";
import type { Job } from "@/lib/types";
import { fetchJob } from "@/lib/api";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { cn, formatDuration, formatTimestamp } from "@/lib/utils";
import {
  X,
  Clock,
  Cpu,
  ChevronDown,
  ChevronRight,
  AlertTriangle,
  Copy,
  Check,
} from "lucide-react";

interface RequestDetailProps {
  jobId: string;
  onClose: () => void;
}

function JsonViewer({ data, label }: { data: unknown; label: string }) {
  const [expanded, setExpanded] = useState(true);
  const [copied, setCopied] = useState(false);
  const jsonStr = JSON.stringify(data, null, 2);

  const handleCopy = () => {
    navigator.clipboard.writeText(jsonStr);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className="border border-clay-600 rounded-lg overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center justify-between w-full px-3 py-2 bg-clay-800 hover:bg-clay-750 transition-colors duration-150 text-left"
      >
        <span className="flex items-center gap-2 text-sm font-medium text-clay-200">
          {expanded ? (
            <ChevronDown className="h-3.5 w-3.5" />
          ) : (
            <ChevronRight className="h-3.5 w-3.5" />
          )}
          {label}
        </span>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={(e) => {
            e.stopPropagation();
            handleCopy();
          }}
          className="h-6 w-6 text-clay-400 hover:text-clay-200"
        >
          {copied ? (
            <Check className="h-3 w-3 text-status-success" />
          ) : (
            <Copy className="h-3 w-3" />
          )}
        </Button>
      </button>
      {expanded && (
        <pre className="bg-zinc-900 p-3 text-xs font-mono text-clay-200 overflow-x-auto max-h-96 overflow-y-auto leading-relaxed">
          <SyntaxHighlightedJson json={jsonStr} />
        </pre>
      )}
    </div>
  );
}

function SyntaxHighlightedJson({ json }: { json: string }) {
  // Simple syntax highlighting for JSON
  const highlighted = json.replace(
    /("(?:[^"\\]|\\.)*")(\s*:)?|(\b(?:true|false|null)\b)|(-?\d+(?:\.\d+)?(?:[eE][+-]?\d+)?)/g,
    (match, str, colon, bool, num) => {
      if (str && colon) {
        // Key
        return `<span class="text-kiln-indigo">${str}</span>${colon}`;
      }
      if (str) {
        // String value
        return `<span class="text-status-success">${str}</span>`;
      }
      if (bool) {
        return `<span class="text-kiln-mustard">${bool}</span>`;
      }
      if (num) {
        return `<span class="text-kiln-coral">${num}</span>`;
      }
      return match;
    }
  );

  return <code dangerouslySetInnerHTML={{ __html: highlighted }} />;
}

const STATUS_STYLES: Record<
  string,
  { bg: string; text: string; label: string }
> = {
  completed: {
    bg: "bg-status-success/15",
    text: "text-status-success",
    label: "Completed",
  },
  failed: {
    bg: "bg-kiln-coral/15",
    text: "text-kiln-coral",
    label: "Failed",
  },
  processing: {
    bg: "bg-kiln-mustard/15",
    text: "text-kiln-mustard",
    label: "Processing",
  },
  queued: {
    bg: "bg-clay-500/15",
    text: "text-clay-300",
    label: "Queued",
  },
  retrying: {
    bg: "bg-kiln-mustard/15",
    text: "text-kiln-mustard",
    label: "Retrying",
  },
  dead_letter: {
    bg: "bg-kiln-coral/15",
    text: "text-kiln-coral",
    label: "Dead Letter",
  },
};

export function RequestDetail({ jobId, onClose }: RequestDetailProps) {
  const [job, setJob] = useState<Job | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    fetchJob(jobId)
      .then((j) => setJob(j))
      .catch((e) => setError((e as Error).message))
      .finally(() => setLoading(false));
  }, [jobId]);

  const statusStyle = job
    ? STATUS_STYLES[job.status] || STATUS_STYLES.queued
    : STATUS_STYLES.queued;

  return (
    <div className="border border-clay-500 rounded-lg bg-clay-900 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 bg-clay-800 border-b border-clay-600">
        <div className="flex items-center gap-3 min-w-0">
          <h3 className="text-sm font-medium text-clay-100 truncate">
            Request Detail
          </h3>
          <code className="text-xs text-clay-400 font-mono truncate">
            {jobId}
          </code>
        </div>
        <Button
          variant="ghost"
          size="icon-sm"
          onClick={onClose}
          className="h-7 w-7 text-clay-400 hover:text-clay-200 shrink-0"
        >
          <X className="h-4 w-4" />
        </Button>
      </div>

      {/* Body */}
      <div className="p-4 space-y-4">
        {loading && (
          <div className="flex items-center justify-center py-8">
            <div className="h-5 w-5 border-2 border-clay-500 border-t-kiln-teal rounded-full animate-spin" />
          </div>
        )}

        {error && (
          <div className="flex items-center gap-2 px-3 py-2 bg-kiln-coral/10 border border-kiln-coral/20 rounded-md text-sm text-kiln-coral">
            <AlertTriangle className="h-4 w-4 shrink-0" />
            {error}
          </div>
        )}

        {job && !loading && (
          <>
            {/* Meta row */}
            <div className="flex flex-wrap items-center gap-3">
              <Badge
                className={cn(
                  statusStyle.bg,
                  statusStyle.text,
                  "border-transparent"
                )}
              >
                {statusStyle.label}
              </Badge>
              <span className="flex items-center gap-1.5 text-xs text-clay-300">
                <Cpu className="h-3 w-3" />
                {job.skill}
              </span>
              <span className="flex items-center gap-1.5 text-xs text-clay-300">
                <Clock className="h-3 w-3" />
                {formatDuration(job.duration_ms)}
              </span>
              <span className="text-xs text-clay-400 font-mono">
                {formatTimestamp(job.created_at)}
              </span>
              {job.priority && job.priority !== "normal" && (
                <Badge variant="outline" className="text-xs border-clay-600">
                  {job.priority}
                </Badge>
              )}
            </div>

            {/* Duration breakdown */}
            {job.input_tokens_est !== undefined && (
              <div className="grid grid-cols-3 gap-3">
                <div className="bg-clay-800 rounded-md px-3 py-2 border border-clay-600">
                  <p className="text-[10px] uppercase tracking-wider text-clay-400 mb-0.5">
                    Input Tokens
                  </p>
                  <p className="text-sm font-mono text-clay-200">
                    {(job.input_tokens_est ?? 0).toLocaleString()}
                  </p>
                </div>
                <div className="bg-clay-800 rounded-md px-3 py-2 border border-clay-600">
                  <p className="text-[10px] uppercase tracking-wider text-clay-400 mb-0.5">
                    Output Tokens
                  </p>
                  <p className="text-sm font-mono text-clay-200">
                    {(job.output_tokens_est ?? 0).toLocaleString()}
                  </p>
                </div>
                <div className="bg-clay-800 rounded-md px-3 py-2 border border-clay-600">
                  <p className="text-[10px] uppercase tracking-wider text-clay-400 mb-0.5">
                    Est. Cost
                  </p>
                  <p className="text-sm font-mono text-clay-200">
                    ${(job.cost_est_usd ?? 0).toFixed(4)}
                  </p>
                </div>
              </div>
            )}

            {/* Error message */}
            {job.error && (
              <div className="flex items-start gap-2 px-3 py-2.5 bg-kiln-coral/10 border border-kiln-coral/20 rounded-md">
                <AlertTriangle className="h-4 w-4 text-kiln-coral shrink-0 mt-0.5" />
                <pre className="text-sm text-kiln-coral font-mono whitespace-pre-wrap break-all">
                  {job.error}
                </pre>
              </div>
            )}

            {/* Result JSON */}
            {job.result && (
              <JsonViewer data={job.result} label="Result" />
            )}
          </>
        )}
      </div>
    </div>
  );
}
