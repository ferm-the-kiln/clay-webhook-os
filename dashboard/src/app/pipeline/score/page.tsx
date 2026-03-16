"use client";

import { useState, useCallback } from "react";
import { Header } from "@/components/layout/header";
import { DatasetSelector } from "@/components/pipeline/dataset-selector";
import { StageProgressBar } from "@/components/pipeline/stage-progress-bar";
import { DatasetSpreadsheetView } from "@/components/pipeline/dataset-spreadsheet/dataset-spreadsheet-view";
import { useDatasetContext } from "@/contexts/dataset-context";
import { useStagePolling } from "@/hooks/use-dataset";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { runDatasetStage } from "@/lib/api";
import { toast } from "sonner";
import { Target, Play, Loader2, CheckCircle2 } from "lucide-react";

const SENIORITY_TIERS = ["IC", "Manager", "Director", "VP", "C-Suite", "Unknown"];
const INDUSTRY_VERTICALS = [
  "SaaS", "Fintech", "Healthcare", "E-commerce", "Cybersecurity",
  "AI/ML", "EdTech", "MarTech", "DevTools", "HR Tech",
  "Data & Analytics", "Cloud Infrastructure", "Media & Entertainment",
  "Supply Chain", "Other",
];
const DEPARTMENTS = [
  "Engineering", "Sales", "Marketing", "Product", "Operations",
  "Finance", "HR", "Legal", "Customer Success", "Other",
];

export default function ScorePage() {
  const { datasets, activeId, setActiveId, dataset, rows, reload, reloadDatasets } = useDatasetContext();
  const [batchId, setBatchId] = useState<string | null>(null);
  const [running, setRunning] = useState(false);

  const stageStatus = useStagePolling(activeId, batchId, () => {
    reload();
    setRunning(false);
  });

  const handleRun = useCallback(async () => {
    if (!activeId) return;
    setRunning(true);
    try {
      const res = await runDatasetStage(activeId, { stage: "classify" });
      setBatchId(res.batch_id);
      toast.success(`Classifying ${res.total_rows} rows...`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to start");
      setRunning(false);
    }
  }, [activeId]);

  const isCompleted = dataset?.stages_completed.includes("classify");
  const columns = dataset?.columns.filter((c) => c.name !== "_row_id") ?? [];

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Score"
        breadcrumbs={[
          { label: "Pipeline", href: "/pipeline" },
          { label: "Score" },
        ]}
      />

      <div className="flex flex-col gap-6 p-6 max-w-[1400px]">
        <DatasetSelector
          datasets={datasets}
          activeId={activeId}
          onSelect={setActiveId}
          onCreated={reloadDatasets}
        />

        {dataset && (
          <>
            <StageProgressBar
              completedStages={dataset.stages_completed}
              currentStage={running ? "classify" : undefined}
            />

            {/* Classify schema reference */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              <div className="border border-clay-600 rounded-lg p-4 bg-clay-800/50">
                <p className="text-xs text-clay-200 uppercase tracking-wider mb-2">Seniority</p>
                <div className="flex flex-wrap gap-1">
                  {SENIORITY_TIERS.map((tier) => (
                    <Badge key={tier} variant="outline" className="text-[10px] border-clay-600 text-clay-300">
                      {tier}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="border border-clay-600 rounded-lg p-4 bg-clay-800/50">
                <p className="text-xs text-clay-200 uppercase tracking-wider mb-2">Industry</p>
                <div className="flex flex-wrap gap-1">
                  {INDUSTRY_VERTICALS.map((v) => (
                    <Badge key={v} variant="outline" className="text-[10px] border-clay-600 text-clay-300">
                      {v}
                    </Badge>
                  ))}
                </div>
              </div>
              <div className="border border-clay-600 rounded-lg p-4 bg-clay-800/50">
                <p className="text-xs text-clay-200 uppercase tracking-wider mb-2">Department</p>
                <div className="flex flex-wrap gap-1">
                  {DEPARTMENTS.map((d) => (
                    <Badge key={d} variant="outline" className="text-[10px] border-clay-600 text-clay-300">
                      {d}
                    </Badge>
                  ))}
                </div>
              </div>
            </div>

            {/* Run button */}
            <div className="border border-clay-600 rounded-lg p-4 bg-clay-800/50 flex items-center justify-between">
              <div>
                <span className="text-sm font-medium text-clay-100">Classify Skill</span>
                <p className="text-xs text-clay-300 mt-0.5">
                  Normalizes seniority, industry, and department for each row
                </p>
                {isCompleted && (
                  <Badge variant="outline" className="mt-1 border-kiln-teal/30 text-kiln-teal text-xs">
                    <CheckCircle2 className="h-3 w-3 mr-1" />
                    Completed
                  </Badge>
                )}
              </div>
              <Button
                onClick={handleRun}
                disabled={running || !rows.length}
                className="bg-kiln-teal text-clay-900 hover:bg-kiln-teal/90"
              >
                {running ? (
                  <>
                    <Loader2 className="h-4 w-4 mr-1.5 animate-spin" />
                    Running...
                  </>
                ) : (
                  <>
                    <Play className="h-4 w-4 mr-1.5" />
                    Run Classify
                  </>
                )}
              </Button>
            </div>

            {/* Progress */}
            {stageStatus && stageStatus.status === "running" && (
              <div className="border border-clay-600 rounded-lg p-4 bg-clay-800/50">
                <div className="flex items-center justify-between text-sm mb-2">
                  <span className="text-clay-200">
                    Processing: {stageStatus.completed + stageStatus.failed}/{stageStatus.total}
                  </span>
                </div>
                <div className="w-full bg-clay-700 rounded-full h-2">
                  <div
                    className="bg-kiln-teal h-2 rounded-full transition-all duration-300"
                    style={{
                      width: `${((stageStatus.completed + stageStatus.failed) / stageStatus.total) * 100}%`,
                    }}
                  />
                </div>
              </div>
            )}

            {stageStatus?.status === "completed" && (
              <div className="flex items-center gap-2 text-sm text-kiln-teal">
                <CheckCircle2 className="h-4 w-4" />
                Done — {stageStatus.completed} classified, {stageStatus.failed} failed
              </div>
            )}

            {/* Results */}
            {rows.length > 0 && (
              <DatasetSpreadsheetView columns={columns} rows={rows} />
            )}
          </>
        )}

        {!dataset && (
          <div className="flex flex-col items-center justify-center py-20 text-clay-300">
            <Target className="h-12 w-12 mb-4 text-clay-500" />
            <p className="text-lg font-medium mb-1">Select a dataset first</p>
            <p className="text-sm">Choose a dataset to classify and score leads.</p>
          </div>
        )}
      </div>
    </div>
  );
}
