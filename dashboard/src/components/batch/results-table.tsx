"use client";

import Papa from "papaparse";
import type { Job } from "@/lib/types";
import { StatusBadge } from "@/components/dashboard/status-badge";
import { formatDuration } from "@/lib/utils";

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
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 overflow-hidden">
      <div className="flex items-center justify-between border-b border-zinc-800 px-4 py-2">
        <span className="text-xs text-zinc-500 uppercase tracking-wide">
          Results ({jobs.length} rows)
        </span>
        <button
          onClick={downloadCsv}
          className="rounded-lg bg-teal-500/20 px-3 py-1 text-xs font-medium text-teal-400 hover:bg-teal-500/30 transition-colors"
        >
          Download CSV
        </button>
      </div>
      <div className="overflow-x-auto max-h-96">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-zinc-800 text-left text-xs text-zinc-500">
              <th className="px-3 py-2">#</th>
              <th className="px-3 py-2">Row ID</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Duration</th>
              <th className="px-3 py-2">Output</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-800">
            {jobs.map((job, i) => (
              <tr key={job.id} className="hover:bg-zinc-800/50">
                <td className="px-3 py-2 text-zinc-500 font-mono text-xs">{i + 1}</td>
                <td className="px-3 py-2 text-zinc-400 font-mono text-xs">{job.row_id || "—"}</td>
                <td className="px-3 py-2"><StatusBadge status={job.status} /></td>
                <td className="px-3 py-2 font-mono text-xs">
                  {job.duration_ms ? formatDuration(job.duration_ms) : "—"}
                </td>
                <td className="px-3 py-2 text-zinc-300 text-xs max-w-md truncate">
                  {job.error
                    ? <span className="text-red-400">{job.error}</span>
                    : job.result
                      ? JSON.stringify(job.result).slice(0, 120) + "..."
                      : "—"}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
