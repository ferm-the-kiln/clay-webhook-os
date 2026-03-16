"use client";

import { useState } from "react";
import { Mail, ShieldCheck, Calculator } from "lucide-react";
import { ActionCard } from "./action-card";
import { useDatasetContext } from "@/contexts/dataset-context";
import { runDatasetStage } from "@/lib/api";
import { toast } from "sonner";
import type { StageStatus } from "@/lib/types";

interface EnrichActionsProps {
  startPolling: (stage: string, batchId: string, onComplete?: () => void) => void;
  getStageStatus: (stage: string) => StageStatus | null;
  isStageRunning: (stage: string) => boolean;
}

export function EnrichActions({ startPolling, getStageStatus, isStageRunning }: EnrichActionsProps) {
  const { activeId, rows, reload } = useDatasetContext();
  const [onlyMissing, setOnlyMissing] = useState(true);

  const missingEmailCount = rows.filter((r) => !r.email || r.email === "").length;

  const handleFindEmail = async () => {
    if (!activeId || !rows.length) return;
    try {
      const targetRowIds = onlyMissing
        ? rows.filter((r) => !r.email || r.email === "").map((r) => r._row_id)
        : undefined;
      const res = await runDatasetStage(activeId, {
        stage: "find-email",
        row_ids: targetRowIds ?? null,
      });
      startPolling("find-email", res.batch_id, () => {
        reload();
        toast.success("Email lookup complete");
      });
      toast.success(`Finding emails for ${res.total_rows} rows...`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to start email lookup");
    }
  };

  const handleVerifyEmail = async () => {
    if (!activeId || !rows.length) return;
    try {
      const rowsWithEmail = rows
        .filter((r) => r.email && r.email !== "")
        .map((r) => r._row_id);
      const res = await runDatasetStage(activeId, {
        stage: "verify-email",
        row_ids: rowsWithEmail.length > 0 ? rowsWithEmail : null,
      });
      startPolling("verify-email", res.batch_id, () => {
        reload();
        toast.success("Email verification complete");
      });
      toast.success(`Verifying ${res.total_rows} emails...`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to start verification");
    }
  };

  const handleComputeColumn = async () => {
    if (!activeId || !rows.length) return;
    try {
      const res = await runDatasetStage(activeId, {
        stage: "compute-column",
      });
      startPolling("compute-column", res.batch_id, () => {
        reload();
        toast.success("Column computation complete");
      });
      toast.success(`Computing column for ${res.total_rows} rows...`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to start computation");
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <ActionCard
        title="Find Email"
        description="Look up email addresses via Findymail"
        icon={Mail}
        onRun={handleFindEmail}
        disabled={!activeId || !rows.length}
        running={isStageRunning("find-email")}
        stageStatus={getStageStatus("find-email")}
      >
        <label className="flex items-center gap-2 text-xs text-clay-300 cursor-pointer">
          <input
            type="checkbox"
            checked={onlyMissing}
            onChange={(e) => setOnlyMissing(e.target.checked)}
            className="rounded border-clay-500 h-3 w-3"
          />
          Only missing emails ({missingEmailCount})
        </label>
      </ActionCard>

      <ActionCard
        title="Verify Email"
        description="Validate existing email addresses"
        icon={ShieldCheck}
        onRun={handleVerifyEmail}
        disabled={!activeId || !rows.length}
        running={isStageRunning("verify-email")}
        stageStatus={getStageStatus("verify-email")}
      />

      <ActionCard
        title="Compute Column"
        description="Add a formula or template-based column"
        icon={Calculator}
        onRun={handleComputeColumn}
        disabled={!activeId || !rows.length}
        running={isStageRunning("compute-column")}
        stageStatus={getStageStatus("compute-column")}
      />
    </div>
  );
}
