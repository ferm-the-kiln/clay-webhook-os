"use client";

import { useEffect, useState } from "react";
import { fetchJobs } from "@/lib/api";
import type { JobListItem } from "@/lib/types";
import { formatDuration, formatTimestamp } from "@/lib/utils";
import { StatusBadge } from "./status-badge";
import { EmptyState } from "@/components/ui/empty-state";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";

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
      <EmptyState
        title="No jobs yet"
        description="Run a webhook or batch to see results here."
      />
    );
  }

  return (
    <div className="rounded-xl border border-clay-800 bg-clay-900 overflow-hidden">
      <Table>
        <TableHeader>
          <TableRow className="border-clay-800 hover:bg-transparent">
            <TableHead className="text-clay-500 text-xs uppercase tracking-wide">Job ID</TableHead>
            <TableHead className="text-clay-500 text-xs uppercase tracking-wide">Skill</TableHead>
            <TableHead className="text-clay-500 text-xs uppercase tracking-wide">Row ID</TableHead>
            <TableHead className="text-clay-500 text-xs uppercase tracking-wide">Status</TableHead>
            <TableHead className="text-clay-500 text-xs uppercase tracking-wide">Duration</TableHead>
            <TableHead className="text-clay-500 text-xs uppercase tracking-wide">Time</TableHead>
          </TableRow>
        </TableHeader>
        <TableBody>
          {jobs.map((job) => (
            <TableRow
              key={job.id}
              className="border-clay-800 hover:bg-clay-800/50 transition-colors"
            >
              <TableCell className="font-[family-name:var(--font-mono)] text-xs text-clay-400">
                {job.id}
              </TableCell>
              <TableCell className="text-kiln-teal font-medium">
                {job.skill}
              </TableCell>
              <TableCell className="text-clay-500 font-[family-name:var(--font-mono)] text-xs">
                {job.row_id || "\u2014"}
              </TableCell>
              <TableCell>
                <StatusBadge status={job.status} />
              </TableCell>
              <TableCell className="font-[family-name:var(--font-mono)] text-xs">
                {job.duration_ms ? formatDuration(job.duration_ms) : "\u2014"}
              </TableCell>
              <TableCell className="text-clay-500 text-xs">
                {formatTimestamp(job.created_at)}
              </TableCell>
            </TableRow>
          ))}
        </TableBody>
      </Table>
    </div>
  );
}
