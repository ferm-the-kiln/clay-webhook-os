"use client";

import { useState, useEffect } from "react";
import { useBatch } from "@/hooks/use-batch";
import { fetchSkills, fetchJob } from "@/lib/api";
import { CsvUploader } from "@/components/batch/csv-uploader";
import { CsvPreview } from "@/components/batch/csv-preview";
import { ColumnMapper, autoMap } from "@/components/batch/column-mapper";
import { BatchProgress } from "@/components/batch/batch-progress";
import { SpreadsheetView } from "@/components/batch/spreadsheet/spreadsheet-view";
import { RowDetailPanel } from "@/components/batch/spreadsheet/row-detail-panel";
import { RetryDialog } from "@/components/batch/retry-dialog";
import { ScheduledTab } from "@/components/batch/scheduled-tab";
import { Button } from "@/components/ui/button";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Badge } from "@/components/ui/badge";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import {
  AlertTriangle,
  ArrowRight,
  Calendar,
  Layers,
  Pause,
  Play,
  RefreshCw,
  RotateCcw,
  Upload,
} from "lucide-react";
import type { Job } from "@/lib/types";

export default function BatchPage() {
  const batch = useBatch();
  const [skills, setSkills] = useState<string[]>([]);
  const [retryOpen, setRetryOpen] = useState(false);
  const [expandedJob, setExpandedJob] = useState<Job | null>(null);

  useEffect(() => {
    fetchSkills()
      .then((resp) => setSkills(resp.skills))
      .catch(() => {});
  }, []);

  // Auto-map columns when skill changes
  useEffect(() => {
    if (batch.selectedSkill && batch.csvHeaders.length > 0) {
      const mapping = autoMap(batch.selectedSkill, batch.csvHeaders);
      batch.setColumnMapping(mapping);
    }
  }, [batch.selectedSkill, batch.csvHeaders]);

  // Convert batch status jobs to full Job objects for SpreadsheetView
  const jobsForSpreadsheet: Job[] = (batch.batchStatus?.jobs ?? []).map((j) => ({
    id: j.id,
    skill: batch.selectedSkill,
    row_id: j.row_id,
    status: j.status,
    duration_ms: j.duration_ms,
    error: j.error,
    result: j.result,
    created_at: 0,
    completed_at: null,
    input_tokens_est: j.input_tokens_est,
    output_tokens_est: j.output_tokens_est,
    cost_est_usd: j.cost_est_usd,
  }));

  const handleRowClick = async (job: Job) => {
    // Fetch full job details for the detail panel
    try {
      const fullJob = await fetchJob(job.id);
      setExpandedJob(fullJob);
    } catch {
      setExpandedJob(job);
    }
  };

  const handleRetryRow = async (jobId: string) => {
    if (batch.batchId) {
      await batch.retryFailed({ [jobId]: {} });
    }
  };

  return (
    <div className="min-h-screen">
      <div className="max-w-7xl mx-auto px-6 py-8">
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center gap-3">
            <Layers className="h-6 w-6 text-kiln-teal" />
            <h1 className="text-2xl font-bold text-clay-100 font-[family-name:var(--font-sans)]">
              Batch Processing
            </h1>
            <Badge variant="outline" className="text-[10px] text-clay-200 border-clay-500">
              {batch.phase}
            </Badge>
          </div>
          {batch.phase !== "upload" && (
            <Button
              variant="ghost"
              onClick={batch.reset}
              className="text-clay-200 hover:text-clay-300"
            >
              <Upload className="h-4 w-4 mr-2" />
              New Batch
            </Button>
          )}
        </div>

        <Tabs defaultValue="batch" className="space-y-4">
          <TabsList className="bg-clay-700 border border-clay-500">
            <TabsTrigger value="batch" className="data-[state=active]:bg-clay-800 data-[state=active]:text-kiln-teal text-clay-200">
              <Layers className="h-3.5 w-3.5 mr-1.5" />
              Batch
            </TabsTrigger>
            <TabsTrigger value="scheduled" className="data-[state=active]:bg-clay-800 data-[state=active]:text-kiln-teal text-clay-200">
              <Calendar className="h-3.5 w-3.5 mr-1.5" />
              Scheduled
            </TabsTrigger>
          </TabsList>

          <TabsContent value="batch" className="space-y-4">
            {/* Upload Phase */}
            {batch.phase === "upload" && (
              <div className="space-y-4">
                <CsvUploader onParsed={batch.setCsvData} />
              </div>
            )}

            {/* Preview Phase */}
            {batch.phase === "preview" && (
              <div className="space-y-4">
                {/* Validation warnings */}
                {batch.validationWarnings.length > 0 && (
                  <Card className="border-kiln-mustard/30 bg-kiln-mustard/5">
                    <CardContent className="p-3">
                      <div className="flex items-start gap-2">
                        <AlertTriangle className="h-4 w-4 text-kiln-mustard shrink-0 mt-0.5" />
                        <div className="space-y-1">
                          {batch.validationWarnings.map((w, i) => (
                            <p key={i} className="text-xs text-kiln-mustard">{w}</p>
                          ))}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                )}

                <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
                  {/* Config panel */}
                  <div className="space-y-4">
                    <Card className="border-clay-500">
                      <CardContent className="p-4 space-y-3">
                        <div>
                          <label className="text-xs text-clay-200 uppercase tracking-wider font-[family-name:var(--font-sans)]">
                            Skill
                          </label>
                          <Select value={batch.selectedSkill} onValueChange={batch.setSelectedSkill}>
                            <SelectTrigger className="mt-1 border-clay-700 bg-clay-700 text-clay-100 focus:ring-kiln-teal">
                              <SelectValue placeholder="Select a skill..." />
                            </SelectTrigger>
                            <SelectContent className="border-clay-700 bg-clay-800">
                              {skills.map((s) => (
                                <SelectItem
                                  key={s}
                                  value={s}
                                  className="text-clay-200 focus:bg-kiln-teal/10 focus:text-kiln-teal"
                                >
                                  {s}
                                </SelectItem>
                              ))}
                            </SelectContent>
                          </Select>
                        </div>

                        <div>
                          <label className="text-xs text-clay-200 uppercase tracking-wider font-[family-name:var(--font-sans)]">
                            Model (optional)
                          </label>
                          <Select value={batch.model || "__auto__"} onValueChange={(v) => batch.setModel(v === "__auto__" ? null : v)}>
                            <SelectTrigger className="mt-1 border-clay-700 bg-clay-700 text-clay-100 focus:ring-kiln-teal">
                              <SelectValue />
                            </SelectTrigger>
                            <SelectContent className="border-clay-700 bg-clay-800">
                              <SelectItem value="__auto__" className="text-clay-200">Auto (from skill)</SelectItem>
                              <SelectItem value="opus" className="text-clay-200">Opus</SelectItem>
                              <SelectItem value="sonnet" className="text-clay-200">Sonnet</SelectItem>
                              <SelectItem value="haiku" className="text-clay-200">Haiku</SelectItem>
                            </SelectContent>
                          </Select>
                        </div>

                        <div>
                          <label className="text-xs text-clay-200 uppercase tracking-wider font-[family-name:var(--font-sans)]">
                            Instructions (optional)
                          </label>
                          <Textarea
                            placeholder="Additional instructions for this batch..."
                            value={batch.instructions}
                            onChange={(e) => batch.setInstructions(e.target.value)}
                            className="mt-1 text-sm bg-clay-700 border-clay-700 text-clay-100 min-h-[80px]"
                          />
                        </div>
                      </CardContent>
                    </Card>

                    {batch.selectedSkill && (
                      <ColumnMapper
                        skill={batch.selectedSkill}
                        csvHeaders={batch.csvHeaders}
                        mapping={batch.columnMapping}
                        onMappingChange={batch.setColumnMapping}
                      />
                    )}
                  </div>

                  {/* CSV Preview */}
                  <div className="lg:col-span-2">
                    <CsvPreview headers={batch.csvHeaders} rows={batch.csvRows} />
                  </div>
                </div>

                {/* Run button */}
                <div className="flex justify-end">
                  <Button
                    onClick={batch.startBatch}
                    disabled={!batch.selectedSkill}
                    className="bg-kiln-teal hover:bg-kiln-teal/90 text-white px-6"
                  >
                    Run Batch ({batch.csvRows.length} rows)
                    <ArrowRight className="h-4 w-4 ml-2" />
                  </Button>
                </div>
              </div>
            )}

            {/* Running / Done Phase */}
            {(batch.phase === "running" || batch.phase === "done") && batch.batchStatus && (
              <div className="space-y-4">
                {/* Progress + controls */}
                <div className="flex gap-4 items-start">
                  <div className="flex-1">
                    <BatchProgress
                      total={batch.batchStatus.total_rows}
                      completed={batch.batchStatus.completed}
                      failed={batch.batchStatus.failed}
                      done={batch.batchStatus.done}
                      costSummary={batch.batchStatus}
                    />
                  </div>
                  <div className="flex flex-col gap-2">
                    {batch.phase === "running" && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={batch.togglePause}
                        className={
                          batch.queuePaused
                            ? "bg-kiln-teal/10 text-kiln-teal border-kiln-teal/30"
                            : "bg-kiln-mustard/10 text-kiln-mustard border-kiln-mustard/30"
                        }
                      >
                        {batch.queuePaused ? (
                          <>
                            <Play className="h-3.5 w-3.5 mr-1" />
                            Resume
                          </>
                        ) : (
                          <>
                            <Pause className="h-3.5 w-3.5 mr-1" />
                            Pause
                          </>
                        )}
                      </Button>
                    )}
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={batch.refreshNow}
                      className="text-clay-200 hover:text-clay-300"
                    >
                      <RefreshCw className="h-3.5 w-3.5 mr-1" />
                      Refresh
                    </Button>
                    {batch.batchStatus.failed > 0 && (
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setRetryOpen(true)}
                        className="bg-kiln-coral/10 text-kiln-coral border-kiln-coral/30 hover:bg-kiln-coral/20"
                      >
                        <RotateCcw className="h-3.5 w-3.5 mr-1" />
                        Retry Failed
                      </Button>
                    )}
                  </div>
                </div>

                {/* Status info */}
                {batch.lastUpdated && (
                  <div className="flex items-center gap-2 text-[11px] text-clay-300">
                    {batch.isPolling && (
                      <span className="flex items-center gap-1">
                        <span className="h-1.5 w-1.5 rounded-full bg-kiln-teal animate-pulse" />
                        Polling every 3s
                      </span>
                    )}
                    <span>Last updated: {batch.lastUpdated.toLocaleTimeString()}</span>
                    {batch.queuePaused && (
                      <Badge variant="outline" className="bg-kiln-mustard/10 text-kiln-mustard border-kiln-mustard/30 text-[10px]">
                        Queue paused
                      </Badge>
                    )}
                  </div>
                )}

                {/* Expanded job detail */}
                {expandedJob && (
                  <div className="relative">
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => setExpandedJob(null)}
                      className="absolute top-2 right-2 h-6 text-clay-200 hover:text-clay-300 z-10"
                    >
                      Close
                    </Button>
                    <RowDetailPanel
                      job={expandedJob}
                      originalData={
                        batch.csvRows[
                          jobsForSpreadsheet.findIndex((j) => j.id === expandedJob.id)
                        ] || {}
                      }
                      onRetryRow={handleRetryRow}
                    />
                  </div>
                )}

                {/* Spreadsheet */}
                <SpreadsheetView
                  jobs={jobsForSpreadsheet}
                  originalRows={batch.csvRows}
                  csvHeaders={batch.csvHeaders}
                  onRetrySelected={(ids) => {
                    const patches: Record<string, Record<string, unknown>> = {};
                    for (const id of ids) patches[id] = {};
                    batch.retryFailed(patches);
                  }}
                  onRowClick={handleRowClick}
                />
              </div>
            )}

            {/* Retry dialog */}
            {batch.batchStatus && (
              <RetryDialog
                open={retryOpen}
                onOpenChange={setRetryOpen}
                batchStatus={batch.batchStatus}
                onRetry={batch.retryFailed}
              />
            )}
          </TabsContent>

          <TabsContent value="scheduled">
            <ScheduledTab />
          </TabsContent>
        </Tabs>
      </div>
    </div>
  );
}
