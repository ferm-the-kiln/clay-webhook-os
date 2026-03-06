"use client";

import { useEffect, useState } from "react";
import { fetchJobs } from "@/lib/api";
import type { JobListItem } from "@/lib/types";
import { formatDuration, formatTimestamp } from "@/lib/utils";
import { StatusBadge } from "./status-badge";

export function JobList() {
  const [jobs, setJobs] = useState<JobListItem[]>([]);

  useEffect(() => {
    let active = true;
    const poll = () =>
      fetchJobs()
        .then((d) => active && setJobs(d.jobs))
        .catch(() => {});
    poll();
    const id = setInterval(poll, 3000);
    return () => {
      active = false;
      clearInterval(id);
    };
  }, []);

  if (jobs.length === 0) {
    return (
      <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-8 text-center text-zinc-500">
        No jobs yet. Run a webhook or batch to see results here.
      </div>
    );
  }

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 overflow-hidden">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-zinc-800 text-left text-xs text-zinc-500 uppercase tracking-wide">
            <th className="px-4 py-3">Job ID</th>
            <th className="px-4 py-3">Skill</th>
            <th className="px-4 py-3">Row ID</th>
            <th className="px-4 py-3">Status</th>
            <th className="px-4 py-3">Duration</th>
            <th className="px-4 py-3">Time</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-zinc-800">
          {jobs.map((job) => (
            <tr key={job.id} className="hover:bg-zinc-800/50 transition-colors">
              <td className="px-4 py-3 font-mono text-xs text-zinc-400">{job.id}</td>
              <td className="px-4 py-3 text-teal-400">{job.skill}</td>
              <td className="px-4 py-3 text-zinc-500 font-mono text-xs">{job.row_id || "—"}</td>
              <td className="px-4 py-3"><StatusBadge status={job.status} /></td>
              <td className="px-4 py-3 font-mono text-xs">
                {job.duration_ms ? formatDuration(job.duration_ms) : "—"}
              </td>
              <td className="px-4 py-3 text-zinc-500 text-xs">{formatTimestamp(job.created_at)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
