"use client";

import { Building2, Users, Tags } from "lucide-react";
import { ActionCard } from "./action-card";
import { useDatasetContext } from "@/contexts/dataset-context";
import { runDatasetStage } from "@/lib/api";
import { toast } from "sonner";
import type { StageStatus } from "@/lib/types";

interface ResearchActionsProps {
  startPolling: (stage: string, batchId: string, onComplete?: () => void) => void;
  getStageStatus: (stage: string) => StageStatus | null;
  isStageRunning: (stage: string) => boolean;
}

export function ResearchActions({ startPolling, getStageStatus, isStageRunning }: ResearchActionsProps) {
  const { activeId, rows, reload } = useDatasetContext();

  const runStage = async (stage: string, label: string, rowFilter?: (r: Record<string, unknown>) => boolean) => {
    if (!activeId || !rows.length) return;
    try {
      const targetRowIds = rowFilter
        ? rows.filter(rowFilter).map((r) => r._row_id)
        : undefined;
      const res = await runDatasetStage(activeId, {
        stage,
        row_ids: targetRowIds ?? null,
      });
      startPolling(stage, res.batch_id, () => {
        reload();
        toast.success(`${label} complete`);
      });
      toast.success(`Running ${label} on ${res.total_rows} rows...`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : `Failed to start ${label}`);
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <ActionCard
        title="Company Research"
        description="Deep research on each company using AI"
        icon={Building2}
        onRun={() => runStage("company-research", "Company Research")}
        disabled={!activeId || !rows.length}
        running={isStageRunning("company-research")}
        stageStatus={getStageStatus("company-research")}
      />

      <ActionCard
        title="People Research"
        description="Research individual contacts and their roles"
        icon={Users}
        onRun={() => runStage("people-research", "People Research")}
        disabled={!activeId || !rows.length}
        running={isStageRunning("people-research")}
        stageStatus={getStageStatus("people-research")}
      />

      <ActionCard
        title="Classify"
        description="Normalize seniority, industry, and department"
        icon={Tags}
        onRun={() => runStage("classify", "Classify")}
        disabled={!activeId || !rows.length}
        running={isStageRunning("classify")}
        stageStatus={getStageStatus("classify")}
      />
    </div>
  );
}
