"use client";

import { cn } from "@/lib/utils";
import {
  Mail,
  Clock,
  Cpu,
  ChevronDown,
  Trash2,
  Copy,
  Check,
  Bookmark,
  RefreshCw,
  GitCompareArrows,
  Loader2,
  Pencil,
  Save,
  X,
  ShieldCheck,
  AlertTriangle,
  CircleAlert,
  Info,
  Sparkles,
  ArrowRight,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import { FeedbackButtons } from "@/components/feedback/feedback-buttons";
import { PushToDestination } from "@/components/shared/push-to-destination";
import type { WebhookResponse } from "@/lib/types";
import type { EmailLabRun } from "@/lib/email-lab-constants";
import type { QualityCheckResult } from "@/hooks/use-email-lab";
import { useState, useEffect } from "react";

const QUICKSTART_DISMISSED_KEY = "email-lab-quickstart-dismissed";

function formatDuration(ms: number): string {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)}s` : `${ms}ms`;
}

function formatTime(ts: number): string {
  return new Date(ts).toLocaleTimeString([], {
    hour: "2-digit",
    minute: "2-digit",
  });
}

// ─── Feature 1: Word Count + Read Time ───

function computeEmailStats(body: string) {
  const trimmed = body.trim();
  if (!trimmed) return { words: 0, sentences: 0, readTimeSec: 0, inRange: true };
  const words = trimmed.split(/\s+/).length;
  const sentences = trimmed.split(/[.!?]+/).filter((s) => s.trim()).length;
  const readTimeSec = Math.ceil((words / 200) * 60); // 200 WPM average
  const inRange = words >= 50 && words <= 125;
  return { words, sentences, readTimeSec, inRange };
}

export function EmailPreviewPanel({
  result,
  loading,
  error,
  history,
  onRestore,
  onClearHistory,
  currentRunId,
  onSaveAsTemplate,
  onCompareOpen,
  subjectAlts,
  regenLoading,
  onRegenSubjectLines,
  onSelectSubjectAlt,
  isEditing = false,
  onSetEditing,
  editedBody = "",
  onSetEditedBody,
  onSaveEdits,
  qualityResult = null,
  qualityLoading = false,
  autoQualityCheck = true,
  onSetAutoQualityCheck,
  onTryItNow,
}: {
  result: WebhookResponse | null;
  loading: boolean;
  error: string | null;
  history: EmailLabRun[];
  onRestore: (run: EmailLabRun) => void;
  onClearHistory: () => void;
  currentRunId: string | null;
  onSaveAsTemplate: (name: string) => void;
  onCompareOpen: () => void;
  subjectAlts: string[];
  regenLoading: boolean;
  onRegenSubjectLines: () => void;
  onSelectSubjectAlt: (alt: string) => void;
  isEditing?: boolean;
  onSetEditing?: (v: boolean) => void;
  editedBody?: string;
  onSetEditedBody?: (v: string) => void;
  onSaveEdits?: () => void;
  qualityResult?: QualityCheckResult | null;
  qualityLoading?: boolean;
  autoQualityCheck?: boolean;
  onSetAutoQualityCheck?: (v: boolean) => void;
  onTryItNow?: () => void;
}) {
  const [metaOpen, setMetaOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [copiedPlain, setCopiedPlain] = useState(false);
  const [savingTemplate, setSavingTemplate] = useState(false);
  const [templateName, setTemplateName] = useState("");
  const [qualityOpen, setQualityOpen] = useState(false);
  const [quickstartDismissed, setQuickstartDismissed] = useState(true);

  // Check quickstart dismissal
  useEffect(() => {
    if (typeof window !== "undefined") {
      setQuickstartDismissed(
        localStorage.getItem(QUICKSTART_DISMISSED_KEY) === "true"
      );
    }
  }, []);

  // Auto-dismiss quickstart after first successful result
  useEffect(() => {
    if (result && !quickstartDismissed) {
      localStorage.setItem(QUICKSTART_DISMISSED_KEY, "true");
      setQuickstartDismissed(true);
    }
  }, [result, quickstartDismissed]);

  // Extract email fields
  const subject =
    (result?.subject as string) ||
    (result?.subject_line as string) ||
    (result?.email_subject as string) ||
    "";
  const body =
    (result?.body as string) ||
    (result?.email_body as string) ||
    (result?.email as string) ||
    "";
  const cta =
    (result?.cta as string) ||
    (result?.call_to_action as string) ||
    "";
  const wasEdited = result?._edited as boolean | undefined;

  // Metadata fields
  const meta = result?._meta;
  const angle = result?.angle_used as string | undefined;
  const angleReasoning = result?.angle_reasoning as string | undefined;
  const frameworkNotes = result?.framework_notes as string | undefined;
  const confidence = result?.confidence_score as number | undefined;

  // Feature 1: Word count stats
  const stats = computeEmailStats(isEditing ? editedBody : body);

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(result, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const handleCopyPlain = () => {
    const text = subject
      ? `Subject: ${subject}\n\n${body}${cta ? `\n\n${cta}` : ""}`
      : body || JSON.stringify(result, null, 2);
    navigator.clipboard.writeText(text);
    setCopiedPlain(true);
    setTimeout(() => setCopiedPlain(false), 2000);
  };

  const handleSaveTemplate = () => {
    if (!templateName.trim()) return;
    onSaveAsTemplate(templateName.trim());
    setTemplateName("");
    setSavingTemplate(false);
  };

  const handleStartEdit = () => {
    onSetEditedBody?.(body);
    onSetEditing?.(true);
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
            <p className="text-sm">Generating email...</p>
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
                    Welcome to Email Lab
                  </h3>
                  <div className="space-y-2 text-xs text-clay-300">
                    <div className="flex items-start gap-2">
                      <span className="shrink-0 h-5 w-5 rounded-full bg-kiln-teal/15 text-kiln-teal flex items-center justify-center text-[10px] font-bold">
                        1
                      </span>
                      <span>
                        Pick a template from the left panel
                        <ArrowRight className="inline h-3 w-3 mx-1 text-clay-300" />
                        or fill in prospect data
                      </span>
                    </div>
                    <div className="flex items-start gap-2">
                      <span className="shrink-0 h-5 w-5 rounded-full bg-kiln-teal/15 text-kiln-teal flex items-center justify-center text-[10px] font-bold">
                        2
                      </span>
                      <span>Customize tone and instructions (optional)</span>
                    </div>
                    <div className="flex items-start gap-2">
                      <span className="shrink-0 h-5 w-5 rounded-full bg-kiln-teal/15 text-kiln-teal flex items-center justify-center text-[10px] font-bold">
                        3
                      </span>
                      <span>
                        Hit <kbd className="text-[9px] bg-clay-700 px-1 py-0.5 rounded mx-0.5">{"\u2318\u21A9"}</kbd> to run
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
                <Mail className="h-8 w-8 text-clay-300" />
                <p className="text-sm text-clay-300">
                  Select a template and run to preview
                </p>
              </>
            )}
          </div>
        )}

        {result && (
          <>
            {/* Mail chrome */}
            <div className="rounded-xl border border-clay-700 overflow-hidden">
              {/* Mail header */}
              <div className="bg-clay-800/80 px-4 py-3 border-b border-clay-700 space-y-1.5">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <div className="h-7 w-7 rounded-full bg-kiln-teal/15 flex items-center justify-center">
                      <Mail className="h-3.5 w-3.5 text-kiln-teal" />
                    </div>
                    <span className="text-xs text-clay-300">
                      New Email
                      {wasEdited && (
                        <span className="ml-1.5 text-[9px] px-1.5 py-0.5 rounded-full bg-amber-500/15 text-amber-400 border border-amber-500/20">
                          Edited
                        </span>
                      )}
                    </span>
                  </div>
                  <div className="flex items-center gap-1">
                    {/* Save as template */}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setSavingTemplate(!savingTemplate)}
                      className="h-7 text-xs text-clay-300 hover:text-kiln-teal"
                      title="Save as template"
                    >
                      <Bookmark className="h-3.5 w-3.5" />
                    </Button>
                    {/* Edit toggle */}
                    {onSetEditing && (
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={isEditing ? () => onSetEditing(false) : handleStartEdit}
                        className={cn(
                          "h-7 text-xs",
                          isEditing
                            ? "text-amber-400 hover:text-amber-300"
                            : "text-clay-300 hover:text-clay-100"
                        )}
                        title={isEditing ? "Cancel editing" : "Edit email"}
                      >
                        {isEditing ? <X className="h-3.5 w-3.5" /> : <Pencil className="h-3.5 w-3.5" />}
                      </Button>
                    )}
                    {/* Copy as plain text (Rec #2) */}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleCopyPlain}
                      className="h-7 text-xs text-clay-300 hover:text-clay-100"
                      title="Copy email as plain text"
                    >
                      {copiedPlain ? (
                        <Check className="h-3.5 w-3.5 mr-1 text-emerald-400" />
                      ) : (
                        <Copy className="h-3.5 w-3.5 mr-1" />
                      )}
                      {copiedPlain ? "Copied" : "Copy Email"}
                    </Button>
                    {/* Copy as JSON */}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleCopyJson}
                      className="h-7 text-[10px] text-clay-300 hover:text-clay-200 px-1.5"
                      title="Copy raw JSON"
                    >
                      {copied ? (
                        <Check className="h-3 w-3 text-emerald-400" />
                      ) : (
                        <span>JSON</span>
                      )}
                    </Button>
                  </div>
                </div>

                {/* Save template inline input */}
                {savingTemplate && (
                  <div className="flex items-center gap-2 pl-9">
                    <input
                      type="text"
                      value={templateName}
                      onChange={(e) => setTemplateName(e.target.value)}
                      onKeyDown={(e) => e.key === "Enter" && handleSaveTemplate()}
                      placeholder="Template name..."
                      className="flex-1 text-xs bg-clay-950 border border-clay-600 rounded px-2 py-1 text-clay-200 outline-none focus:border-kiln-teal"
                      autoFocus
                    />
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={handleSaveTemplate}
                      disabled={!templateName.trim()}
                      className="h-6 text-[10px] text-kiln-teal hover:text-kiln-teal-light px-2"
                    >
                      Save
                    </Button>
                  </div>
                )}

                {/* Subject + regen button */}
                {subject && (
                  <div className="flex items-start gap-1.5 pl-9">
                    <p className="text-sm font-medium text-clay-100 flex-1">
                      {subject}
                    </p>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={onRegenSubjectLines}
                      disabled={regenLoading}
                      className="h-6 w-6 p-0 text-clay-300 hover:text-kiln-teal shrink-0"
                      title="Generate alternative subject lines"
                    >
                      {regenLoading ? (
                        <Loader2 className="h-3 w-3 animate-spin" />
                      ) : (
                        <RefreshCw className="h-3 w-3" />
                      )}
                    </Button>
                  </div>
                )}

                {/* Subject alternatives */}
                {subjectAlts.length > 0 && (
                  <div className="pl-9 space-y-1">
                    <p className="text-[10px] text-clay-300 uppercase tracking-wider">
                      Alternatives
                    </p>
                    {subjectAlts.map((alt, i) => (
                      <button
                        key={i}
                        onClick={() => onSelectSubjectAlt(alt)}
                        className="block w-full text-left text-xs text-clay-200 hover:text-kiln-teal px-2 py-1 rounded hover:bg-kiln-teal/5 transition-colors"
                      >
                        {alt}
                      </button>
                    ))}
                  </div>
                )}
              </div>

              {/* Mail body — with inline editing (Rec #7) */}
              <div className="px-4 py-4">
                {isEditing ? (
                  <div className="space-y-2">
                    <textarea
                      value={editedBody}
                      onChange={(e) => onSetEditedBody?.(e.target.value)}
                      className="w-full min-h-[120px] resize-y bg-clay-950 border border-kiln-teal/30 rounded-lg p-3 text-sm text-clay-200 leading-relaxed outline-none focus:border-kiln-teal"
                      autoFocus
                    />
                    <div className="flex items-center gap-2">
                      <Button
                        size="sm"
                        onClick={onSaveEdits}
                        className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light text-xs h-7"
                      >
                        <Save className="h-3 w-3 mr-1" />
                        Save edits
                      </Button>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => onSetEditing?.(false)}
                        className="text-xs text-clay-300 h-7"
                      >
                        Cancel
                      </Button>
                    </div>
                  </div>
                ) : body ? (
                  <p className="text-sm text-clay-200 whitespace-pre-wrap leading-relaxed">
                    {body}
                  </p>
                ) : (
                  <pre className="text-xs text-clay-200 font-[family-name:var(--font-mono)] overflow-x-auto">
                    {JSON.stringify(result, null, 2)}
                  </pre>
                )}
              </div>

              {/* CTA */}
              {cta && !isEditing && (
                <div className="mx-4 mb-4 rounded-md bg-kiln-teal/10 border border-kiln-teal/20 px-3 py-2">
                  <p className="text-[10px] text-clay-300 uppercase tracking-wider mb-0.5">
                    Call to Action
                  </p>
                  <p className="text-sm font-medium text-kiln-teal">{cta}</p>
                </div>
              )}
            </div>

            {/* Quality gate badges (Rec #5) */}
            {qualityLoading && (
              <div className="flex items-center gap-2 px-3 py-2 rounded-lg border border-clay-700 bg-clay-800/30 text-[11px] text-clay-300">
                <Loader2 className="h-3 w-3 animate-spin" />
                Checking quality...
              </div>
            )}
            {qualityResult && (
              <div className="space-y-1.5">
                <button
                  onClick={() => setQualityOpen(!qualityOpen)}
                  className={cn(
                    "w-full flex items-center gap-2 px-3 py-2 rounded-lg border text-[11px] transition-colors",
                    qualityResult.passed
                      ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-400"
                      : qualityResult.issues.some((i) => i.severity === "error")
                        ? "bg-red-500/5 border-red-500/20 text-red-400"
                        : "bg-amber-500/5 border-amber-500/20 text-amber-400"
                  )}
                >
                  {qualityResult.passed ? (
                    <ShieldCheck className="h-3.5 w-3.5" />
                  ) : qualityResult.issues.some((i) => i.severity === "error") ? (
                    <CircleAlert className="h-3.5 w-3.5" />
                  ) : (
                    <AlertTriangle className="h-3.5 w-3.5" />
                  )}
                  <span className="font-medium">
                    {qualityResult.passed
                      ? "Passed quality check"
                      : `${qualityResult.issues.length} suggestion${qualityResult.issues.length > 1 ? "s" : ""}`}
                  </span>
                  {qualityResult.issues.length > 0 && (
                    <ChevronDown
                      className={cn(
                        "h-3 w-3 ml-auto transition-transform",
                        qualityOpen && "rotate-180"
                      )}
                    />
                  )}
                </button>
                {qualityOpen && qualityResult.issues.length > 0 && (
                  <div className="rounded-lg border border-clay-700 bg-clay-800/30 p-2 space-y-1.5">
                    {qualityResult.issues.map((issue, i) => (
                      <div key={i} className="flex items-start gap-2 text-xs">
                        {issue.severity === "error" ? (
                          <CircleAlert className="h-3.5 w-3.5 text-red-400 shrink-0 mt-0.5" />
                        ) : issue.severity === "info" ? (
                          <Info className="h-3.5 w-3.5 text-blue-400 shrink-0 mt-0.5" />
                        ) : (
                          <AlertTriangle className="h-3.5 w-3.5 text-amber-400 shrink-0 mt-0.5" />
                        )}
                        <span className="text-clay-200">{issue.message}</span>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Quality gate toggle */}
            {onSetAutoQualityCheck && (
              <div className="flex items-center justify-between text-[10px] text-clay-300">
                <span>Auto-check quality</span>
                <button
                  onClick={() => onSetAutoQualityCheck(!autoQualityCheck)}
                  className={cn(
                    "relative w-7 h-4 rounded-full transition-colors",
                    autoQualityCheck ? "bg-kiln-teal/60" : "bg-clay-600"
                  )}
                >
                  <span
                    className={cn(
                      "absolute top-0.5 h-3 w-3 rounded-full bg-white transition-transform",
                      autoQualityCheck ? "translate-x-3.5" : "translate-x-0.5"
                    )}
                  />
                </button>
              </div>
            )}

            {/* Word count + read time stats bar */}
            {body && !isEditing && (
              <div
                className={cn(
                  "flex items-center gap-3 px-3 py-2 rounded-lg border text-[11px]",
                  stats.inRange
                    ? "bg-emerald-500/5 border-emerald-500/20 text-emerald-400"
                    : "bg-amber-500/5 border-amber-500/20 text-amber-400"
                )}
              >
                <span className="font-medium">{stats.words} words</span>
                <span className="text-clay-300">&middot;</span>
                <span>{stats.sentences} sentences</span>
                <span className="text-clay-300">&middot;</span>
                <span>~{stats.readTimeSec}s read</span>
                {!stats.inRange && (
                  <>
                    <span className="text-clay-300">&middot;</span>
                    <span className="font-medium">
                      {stats.words < 50 ? "Too short" : "Too long"}
                    </span>
                  </>
                )}
              </div>
            )}

            {/* Quick metadata chips */}
            <div className="flex flex-wrap gap-2">
              {angle && (
                <span className="text-[11px] px-2 py-1 rounded-full bg-kiln-teal/10 text-kiln-teal border border-kiln-teal/20">
                  {angle}
                </span>
              )}
              {confidence !== undefined && (
                <span
                  className={cn(
                    "text-[11px] px-2 py-1 rounded-full border",
                    confidence >= 0.8
                      ? "bg-emerald-500/10 text-emerald-400 border-emerald-500/20"
                      : confidence >= 0.5
                        ? "bg-amber-500/10 text-amber-400 border-amber-500/20"
                        : "bg-red-500/10 text-red-400 border-red-500/20"
                  )}
                >
                  {(confidence * 100).toFixed(0)}% confidence
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

            {/* Push to Clay (Rec #9) + Inline feedback */}
            <div className="flex items-center gap-2">
              {currentRunId && meta && (
                <FeedbackButtons
                  jobId={currentRunId}
                  skill={meta.skill ?? "email-gen"}
                  model={meta.model}
                />
              )}
              <div className="ml-auto">
                <PushToDestination data={result as Record<string, unknown>} />
              </div>
            </div>

            {/* Collapsible metadata */}
            {(angleReasoning || frameworkNotes || meta) && (
              <button
                onClick={() => setMetaOpen(!metaOpen)}
                className="flex items-center gap-1.5 text-xs text-clay-300 hover:text-clay-200 transition-colors"
              >
                <ChevronDown
                  className={cn(
                    "h-3.5 w-3.5 transition-transform",
                    metaOpen && "rotate-180"
                  )}
                />
                Details
              </button>
            )}

            {metaOpen && (
              <div className="rounded-lg border border-clay-700 bg-clay-800/30 p-3 space-y-2 text-xs">
                {angleReasoning && (
                  <div>
                    <p className="text-clay-300 font-medium mb-0.5">
                      Angle Reasoning
                    </p>
                    <p className="text-clay-200">{angleReasoning}</p>
                  </div>
                )}
                {frameworkNotes && (
                  <div>
                    <p className="text-clay-300 font-medium mb-0.5">
                      Framework Notes
                    </p>
                    <p className="text-clay-200">{frameworkNotes}</p>
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
      </div>

      {/* History section */}
      {history.length > 0 && (
        <div className="border-t border-clay-700 p-3">
          <div className="flex items-center justify-between mb-2">
            <h3 className="text-[11px] font-semibold text-clay-300 uppercase tracking-[0.1em]">
              History
            </h3>
            <div className="flex items-center gap-1">
              {/* Compare button */}
              {history.length >= 2 && (
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={onCompareOpen}
                  className="h-6 text-[10px] text-clay-300 hover:text-kiln-teal px-1.5"
                  title="Compare runs"
                >
                  <GitCompareArrows className="h-3 w-3" />
                </Button>
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={onClearHistory}
                className="h-6 text-[10px] text-clay-300 hover:text-red-400 px-1.5"
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            </div>
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
                    {(run.data.company_name as string) || run.skill}
                  </span>
                  <span className="text-[10px] text-clay-300 shrink-0 ml-2">
                    {formatDuration(run.durationMs)}
                  </span>
                </div>
                <div className="flex items-center gap-2 text-[10px] text-clay-300">
                  <span>{run.skill}</span>
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
