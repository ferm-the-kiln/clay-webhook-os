"use client";

import Papa from "papaparse";
import type { Job } from "@/lib/types";
import { StatusBadge } from "@/components/dashboard/status-badge";
import { formatDuration } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import { Download } from "lucide-react";

export function ResultsTable({
  jobs,
  originalRows,
}: {
  jobs: Job[];
  originalRows: Record<string, string>[];
}) {
  const downloadCsv = () => {
    const rows = jobs.map((job, i) => {
      const original = originalRows[i] || {};
      const result = job.result || {};
      return {
        ...original,
        _status: job.status,
        _duration_ms: job.duration_ms,
        _error: job.error || "",
        ...Object.fromEntries(
          Object.entries(result).map(([k, v]) => [
            `_result_${k}`,
            typeof v === "string" ? v : JSON.stringify(v),
          ])
        ),
      };
    });

    const csv = Papa.unparse(rows);
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `batch-results-${Date.now()}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="rounded-xl border border-clay-800 bg-clay-900 overflow-hidden">
      <div className="flex items-center justify-between border-b border-clay-800 px-4 py-2">
        <span className="text-xs text-clay-500 uppercase tracking-wide font-[family-name:var(--font-sans)]">
          Results ({jobs.length} rows)
        </span>
        <Button
          variant="outline"
          size="sm"
          onClick={downloadCsv}
          className="bg-kiln-teal/10 text-kiln-teal border-kiln-teal/30 hover:bg-kiln-teal/20 hover:text-kiln-teal"
        >
          <Download className="h-3.5 w-3.5 mr-1.5" />
          Download CSV
        </Button>
      </div>
      <div className="overflow-x-auto max-h-96">
        <Table>
          <TableHeader>
            <TableRow className="border-clay-800 hover:bg-transparent">
              <TableHead className="text-clay-500 text-xs">#</TableHead>
              <TableHead className="text-clay-500 text-xs">Row ID</TableHead>
              <TableHead className="text-clay-500 text-xs">Status</TableHead>
              <TableHead className="text-clay-500 text-xs">Duration</TableHead>
              <TableHead className="text-clay-500 text-xs">Output</TableHead>
            </TableRow>
          </TableHeader>
          <TableBody>
            {jobs.map((job, i) => (
              <TableRow
                key={job.id}
                className="border-clay-800 hover:bg-clay-800/50"
              >
                <TableCell className="text-clay-500 font-[family-name:var(--font-mono)] text-xs">
                  {i + 1}
                </TableCell>
                <TableCell className="text-clay-400 font-[family-name:var(--font-mono)] text-xs">
                  {job.row_id || "\u2014"}
                </TableCell>
                <TableCell>
                  <StatusBadge status={job.status} />
                </TableCell>
                <TableCell className="font-[family-name:var(--font-mono)] text-xs">
                  {job.duration_ms ? formatDuration(job.duration_ms) : "\u2014"}
                </TableCell>
                <TableCell className="text-clay-300 text-xs max-w-md truncate">
                  {job.error ? (
                    <span className="text-kiln-coral">{job.error}</span>
                  ) : job.result ? (
                    JSON.stringify(job.result).slice(0, 120) + "..."
                  ) : (
                    "\u2014"
                  )}
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </div>
    </div>
  );
}
