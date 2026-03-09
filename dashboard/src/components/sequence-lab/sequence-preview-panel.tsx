"use client";

import { cn } from "@/lib/utils";
import {
  ListOrdered,
  Clock,
  Cpu,
  ChevronDown,
  Trash2,
  Copy,
  Check,
  Mail,
  Linkedin,
  Phone,
  Download,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { PushToDestination } from "@/components/shared/push-to-destination";
import type { WebhookResponse } from "@/lib/types";
import type { SequenceLabRun } from "@/lib/sequence-lab-constants";
import { SEQUENCE_TYPE_COLORS, type SequenceType } from "@/lib/sequence-lab-constants";
import { TouchCard } from "./touch-card";
import { useState, useEffect } from "react";

const QUICKSTART_DISMISSED_KEY = "sequence-lab-quickstart-dismissed";

function formatDuration(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
}

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

interface Touch {
  touch_number: number;
  channel: string;
  wait_days: number;
  subject?: string;
  body: string;
  tone_note?: string;
  purpose?: string;
}

export function SequencePreviewPanel({
  result,
  loading,
  error,
  history,
  onRestore,
  onClearHistory,
  onTryItNow,
}: {
  result: WebhookResponse | null;
  loading: boolean;
  error: string | null;
  history: SequenceLabRun[];
  onRestore: (run: SequenceLabRun) => void;
  onClearHistory: () => void;
  onTryItNow?: () => void;
}) {
  const [detailsOpen, setDetailsOpen] = useState(false);
  const [copiedJson, setCopiedJson] = useState(false);
  const [copiedAll, setCopiedAll] = useState(false);
  const [quickstartDismissed, setQuickstartDismissed] = useState(true);

  useEffect(() => {
    if (typeof window !== "undefined") {
      setQuickstartDismissed(
        localStorage.getItem(QUICKSTART_DISMISSED_KEY) === "true"
      );
    }
  }, []);

  useEffect(() => {
    if (result && !quickstartDismissed) {
      localStorage.setItem(QUICKSTART_DISMISSED_KEY, "true");
      setQuickstartDismissed(true);
    }
  }, [result, quickstartDismissed]);

  // Extract sequence fields
  const sequenceName = result?.sequence_name as string | undefined;
  const sequenceType = result?.sequence_type as SequenceType | undefined;
  const touches = (result?.touches ?? result?.sequence ?? []) as Touch[];
  const personalizationThread = result?.personalization_thread as string | undefined;
  const confidence = result?.confidence_score as number | undefined;
  const angleReasoning = result?.angle_reasoning as string | undefined;
  const angleUsed = result?.angle_used as string | undefined;
  const meta = result?._meta;

  // Compute cadence
  const cadenceDays = touches.map((t) => t.wait_days ?? 0);
  let cumulativeDays = 0;
  const dayMarkers = cadenceDays.map((d) => {
    cumulativeDays += d;
    return cumulativeDays;
  });
  const totalDuration = dayMarkers[dayMarkers.length - 1] ?? 0;

  // Channel mix counts
  const channelCounts = touches.reduce<Record<string, number>>((acc, t) => {
    acc[t.channel] = (acc[t.channel] ?? 0) + 1;
    return acc;
  }, {});
  const totalTouches = touches.length;

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(result, null, 2));
    setCopiedJson(true);
    setTimeout(() => setCopiedJson(false), 2000);
  };

  // Copy all touches as formatted text (Rec #2)
  const handleCopyAllTouches = () => {
    const lines = touches.map((t) => {
      const dayLabel = `Day ${dayMarkers[t.touch_number - 1] ?? 0}`;
      const parts = [`Touch ${t.touch_number} — ${dayLabel} — ${t.channel.toUpperCase()}`];
      if (t.subject) parts.push(`Subject: ${t.subject}`);
      parts.push("", t.body);
      if (t.tone_note) parts.push(`[Tone: ${t.tone_note}]`);
      return parts.join("\n");
    });
    navigator.clipboard.writeText(lines.join("\n\n---\n\n"));
    setCopiedAll(true);
    setTimeout(() => setCopiedAll(false), 2000);
  };

  // Export as CSV (Rec #2)
  const handleExportCsv = () => {
    const headers = ["Touch", "Day", "Channel", "Subject", "Body", "Tone", "Purpose"];
    const rows = touches.map((t) => [
      t.touch_number,
      dayMarkers[t.touch_number - 1] ?? 0,
      t.channel,
      t.subject ?? "",
      t.body.replace(/"/g, '""'),
      t.tone_note ?? "",
      t.purpose ?? "",
    ]);
    const csv = [
      headers.join(","),
      ...rows.map((r) => r.map((c) => `"${c}"`).join(",")),
    ].join("\n");

    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${sequenceName ?? "sequence"}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="flex flex-col h-full overflow-y-auto">
      {/* Preview section */}
      <div className="flex-1 p-3 space-y-3 min-h-0 overflow-y-auto">
        {error && (
          <div className="rounded-lg border border-red-500/30 bg-red-500/5 p-3">
            <p className="text-sm text-red-400">{error}</p>
          </div>
        )}

        {loading && !result && (
          <div className="flex flex-col items-center justify-center h-full gap-3 text-clay-300">
            <div className="h-8 w-8 rounded-full border-2 border-kiln-teal border-t-transparent animate-spin" />
            <p className="text-sm">Generating sequence...</p>
          </div>
        )}

        {/* Guided empty state (Rec #3) */}
        {!result && !loading && !error && (
          <div className="flex flex-col items-center justify-center h-full gap-4 text-clay-300 px-4">
            {!quickstartDismissed ? (
              <>
                <Sparkles className="h-10 w-10 text-kiln-teal/60" />
                <div className="text-center space-y-3 max-w-xs">
                  <h3 className="text-sm font-semibold text-clay-100">
                    Welcome to Sequence Lab
                  </h3>
                  <div className="space-y-2 text-xs text-clay-300">
                    <div className="flex items-start gap-2">
                      <span className="shrink-0 h-5 w-5 rounded-full bg-kiln-teal/15 text-kiln-teal flex items-center justify-center text-[10px] font-bold">
                        1
                      </span>
                      <span>
                        Pick a template
                        <ArrowRight className="inline h-3 w-3 mx-1 text-clay-500" />
                        or enter prospect details
                      </span>
                    </div>
                    <div className="flex items-start gap-2">
                      <span className="shrink-0 h-5 w-5 rounded-full bg-kiln-teal/15 text-kiln-teal flex items-center justify-center text-[10px] font-bold">
                        2
                      </span>
                      <span>Choose sequence type: Cold, LinkedIn-First, or Warm Intro</span>
                    </div>
                    <div className="flex items-start gap-2">
                      <span className="shrink-0 h-5 w-5 rounded-full bg-kiln-teal/15 text-kiln-teal flex items-center justify-center text-[10px] font-bold">
                        3
                      </span>
                      <span>
                        Hit <kbd className="text-[9px] bg-clay-700 px-1 py-0.5 rounded mx-0.5">{"\u2318\u21A9"}</kbd> to generate your multi-touch sequence
                      </span>
                    </div>
                  </div>
                  {onTryItNow && (
                    <Button
                      onClick={onTryItNow}
                      className="mt-2 bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light text-xs font-semibold"
                      size="sm"
                    >
                      <Sparkles className="h-3.5 w-3.5 mr-1.5" />
                      Try it now
                    </Button>
                  )}
                </div>
              </>
            ) : (
              <>
                <ListOrdered className="h-8 w-8 text-clay-500" />
                <p className="text-sm text-clay-300">
                  Select a template and run to preview
                </p>
              </>
            )}
          </div>
        )}

        {result && touches.length > 0 && (
          <>
            {/* Sequence header */}
            <div className="rounded-xl border border-clay-700 bg-clay-800/30 p-3 space-y-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2 min-w-0">
                  {sequenceName && (
                    <span className="text-sm font-semibold text-clay-100 truncate">
                      {sequenceName}
                    </span>
                  )}
                  {sequenceType && (
                    <span
                      className={cn(
                        "text-[10px] px-1.5 py-0.5 rounded-full font-medium shrink-0",
                        SEQUENCE_TYPE_COLORS[sequenceType] ?? "bg-clay-500/15 text-clay-300"
                      )}
                    >
                      {sequenceType}
                    </span>
                  )}
                  {confidence !== undefined && (
                    <span
                      className={cn(
                        "text-[10px] px-1.5 py-0.5 rounded-full border shrink-0",
                        confidence >= 0.8
                          ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                          : confidence >= 0.5
                            ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                            : "bg-red-500/10 text-red-400 border-red-500/20"
                      )}
                    >
                      {(confidence * 100).toFixed(0)}%
                    </span>
                  )}
                </div>
                {/* Copy/Export buttons (Rec #2) */}
                <div className="flex items-center gap-1 shrink-0">
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleCopyAllTouches}
                    className="h-7 text-xs text-clay-300 hover:text-clay-100"
                    title="Copy all touches as formatted text"
                  >
                    {copiedAll ? (
                      <Check className="h-3.5 w-3.5 mr-1 text-emerald-400" />
                    ) : (
                      <Copy className="h-3.5 w-3.5 mr-1" />
                    )}
                    {copiedAll ? "Copied" : "Copy All"}
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleExportCsv}
                    className="h-7 text-[10px] text-clay-400 hover:text-clay-200 px-1.5"
                    title="Export as CSV"
                  >
                    <Download className="h-3 w-3" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    onClick={handleCopyJson}
                    className="h-7 text-[10px] text-clay-400 hover:text-clay-200 px-1.5"
                    title="Copy raw JSON"
                  >
                    {copiedJson ? (
                      <Check className="h-3 w-3 text-emerald-400" />
                    ) : (
                      <span>JSON</span>
                    )}
                  </Button>
                </div>
              </div>

              {/* Cadence strip */}
              <div className="flex items-center gap-1.5 flex-wrap">
                {dayMarkers.map((day, i) => (
                  <span key={i} className="flex items-center gap-1.5">
                    <span className="text-[11px] font-mono text-clay-200 bg-clay-700/60 px-1.5 py-0.5 rounded">
                      Day {day}
                    </span>
                    {i < dayMarkers.length - 1 && (
                      <span className="text-clay-500 text-[10px]">&rarr;</span>
                    )}
                  </span>
                ))}
                {totalDuration > 0 && (
                  <span className="text-[10px] px-1.5 py-0.5 rounded-full bg-kiln-teal/10 text-kiln-teal border border-kiln-teal/20 ml-1">
                    {totalDuration}-day sequence
                  </span>
                )}
              </div>

              {/* Channel mix bar */}
              {totalTouches > 0 && (
                <div className="space-y-1">
                  <div className="flex h-2 rounded-full overflow-hidden bg-clay-700/30">
                    {channelCounts.email && (
                      <div
                        className="bg-blue-400/60 h-full"
                        style={{ width: `${(channelCounts.email / totalTouches) * 100}%` }}
                      />
                    )}
                    {channelCounts.linkedin && (
                      <div
                        className="bg-purple-400/60 h-full"
                        style={{ width: `${(channelCounts.linkedin / totalTouches) * 100}%` }}
                      />
                    )}
                    {channelCounts.phone && (
                      <div
                        className="bg-emerald-400/60 h-full"
                        style={{ width: `${(channelCounts.phone / totalTouches) * 100}%` }}
                      />
                    )}
                  </div>
                  <div className="flex gap-3 text-[10px] text-clay-300">
                    {channelCounts.email && (
                      <span className="flex items-center gap-1">
                        <Mail className="h-3 w-3 text-blue-400" />
                        {channelCounts.email} email
                      </span>
                    )}
                    {channelCounts.linkedin && (
                      <span className="flex items-center gap-1">
                        <Linkedin className="h-3 w-3 text-purple-400" />
                        {channelCounts.linkedin} linkedin
                      </span>
                    )}
                    {channelCounts.phone && (
                      <span className="flex items-center gap-1">
                        <Phone className="h-3 w-3 text-emerald-400" />
                        {channelCounts.phone} phone
                      </span>
                    )}
                  </div>
                </div>
              )}
            </div>

            {/* Personalization thread */}
            {personalizationThread && (
              <div className="rounded-lg border border-kiln-teal/20 bg-kiln-teal/5 px-3 py-2">
                <p className="text-[10px] text-kiln-teal uppercase tracking-wider mb-0.5 font-semibold">
                  Personalization Thread
                </p>
                <p className="text-sm text-clay-200 leading-relaxed">
                  {personalizationThread}
                </p>
              </div>
            )}

            {/* Touch timeline */}
            <div className="space-y-0">
              {touches.map((touch, i) => (
                <TouchCard
                  key={i}
                  touch={touch}
                  isLast={i === touches.length - 1}
                  defaultExpanded={i < 3}
                />
              ))}
            </div>

            {/* Metadata chips */}
            <div className="flex flex-wrap gap-2">
              {angleUsed && (
                <span className="text-[11px] px-2 py-1 rounded-full bg-kiln-teal/10 text-kiln-teal border border-kiln-teal/20">
                  {angleUsed}
                </span>
              )}
              {meta && (
                <>
                  <span className="text-[11px] px-2 py-1 rounded-full bg-clay-700/50 text-clay-300 flex items-center gap-1">
                    <Cpu className="h-3 w-3" />
                    {meta.model}
                  </span>
                  <span className="text-[11px] px-2 py-1 rounded-full bg-clay-700/50 text-clay-300 flex items-center gap-1">
                    <Clock className="h-3 w-3" />
                    {formatDuration(meta.duration_ms)}
                  </span>
                </>
              )}
            </div>

            {/* Push to Clay (Rec #9) */}
            <div className="flex justify-end">
              <PushToDestination data={result as Record<string, unknown>} />
            </div>

            {/* Collapsible details */}
            {(angleReasoning || meta) && (
              <button
                onClick={() => setDetailsOpen(!detailsOpen)}
                className="flex items-center gap-1.5 text-xs text-clay-300 hover:text-clay-200 transition-colors"
              >
                <ChevronDown
                  className={cn(
                    "h-3.5 w-3.5 transition-transform",
                    detailsOpen && "rotate-180"
                  )}
                />
                Details
              </button>
            )}

            {detailsOpen && (
              <div className="rounded-lg border border-clay-700 bg-clay-800/30 p-3 space-y-2 text-xs">
                {angleReasoning && (
                  <div>
                    <p className="text-clay-300 font-medium mb-0.5">
                      Angle Reasoning
                    </p>
                    <p className="text-clay-200">{angleReasoning}</p>
                  </div>
                )}
                {meta && (
                  <div className="flex gap-4 text-clay-300 pt-1 border-t border-clay-700">
                    {meta.input_tokens_est && (
                      <span>In: ~{meta.input_tokens_est.toLocaleString()} tok</span>
                    )}
                    {meta.output_tokens_est && (
                      <span>Out: ~{meta.output_tokens_est.toLocaleString()} tok</span>
                    )}
                    {meta.cached && (
                      <span className="text-kiln-teal">Cached</span>
                    )}
                  </div>
                )}
              </div>
            )}
          </>
        )}

        {/* Fallback: result exists but no touches parsed */}
        {result && touches.length === 0 && (
          <div className="rounded-xl border border-clay-700 overflow-hidden">
            <div className="bg-clay-800/80 px-4 py-3 border-b border-clay-700 flex items-center justify-between">
              <span className="text-xs text-clay-300">Raw Output</span>
              <Button
                variant="ghost"
                size="sm"
                onClick={handleCopyJson}
                className="h-7 text-xs text-clay-300 hover:text-clay-100"
              >
                {copiedJson ? (
                  <Check className="h-3.5 w-3.5 mr-1 text-emerald-400" />
                ) : (
                  <Copy className="h-3.5 w-3.5 mr-1" />
                )}
                {copiedJson ? "Copied" : "Copy"}
              </Button>
            </div>
            <pre className="px-4 py-4 text-xs text-clay-200 font-[family-name:var(--font-mono)] overflow-x-auto">
              {JSON.stringify(result, null, 2)}
            </pre>
          </div>
        )}
      </div>

      {/* History section */}
      {history.length > 0 && (
        <div className="border-t border-clay-700 p-3">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-[11px] font-semibold text-clay-300 uppercase tracking-[0.1em]">
              History
            </h3>
            <Button
              variant="ghost"
              size="sm"
              onClick={onClearHistory}
              className="h-6 text-[10px] text-clay-300 hover:text-red-400 px-1.5"
            >
              <Trash2 className="h-3 w-3" />
            </Button>
          </div>
          <div className="space-y-1 max-h-40 overflow-y-auto">
            {history.slice(0, 10).map((run) => (
              <button
                key={run.id}
                onClick={() => onRestore(run)}
                className="w-full text-left px-2.5 py-1.5 rounded-md text-xs hover:bg-clay-700/50 transition-colors group"
              >
                <div className="flex items-center justify-between">
                  <span className="text-clay-200 truncate">
                    {(run.data.company_name as string) || "Sequence"}
                  </span>
                  <span className="text-[10px] text-clay-300 shrink-0 ml-2">
                    {formatDuration(run.durationMs)}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-[10px] text-clay-300">
                  <span>{(run.data.sequence_type as string) || "cold"}</span>
                  <span>&middot;</span>
                  <span>{run.model}</span>
                  <span>&middot;</span>
                  <span>{formatTime(run.timestamp)}</span>
                </div>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
