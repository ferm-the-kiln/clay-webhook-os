"use client";

import { useState } from "react";
import { Upload, Users, Building2 } from "lucide-react";
import { Input } from "@/components/ui/input";
import { ActionCard } from "./action-card";
import { DatasetImportDialog } from "@/components/pipeline/dataset-import-dialog";
import { useDatasetContext } from "@/contexts/dataset-context";
import { runDatasetStage } from "@/lib/api";
import { toast } from "sonner";
import type { StageStatus } from "@/lib/types";

interface SourceActionsProps {
  startPolling: (stage: string, batchId: string, onComplete?: () => void) => void;
  getStageStatus: (stage: string) => StageStatus | null;
  isStageRunning: (stage: string) => boolean;
}

export function SourceActions({ startPolling, getStageStatus, isStageRunning }: SourceActionsProps) {
  const { activeId, rows, reload, reloadDatasets, setActiveId } = useDatasetContext();
  const [showImport, setShowImport] = useState(false);
  const [leadQuery, setLeadQuery] = useState("");
  const [leadTitles, setLeadTitles] = useState("");
  const [leadLimit, setLeadLimit] = useState("25");

  const handleImport = () => {
    setShowImport(true);
  };

  const handleGenerateLeads = async () => {
    if (!activeId || !leadQuery.trim()) {
      toast.error("Enter a search query first");
      return;
    }
    try {
      const config: Record<string, unknown> = { query: leadQuery.trim() };
      if (leadTitles.trim()) {
        config.job_titles = leadTitles.split(",").map((t) => t.trim()).filter(Boolean);
      }
      config.limit = parseInt(leadLimit, 10) || 25;

      const res = await runDatasetStage(activeId, {
        stage: "generate-leads",
        config,
      });
      startPolling("generate-leads", res.batch_id, () => {
        reload();
        toast.success("Lead generation complete");
      });
      toast.success(`Generating leads for "${leadQuery}"...`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to generate leads");
    }
  };

  const handleEnrichCompany = async () => {
    if (!activeId || !rows.length) return;
    try {
      const rowsWithDomain = rows
        .filter((r) => r.company_domain || r.domain)
        .map((r) => r._row_id);
      const res = await runDatasetStage(activeId, {
        stage: "enrich-company",
        row_ids: rowsWithDomain.length > 0 ? rowsWithDomain : null,
      });
      startPolling("enrich-company", res.batch_id, () => {
        reload();
        toast.success("Company enrichment complete");
      });
      toast.success(`Enriching companies for ${res.total_rows} rows...`);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to start enrichment");
    }
  };

  return (
    <div className="flex flex-col gap-3">
      <ActionCard
        title="Import CSV"
        description="Upload a CSV file to create or add to your dataset"
        icon={Upload}
        onRun={handleImport}
      />

      <ActionCard
        title="Generate Leads"
        description="Find new prospects matching your criteria"
        icon={Users}
        onRun={handleGenerateLeads}
        disabled={!activeId}
        running={isStageRunning("generate-leads")}
        stageStatus={getStageStatus("generate-leads")}
      >
        <div className="flex flex-col gap-2">
          <Input
            value={leadQuery}
            onChange={(e) => setLeadQuery(e.target.value)}
            placeholder="e.g. SaaS companies in NYC"
            className="h-7 text-xs bg-clay-700 border-clay-600"
          />
          <Input
            value={leadTitles}
            onChange={(e) => setLeadTitles(e.target.value)}
            placeholder="Job titles (comma separated)"
            className="h-7 text-xs bg-clay-700 border-clay-600"
          />
          <Input
            value={leadLimit}
            onChange={(e) => setLeadLimit(e.target.value)}
            placeholder="Limit (default 25)"
            type="number"
            className="h-7 text-xs bg-clay-700 border-clay-600 w-24"
          />
        </div>
      </ActionCard>

      <ActionCard
        title="Enrich Company"
        description="Look up company details from domain column"
        icon={Building2}
        onRun={handleEnrichCompany}
        disabled={!activeId || !rows.length}
        running={isStageRunning("enrich-company")}
        stageStatus={getStageStatus("enrich-company")}
      />

      <DatasetImportDialog
        open={showImport}
        onOpenChange={setShowImport}
        onCreated={(id) => {
          setActiveId(id);
          reloadDatasets();
          reload();
          setShowImport(false);
        }}
      />
    </div>
  );
}
