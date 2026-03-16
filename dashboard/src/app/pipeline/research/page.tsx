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
import { Search, Building2, Users, Swords, Play, Loader2, CheckCircle2 } from "lucide-react";

const RESEARCH_SKILLS = [
  {
    id: "company-research",
    label: "Company Research",
    description: "Tech stack, funding, news, competitive landscape",
    icon: Building2,
  },
  {
    id: "people-research",
    label: "People Research",
    description: "Role context, career trajectory, social presence",
    icon: Users,
  },
  {
    id: "competitor-research",
    label: "Competitor Research",
    description: "Competitive positioning, win/loss patterns",
    icon: Swords,
  },
];

export default function ResearchPage() {
  const { datasets, activeId, setActiveId, dataset, rows, reload, reloadDatasets } = useDatasetContext();
  const [batchId, setBatchId] = useState<string | null>(null);
  const [running, setRunning] = useState<string | null>(null);

  const stageStatus = useStagePolling(activeId, batchId, () => {
    reload();
    setRunning(null);
  });

  const handleRun = useCallback(async (skillId: string) => {
    if (!activeId) return;
    setRunning(skillId);
    try {
      const res = await runDatasetStage(activeId, { stage: skillId });
      setBatchId(res.batch_id);
      toast.success(`Running ${skillId} on ${res.total_rows} rows...`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to start");
      setRunning(null);
    }
  }, [activeId]);

  const isCompleted = dataset?.stages_completed.includes("research");
  const columns = dataset?.columns.filter((c) => c.name !== "_row_id") ?? [];

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Research"
        breadcrumbs={[
          { label: "Pipeline", href: "/pipeline" },
          { label: "Research" },
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
              currentStage={running ? "research" : undefined}
            />

            {/* Research provider cards */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {RESEARCH_SKILLS.map((skill) => (
                <div
                  key={skill.id}
                  className="border border-clay-600 rounded-lg p-4 bg-clay-800/50"
                >
                  <div className="flex items-center gap-2 mb-2">
                    <skill.icon className="h-4 w-4 text-kiln-teal" />
                    <span className="text-sm font-medium text-clay-100">{skill.label}</span>
                  </div>
                  <p className="text-xs text-clay-300 mb-3">{skill.description}</p>
                  <Button
                    size="sm"
                    onClick={() => handleRun(skill.id)}
                    disabled={running !== null || !rows.length}
                    className="w-full bg-kiln-teal text-clay-900 hover:bg-kiln-teal/90"
                  >
                    {running === skill.id ? (
                      <>
                        <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                        Running...
                      </>
                    ) : (
                      <>
                        <Play className="h-3.5 w-3.5 mr-1.5" />
                        Run Research
                      </>
                    )}
                  </Button>
                </div>
              ))}
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
                Done — {stageStatus.completed} enriched, {stageStatus.failed} failed
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
            <Search className="h-12 w-12 mb-4 text-clay-500" />
            <p className="text-lg font-medium mb-1">Select a dataset first</p>
            <p className="text-sm">Choose a dataset to run research enrichment.</p>
          </div>
        )}
      </div>
    </div>
  );
}
