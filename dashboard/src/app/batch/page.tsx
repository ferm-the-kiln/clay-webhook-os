"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import { Header } from "@/components/layout/header";
import { CsvUploader } from "@/components/batch/csv-uploader";
import { CsvPreview } from "@/components/batch/csv-preview";
import { ColumnMapper, autoMap } from "@/components/batch/column-mapper";
import { BatchProgress } from "@/components/batch/batch-progress";
import { ResultsTable } from "@/components/batch/results-table";
import { SkillSelector } from "@/components/playground/skill-selector";
import { ModelSelector } from "@/components/playground/model-selector";
import { runBatch, fetchJob } from "@/lib/api";
import type { Job } from "@/lib/types";
import type { Model } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import { Rocket, RotateCcw } from "lucide-react";

type Phase = "upload" | "configure" | "processing" | "done";

export default function BatchPage() {
  const [phase, setPhase] = useState<Phase>("upload");
  const [headers, setHeaders] = useState<string[]>([]);
  const [rows, setRows] = useState<Record<string, string>[]>([]);
  const [skill, setSkill] = useState("");
  const [model, setModel] = useState<Model>("sonnet");
  const [mapping, setMapping] = useState<Record<string, string>>({});
  const [jobIds, setJobIds] = useState<string[]>([]);
  const [jobs, setJobs] = useState<Job[]>([]);
  const pollingRef = useRef<ReturnType<typeof setInterval> | null>(null);

  const handleParsed = useCallback(
    (h: string[], r: Record<string, string>[]) => {
      setHeaders(h);
      setRows(r);
      setPhase("configure");
    },
    []
  );

  const handleSkillChange = (s: string) => {
    setSkill(s);
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
    if (!skill) return;
    const mappedRows = buildMappedRows();

    setPhase("processing");
    setJobs(Array(mappedRows.length).fill(null));

    try {
      const res = await runBatch({
        skill,
        rows: mappedRows,
        model,
      });
      setJobIds(res.job_ids);
    } catch (e) {
      setPhase("configure");
      alert(`Batch failed: ${(e as Error).message}`);
    }
  };

  useEffect(() => {
    if (phase !== "processing" || jobIds.length === 0) return;

    const poll = async () => {
      const updated = await Promise.all(jobIds.map((id) => fetchJob(id)));
      setJobs(updated);

      const allDone = updated.every(
        (j) => j.status === "completed" || j.status === "failed"
      );
      if (allDone) {
        setPhase("done");
        if (pollingRef.current) clearInterval(pollingRef.current);
      }
    };

    poll();
    pollingRef.current = setInterval(poll, 2000);
    return () => {
      if (pollingRef.current) clearInterval(pollingRef.current);
    };
  }, [phase, jobIds]);

  const completed = jobs.filter((j) => j?.status === "completed").length;
  const failed = jobs.filter((j) => j?.status === "failed").length;

  const handleReset = () => {
    setPhase("upload");
    setHeaders([]);
    setRows([]);
    setSkill("");
    setMapping({});
    setJobIds([]);
    setJobs([]);
  };

  return (
    <div className="flex flex-col h-full">
      <Header title="Batch Processing" />
      <div className="flex-1 overflow-auto p-6 space-y-6">
        {phase === "upload" && <CsvUploader onParsed={handleParsed} />}

        {(phase === "configure" || phase === "processing" || phase === "done") && (
          <>
            <CsvPreview headers={headers} rows={rows} />

            {phase === "configure" && (
              <>
                <div className="grid grid-cols-2 gap-4">
                  <SkillSelector value={skill} onChange={handleSkillChange} />
                  <ModelSelector value={model} onChange={setModel} />
                </div>

                {skill && (
                  <ColumnMapper
                    skill={skill}
                    csvHeaders={headers}
                    mapping={mapping}
                    onMappingChange={setMapping}
                  />
                )}

                <Button
                  onClick={handleProcess}
                  disabled={!skill}
                  className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold transition-all duration-200"
                >
                  <Rocket className="h-4 w-4 mr-2" />
                  Process All ({rows.length} rows)
                </Button>
              </>
            )}

            {(phase === "processing" || phase === "done") && (
              <>
                <BatchProgress
                  total={jobIds.length}
                  completed={completed}
                  failed={failed}
                />
                {jobs.some((j) => j !== null) && (
                  <ResultsTable
                    jobs={jobs.filter((j): j is Job => j !== null)}
                    originalRows={rows}
                  />
                )}
                {phase === "done" && (
                  <Button
                    variant="outline"
                    onClick={handleReset}
                    className="border-clay-700 bg-clay-900 text-clay-300 hover:bg-clay-800 hover:text-clay-100"
                  >
                    <RotateCcw className="h-4 w-4 mr-2" />
                    Start New Batch
                  </Button>
                )}
              </>
            )}
          </>
        )}
      </div>
    </div>
  );
}
