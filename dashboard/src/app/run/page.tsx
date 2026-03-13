"use client";

import { Suspense, useState, useEffect, useCallback, useRef } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Header } from "@/components/layout/header";
import { SkillSelector } from "@/components/playground/skill-selector";
import { FormEditor } from "@/components/playground/form-editor";
import { ModelSelector } from "@/components/playground/model-selector";
import { ResultViewer } from "@/components/playground/result-viewer";
import { PromptDrawer } from "@/components/playground/prompt-drawer";
import { RunHistory, loadHistory, saveToHistory, clearHistory, type HistoryEntry } from "@/components/playground/run-history";
import { CsvUploader } from "@/components/batch/csv-uploader";
import { CsvPreview } from "@/components/batch/csv-preview";
import { ColumnMapper, autoMap } from "@/components/batch/column-mapper";
import { BatchProgress } from "@/components/batch/batch-progress";
import { SpreadsheetView } from "@/components/batch/spreadsheet/spreadsheet-view";
import { PushDialog } from "@/components/batch/push-dialog";
import { SKILL_SAMPLES, type Model } from "@/lib/constants";
import {
  runWebhook,
  fetchDestinations,
  pushToDestination,
  runBatch,
  fetchJob,
  fetchScheduledBatches,
  fetchBatchStatus,
} from "@/lib/api";
import type { BatchStatus, Destination, Job, ScheduledBatch, WebhookResponse } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import { Play, Rocket, RotateCcw, Clock, CheckCircle, ChevronDown, ChevronUp, Send, ExternalLink } from "lucide-react";
import { toast } from "sonner";

type BatchPhase = "upload" | "configure" | "processing" | "done" | "scheduled";

function RunInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const activeTab = searchParams.get("tab") === "batch" ? "batch" : "single";

  const setActiveTab = (tab: string) => {
    const params = new URLSearchParams(searchParams.toString());
    if (tab === "batch") {
      params.set("tab", "batch");
      params.delete("skill");
    } else {
      params.delete("tab");
    }
    router.replace(`/run?${params.toString()}`);
  };

  // ─── Single mode state ───
  const [skill, setSkill] = useState("");
  const [json, setJson] = useState("{}");
  const [model, setModel] = useState<Model>("sonnet");
  const [result, setResult] = useState<WebhookResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);

  // ─── Batch mode state ───
  const [batchPhase, setBatchPhase] = useState<BatchPhase>("upload");
  const [headers, setHeaders] = useState<string[]>([]);
  const [rows, setRows] = useState<Record<string, string>[]>([]);
  const [batchSkill, setBatchSkill] = useState("");
  const [batchModel, setBatchModel] = useState<Model>("sonnet");
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [jobIds, setJobIds] = useState<string[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const [scheduledAt, setScheduledAt] = useState("");
  const [scheduledBatches, setScheduledBatches] = useState<ScheduledBatch[]>([]);
  const [scheduledCollapsed, setScheduledCollapsed] = useState(true);
  const [selectedDestId, setSelectedDestId] = useState("");
  const [autoPushResult, setAutoPushResult] = useState<{ success: number; failed: number } | null>(null);
  const [pushOpen, setPushOpen] = useState(false);
  const [batchId, setBatchId] = useState<string | null>(null);
  const [costSummary, setCostSummary] = useState<Pick<BatchStatus, "tokens" | "cost"> | null>(null);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Load destinations and history on mount
  useEffect(() => {
    fetchDestinations()
      .then((res) => setDestinations(res.destinations))
      .catch(() => {});
    setHistory(loadHistory());
  }, []);

  // Handle skill from URL param (single mode)
  useEffect(() => {
    const s = searchParams.get("skill");
    if (s && SKILL_SAMPLES[s]) {
      setSkill(s);
      setJson(JSON.stringify(SKILL_SAMPLES[s], null, 2));
    }
  }, [searchParams]);

  // ─── Single mode handlers ───
  const handleSkillChange = (s: string) => {
    setSkill(s);
    if (SKILL_SAMPLES[s]) {
      setJson(JSON.stringify(SKILL_SAMPLES[s], null, 2));
    }
    setResult(null);
  };

  const handleRun = async () => {
    if (!skill) return;
    let data: Record<string, unknown>;
    try {
      data = JSON.parse(json);
    } catch {
      toast.error("Invalid JSON", {
        description: "Fix your JSON data before running.",
      });
      return;
    }

    setLoading(true);
    setResult(null);
    try {
      const res = await runWebhook({ skill, data, model });
      setResult(res);
      if (res.error) {
        toast.error("Webhook returned an error", {
          description: res.error_message || "Unknown error",
        });
      } else {
        const duration = res._meta?.duration_ms;
        toast.success("Webhook executed successfully", {
          description: duration ? `Completed in ${(duration / 1000).toFixed(1)}s` : undefined,
        });
        // Save to history on success
        const updated = saveToHistory({ skill, model, input: json, result: res });
        setHistory(updated);
      }
    } catch (e) {
      const msg = (e as Error).message;
      setResult({ error: true, error_message: msg });
      toast.error("Failed to execute webhook", {
        description: msg,
        action: {
          label: "Retry",
          onClick: () => handleRun(),
        },
      });
    } finally {
      setLoading(false);
    }
  };

  const handleRestoreHistory = (entry: HistoryEntry) => {
    setSkill(entry.skill);
    setModel(entry.model as Model);
    setJson(entry.input);
    setResult(entry.result);
  };

  const handleClearHistory = () => {
    clearHistory();
    setHistory([]);
  };

  // Keyboard shortcut: Cmd+Enter to run (single mode)
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        if (activeTab === "single" && skill && !loading) handleRun();
      }
    };
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [activeTab, skill, loading, json, model]);

  // ─── Batch mode handlers ───
  const handleParsed = useCallback(
    (h: string[], r: Record<string, string>[]) => {
      setHeaders(h);
      setRows(r);
      setBatchPhase("configure");
      toast.success("CSV uploaded", {
        description: `${r.length} rows with ${h.length} columns detected.`,
      });
    },
    []
  );

  const handleBatchSkillChange = (s: string) => {
    setBatchSkill(s);
    setMapping(autoMap(s, headers));
  };

  const buildMappedRows = (): Record<string, string>[] => {
    return rows.map((row, i) => {
      const mapped: Record<string, string> = { row_id: String(i) };
      for (const [field, csvCol] of Object.entries(mapping)) {
        if (csvCol && row[csvCol] !== undefined) {
          mapped[field] = row[csvCol];
        }
      }
      return mapped;
    });
  };

  const handleProcess = async () => {
    if (!batchSkill) return;
    const mappedRows = buildMappedRows();

    if (scheduledAt) {
      const scheduled = new Date(scheduledAt);
      if (scheduled <= new Date()) {
        toast.error("Invalid schedule time", {
          description: "Scheduled time must be in the future.",
        });
        return;
      }
      try {
        await runBatch({
          skill: batchSkill,
          rows: mappedRows,
          model: batchModel,
          scheduled_at: scheduled.toISOString(),
        });
        setBatchPhase("scheduled");
        loadScheduledBatches();
        toast.success("Batch scheduled", {
          description: `${mappedRows.length} rows will be processed at ${scheduled.toLocaleString()}.`,
        });
      } catch (e) {
        toast.error("Schedule failed", {
          description: (e as Error).message,
          action: {
            label: "Retry",
            onClick: () => handleProcess(),
          },
        });
      }
      return;
    }

    setBatchPhase("processing");
    setJobs(Array(mappedRows.length).fill(null));
    toast.info(`Processing ${mappedRows.length} rows`, {
      description: `Running ${batchSkill} with ${batchModel}...`,
    });

    try {
      const res = await runBatch({
        skill: batchSkill,
        rows: mappedRows,
        model: batchModel,
      });
      setJobIds(res.job_ids || []);
      setBatchId(res.batch_id);
    } catch (e) {
      setBatchPhase("configure");
      toast.error("Batch failed", {
        description: (e as Error).message,
        action: {
          label: "Retry",
          onClick: () => handleProcess(),
        },
      });
    }
  };

  useEffect(() => {
    if (batchPhase !== "processing" || jobIds.length === 0) return;

    const poll = async () => {
      const updated = await Promise.all(jobIds.map((id) => fetchJob(id)));
      setJobs(updated);

      const allDone = updated.every(
        (j) =>
          j.status === "completed" ||
          j.status === "failed" ||
          j.status === "dead_letter"
      );
      if (allDone) {
        setBatchPhase("done");
        if (pollingRef.current) clearInterval(pollingRef.current);
        if (batchId) {
          fetchBatchStatus(batchId)
            .then((bs) => setCostSummary({ tokens: bs.tokens, cost: bs.cost }))
            .catch(() => {});
        }
        const completedJobs = updated.filter((j) => j.status === "completed");
        const failedCount = updated.filter(
          (j) => j.status === "failed" || j.status === "dead_letter"
        ).length;
        if (failedCount === 0) {
          toast.success("Batch complete", {
            description: `All ${completedJobs.length} rows processed successfully.`,
          });
        } else {
          toast.warning(`Batch complete with errors`, {
            description: `${completedJobs.length} succeeded, ${failedCount} failed.`,
          });
        }

        if (selectedDestId && completedJobs.length > 0) {
          pushToDestination(selectedDestId, completedJobs.map((j) => j.id))
            .then((pushResult) => {
              setAutoPushResult({ success: pushResult.success, failed: pushResult.failed });
              if (pushResult.failed === 0) {
                toast.success("Auto-push complete", {
                  description: `${pushResult.success} rows sent to ${pushResult.destination_name}`,
                });
              } else {
                toast.warning("Auto-push completed with errors", {
                  description: `${pushResult.success} succeeded, ${pushResult.failed} failed`,
                });
              }
            })
            .catch((e) => {
              setAutoPushResult(null);
              toast.error("Auto-push failed", {
                description: (e as Error).message,
              });
            });
        }
      }
    };

    poll();
    pollingRef.current = setInterval(poll, 2000);
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [batchPhase, jobIds, selectedDestId]);

  const loadScheduledBatches = () => {
    fetchScheduledBatches()
      .then((res) => setScheduledBatches(res.batches))
      .catch(() => {});
  };

  useEffect(() => {
    loadScheduledBatches();
  }, []);

  const completed = jobs.filter((j) => j?.status === "completed").length;
  const failed = jobs.filter(
    (j) => j?.status === "failed" || j?.status === "dead_letter"
  ).length;

  const handleRetryFailed = async () => {
    const failedJobs = jobs.filter(
      (j) => j?.status === "failed" || j?.status === "dead_letter"
    );
    if (failedJobs.length === 0) return;

    const failedRows = failedJobs.map((j) => {
      const idx = parseInt(j.row_id || "0", 10);
      const original = rows[idx] || {};
      const mapped: Record<string, string> = { row_id: j.row_id || String(idx) };
      for (const [field, csvCol] of Object.entries(mapping)) {
        if (csvCol && original[csvCol] !== undefined) {
          mapped[field] = original[csvCol];
        }
      }
      return mapped;
    });

    toast.info(`Retrying ${failedRows.length} failed rows`, {
      description: `Running ${batchSkill} with ${batchModel}...`,
    });

    try {
      const res = await runBatch({ skill: batchSkill, rows: failedRows, model: batchModel });
      const newJobIds = res.job_ids || [];

      const updatedJobIds = [...jobIds];
      const updatedJobs = [...jobs];
      let retryIdx = 0;
      for (let i = 0; i < updatedJobs.length; i++) {
        const j = updatedJobs[i];
        if (
          j &&
          (j.status === "failed" || j.status === "dead_letter") &&
          retryIdx < newJobIds.length
        ) {
          updatedJobIds[i] = newJobIds[retryIdx];
          updatedJobs[i] = { ...j, status: "queued", error: null, result: null, duration_ms: 0 } as Job;
          retryIdx++;
        }
      }

      setJobIds(updatedJobIds);
      setJobs(updatedJobs);
      setBatchPhase("processing");
    } catch (e) {
      toast.error("Retry failed", {
        description: (e as Error).message,
        action: {
          label: "Retry again",
          onClick: () => handleRetryFailed(),
        },
      });
    }
  };

  const handleBatchReset = () => {
    setBatchPhase("upload");
    setHeaders([]);
    setRows([]);
    setBatchSkill("");
    setMapping({});
    setJobIds([]);
    setJobs([]);
    setScheduledAt("");
    setBatchId(null);
    setCostSummary(null);
    setSelectedDestId("");
    setAutoPushResult(null);
  };

  return (
    <div className="flex-1 overflow-auto p-4 md:p-6 space-y-6 pb-20 md:pb-6">
      <div className="flex items-center gap-3">
        <Tabs value={activeTab} onValueChange={setActiveTab}>
          <TabsList className="bg-clay-800 border border-clay-500">
            <TabsTrigger
              value="single"
              className="data-[state=active]:bg-kiln-teal/10 data-[state=active]:text-kiln-teal text-clay-200"
            >
              Single
            </TabsTrigger>
            <TabsTrigger
              value="batch"
              className="data-[state=active]:bg-kiln-teal/10 data-[state=active]:text-kiln-teal text-clay-200"
            >
              Batch
            </TabsTrigger>
          </TabsList>
        </Tabs>
        {activeTab === "single" && (
          <div className="ml-auto">
            <RunHistory
              history={history}
              onRestore={handleRestoreHistory}
              onClear={handleClearHistory}
            />
          </div>
        )}
      </div>

      {/* ─── Single Mode ─── */}
      {activeTab === "single" && (
        <div className="grid grid-cols-1 md:grid-cols-2 gap-6 h-full">
          <div className="flex flex-col gap-4">
            <SkillSelector value={skill} onChange={handleSkillChange} />
            <FormEditor value={json} onChange={setJson} skill={skill} />
            <ModelSelector value={model} onChange={setModel} />
            <div className="flex items-center gap-2">
              <Button
                onClick={handleRun}
                disabled={!skill || loading}
                className="flex-1 bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold transition-all duration-200"
              >
                <Play className="h-4 w-4 mr-2" />
                {loading
                  ? "Processing..."
                  : skill
                    ? `Run with ${model.charAt(0).toUpperCase() + model.slice(1)}`
                    : "Run"}
                {!loading && (
                  <kbd className="hidden md:inline-block ml-2 text-[10px] opacity-60 border border-kiln-teal-dark rounded px-1 py-0.5">
                    {"\u2318"}Enter
                  </kbd>
                )}
              </Button>
              <PromptDrawer skill={skill} json={json} />
            </div>
          </div>
          <ResultViewer
            result={result}
            loading={loading}
            skill={skill}
            model={model}
            destinations={destinations}
            onLoadSkill={handleSkillChange}
          />
        </div>
      )}

      {/* ─── Sticky Run button on mobile ─── */}
      {activeTab === "single" && (
        <div className="fixed bottom-0 left-0 right-0 md:hidden p-3 bg-clay-950/80 backdrop-blur-sm border-t border-clay-500 z-40">
          <Button
            onClick={handleRun}
            disabled={!skill || loading}
            className="w-full bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
          >
            <Play className="h-4 w-4 mr-2" />
            {loading ? "Processing..." : "Run"}
          </Button>
        </div>
      )}

      {/* ─── Batch Mode ─── */}
      {activeTab === "batch" && (
        <div className="space-y-6">
          {batchPhase === "upload" && <CsvUploader onParsed={handleParsed} />}

          {(batchPhase === "configure" || batchPhase === "processing" || batchPhase === "done") && (
            <>
              <CsvPreview headers={headers} rows={rows} />

              {batchPhase === "configure" && (
                <>
                  <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                    <SkillSelector value={batchSkill} onChange={handleBatchSkillChange} />
                    <ModelSelector value={batchModel} onChange={setBatchModel} />
                    <div>
                      <label className="block text-xs text-clay-200 uppercase tracking-wider mb-1.5">
                        Destination (optional)
                      </label>
                      <Select value={selectedDestId} onValueChange={(v) => setSelectedDestId(v === "none" ? "" : v)}>
                        <SelectTrigger className="w-full border-clay-700 bg-clay-800 text-clay-200">
                          <SelectValue placeholder="None — manual push" />
                        </SelectTrigger>
                        <SelectContent className="border-clay-700 bg-clay-800">
                          <SelectItem value="none">None — manual push</SelectItem>
                          {destinations.map((d) => (
                            <SelectItem key={d.id} value={d.id}>
                              {d.name} ({d.type === "clay_webhook" ? "Clay" : "Webhook"})
                            </SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                    </div>
                  </div>

                  {batchSkill && (
                    <ColumnMapper
                      skill={batchSkill}
                      csvHeaders={headers}
                      mapping={mapping}
                      onMappingChange={setMapping}
                    />
                  )}

                  <div className="flex flex-col sm:flex-row items-stretch sm:items-end gap-4">
                    <div className="flex-1">
                      <label className="block text-xs text-clay-200 uppercase tracking-wider mb-1.5">
                        Schedule (optional)
                      </label>
                      <input
                        type="datetime-local"
                        value={scheduledAt}
                        onChange={(e) => setScheduledAt(e.target.value)}
                        className="w-full rounded-lg border border-clay-500 bg-clay-800 text-clay-200 px-3 py-2 text-sm focus:border-kiln-teal focus:outline-none"
                      />
                    </div>
                    <Button
                      onClick={handleProcess}
                      disabled={!batchSkill}
                      className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold transition-all duration-200"
                    >
                      {scheduledAt ? (
                        <>
                          <Clock className="h-4 w-4 mr-2" />
                          Schedule {rows.length} rows
                        </>
                      ) : (
                        <>
                          <Rocket className="h-4 w-4 mr-2" />
                          Process {rows.length} rows
                        </>
                      )}
                    </Button>
                  </div>
                </>
              )}

              {(batchPhase === "processing" || batchPhase === "done") && (
                <>
                  <BatchProgress
                    total={jobIds.length}
                    completed={completed}
                    failed={failed}
                    done={batchPhase === "done"}
                    costSummary={costSummary}
                  />
                  {selectedDestId && (() => {
                    const destName = destinations.find((d) => d.id === selectedDestId)?.name || "destination";
                    if (batchPhase === "processing") {
                      return (
                        <Badge variant="outline" className="border-kiln-teal/30 bg-kiln-teal/5 text-kiln-teal w-fit">
                          <Send className="h-3 w-3 mr-1.5" />
                          Results will auto-push to {destName}
                        </Badge>
                      );
                    }
                    if (batchPhase === "done" && autoPushResult) {
                      return (
                        <Badge
                          variant="outline"
                          className={`w-fit ${
                            autoPushResult.failed === 0
                              ? "border-kiln-teal/30 bg-kiln-teal/5 text-kiln-teal"
                              : "border-kiln-mustard/30 bg-kiln-mustard/5 text-kiln-mustard"
                          }`}
                        >
                          <Send className="h-3 w-3 mr-1.5" />
                          Pushed {autoPushResult.success} rows to {destName}
                          {autoPushResult.failed > 0 && ` (${autoPushResult.failed} failed)`}
                        </Badge>
                      );
                    }
                    if (batchPhase === "done" && !autoPushResult) {
                      return (
                        <Badge variant="outline" className="border-clay-700 bg-clay-800/50 text-clay-200 w-fit">
                          <Send className="h-3 w-3 mr-1.5" />
                          Auto-pushing to {destName}...
                        </Badge>
                      );
                    }
                    return null;
                  })()}
                  {jobs.some((j) => j !== null) && (
                    <SpreadsheetView
                      jobs={jobs.filter((j): j is Job => j !== null)}
                      originalRows={rows}
                      csvHeaders={headers}
                      onRetrySelected={
                        batchPhase === "done"
                          ? (jobIds) => {
                              // Retry the selected failed jobs
                              handleRetryFailed();
                            }
                          : undefined
                      }
                      onPushSelected={
                        batchPhase === "done" && completed > 0
                          ? () => setPushOpen(true)
                          : undefined
                      }
                    />
                  )}
                  {batchPhase === "done" && (
                    <div className="flex items-center gap-2">
                      {batchId && (
                        <Button
                          variant="outline"
                          onClick={() => router.push(`/batch-results?id=${batchId}`)}
                          className="border-kiln-teal/30 bg-kiln-teal/10 text-kiln-teal hover:bg-kiln-teal/20"
                        >
                          <ExternalLink className="h-4 w-4 mr-2" />
                          View Results
                        </Button>
                      )}
                      <Button
                        variant="outline"
                        onClick={handleBatchReset}
                        className="border-clay-700 bg-clay-800 text-clay-300 hover:bg-clay-800 hover:text-clay-100"
                      >
                        <RotateCcw className="h-4 w-4 mr-2" />
                        Start New Batch
                      </Button>
                    </div>
                  )}
                </>
              )}
            </>
          )}

          {batchPhase === "scheduled" && (
            <div className="rounded-xl border border-kiln-teal/30 bg-kiln-teal/5 p-6 text-center space-y-4">
              <CheckCircle className="h-12 w-12 text-kiln-teal mx-auto" />
              <h3 className="text-lg font-semibold text-clay-100">Batch Scheduled</h3>
              <p className="text-clay-200 text-sm">
                Your batch of {rows.length} rows will be processed at the scheduled time.
              </p>
              <Button
                variant="outline"
                onClick={handleBatchReset}
                className="border-clay-700 bg-clay-800 text-clay-300 hover:bg-clay-800 hover:text-clay-100"
              >
                <RotateCcw className="h-4 w-4 mr-2" />
                Start New Batch
              </Button>
            </div>
          )}

          <PushDialog
            open={pushOpen}
            onOpenChange={setPushOpen}
            destinations={destinations}
            jobs={jobs.filter((j): j is Job => j !== null)}
          />

          {scheduledBatches.length > 0 && (
            <div className="rounded-xl border border-clay-500  overflow-hidden">
              <button
                onClick={() => setScheduledCollapsed((c) => !c)}
                className="w-full flex items-center justify-between p-4 text-left hover:bg-clay-800/50 transition-colors"
              >
                <h3 className="text-sm font-semibold text-clay-300 uppercase tracking-wider">
                  Scheduled Batches
                  <span className="ml-2 inline-flex items-center justify-center h-5 min-w-5 rounded-full bg-kiln-mustard/15 text-kiln-mustard text-xs px-1.5">
                    {scheduledBatches.length}
                  </span>
                </h3>
                {scheduledCollapsed ? (
                  <ChevronDown className="h-4 w-4 text-clay-200" />
                ) : (
                  <ChevronUp className="h-4 w-4 text-clay-200" />
                )}
              </button>
              {!scheduledCollapsed && (
                <div className="px-4 pb-4 space-y-3">
                  {scheduledBatches.map((b) => (
                    <div
                      key={b.id}
                      className="flex items-center justify-between text-sm border-b border-clay-500 pb-2 last:border-0"
                    >
                      <div>
                        <span className="text-kiln-teal font-medium">{b.skill}</span>
                        <span className="text-clay-200 ml-2">({b.total_rows} rows)</span>
                      </div>
                      <div className="flex items-center gap-3">
                        <span className="text-clay-200 text-xs">
                          {new Date(b.scheduled_at * 1000).toLocaleString()}
                        </span>
                        <span
                          className={`text-xs font-medium px-2 py-0.5 rounded ${
                            b.status === "scheduled"
                              ? "bg-kiln-mustard/15 text-kiln-mustard"
                              : b.status === "enqueued"
                                ? "bg-kiln-teal/15 text-kiln-teal"
                                : "bg-clay-700 text-clay-200"
                          }`}
                        >
                          {b.status}
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </div>
  );
}

export default function RunPage() {
  return (
    <div className="flex flex-col h-full">
      <Header title="Run" />
      <Suspense>
        <RunInner />
      </Suspense>
    </div>
  );
}
