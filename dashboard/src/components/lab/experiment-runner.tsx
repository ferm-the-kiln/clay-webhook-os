"use client";

import { useState } from "react";
import type { Experiment } from "@/lib/types";
import { runExperiment } from "@/lib/api";
import { Textarea } from "@/components/ui/textarea";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Loader2, Play } from "lucide-react";
import { toast } from "sonner";

export function ExperimentRunner({
  experiment,
  onRan,
}: {
  experiment: Experiment;
  onRan?: () => void;
}) {
  const [csvText, setCsvText] = useState("");
  const [running, setRunning] = useState(false);
  const [result, setResult] = useState<{
    total_rows: number;
    distribution: { job_id: string; variant_id: string }[];
  } | null>(null);

  const parseCSV = (text: string): Record<string, unknown>[] => {
    const lines = text.trim().split("\n");
    if (lines.length < 2) return [];
    const headers = lines[0].split(",").map((h) => h.trim());
    return lines.slice(1).map((line) => {
      const values = line.split(",").map((v) => v.trim());
      const row: Record<string, unknown> = {};
      headers.forEach((h, i) => {
        row[h] = values[i] || "";
      });
      return row;
    });
  };

  const handleRun = async () => {
    const rows = parseCSV(csvText);
    if (rows.length === 0) {
      toast.error("No rows parsed. Ensure CSV has header + data rows.");
      return;
    }

    setRunning(true);
    try {
      const res = await runExperiment(experiment.id, { rows });
      setResult(res);
      toast.success(`Experiment started: ${res.total_rows} rows distributed`);
      onRan?.();
    } catch (e) {
      toast.error("Failed to run", { description: (e as Error).message });
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs text-clay-500 uppercase tracking-wide mb-2 block">
          Paste CSV Data
        </label>
        <Textarea
          value={csvText}
          onChange={(e) => setCsvText(e.target.value)}
          placeholder={`first_name,company_name,industry\nSarah,Acme,SaaS\nMarcus,Snowflake,Data`}
          className="h-40 font-[family-name:var(--font-mono)] text-sm border-clay-700 bg-clay-950 text-clay-200 placeholder:text-clay-600 resize-none"
        />
        <p className="text-xs text-clay-600 mt-1">
          Rows will be round-robin distributed across{" "}
          {experiment.variant_ids.length} variants.
        </p>
      </div>

      <Button
        onClick={handleRun}
        disabled={running || !csvText.trim()}
        className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
      >
        {running ? (
          <>
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            Running...
          </>
        ) : (
          <>
            <Play className="h-4 w-4 mr-2" />
            Run Experiment
          </>
        )}
      </Button>

      {result && (
        <div className="rounded-lg border border-clay-800 bg-clay-950 p-4 space-y-2">
          <p className="text-sm text-clay-200">
            Distributed {result.total_rows} rows:
          </p>
          <div className="flex flex-wrap gap-2">
            {experiment.variant_ids.map((vid) => {
              const count = result.distribution.filter(
                (d) => d.variant_id === vid
              ).length;
              return (
                <Badge
                  key={vid}
                  variant="outline"
                  className="border-clay-700 text-clay-300"
                >
                  {vid}: {count} rows
                </Badge>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
