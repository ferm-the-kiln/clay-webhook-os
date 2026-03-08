"use client";

import { useEffect, useState, useRef, useMemo, useCallback } from "react";
import Link from "next/link";
import { fetchJobs, fetchJob, createJobStream } from "@/lib/api";
import type { JobListItem, Job } from "@/lib/types";
import { formatDuration, formatRelativeTime } from "@/lib/utils";
import { StatusBadge } from "./status-badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table";
import {
  Search,
  ChevronUp,
  ChevronDown,
  ChevronsUpDown,
  ChevronRight,
  ArrowUp,
  ArrowDown,
  Minus,
  X,
  RotateCcw,
  Send,
  Zap,
  Download,
  Copy,
  ClipboardCheck,
} from "lucide-react";
import Papa from "papaparse";
import { Badge } from "@/components/ui/badge";
import { Checkbox } from "@/components/ui/checkbox";
import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuTrigger,
  ContextMenuSeparator,
} from "@/components/ui/context-menu";
import { FeedbackButtons } from "@/components/feedback/feedback-buttons";
import { FormattedResult } from "@/components/playground/formatted-results";
import { AnimatePresence, motion } from "framer-motion";
import { toast } from "sonner";
import { runWebhook } from "@/lib/api";

const PRIORITY_ICONS: Record<string, typeof ArrowUp> = {
  high: ArrowUp,
  normal: Minus,
  low: ArrowDown,
};

const PRIORITY_COLORS: Record<string, string> = {
  high: "text-kiln-coral",
  normal: "text-clay-500",
  low: "text-clay-700",
};

const PAGE_SIZE = 25;

type SortKey = "skill" | "priority" | "status" | "duration_ms" | "created_at";
type SortDir = "asc" | "desc";

const PRIORITY_ORDER: Record<string, number> = { high: 0, normal: 1, low: 2 };

export function JobList() {
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [search, setSearch] = useState("");
  const [sortKey, setSortKey] = useState<SortKey>("created_at");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [page, setPage] = useState(0);
  const [selectedJob, setSelectedJob] = useState<Job | null>(null);
  const [detailOpen, setDetailOpen] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const esRef = useRef<EventSource | null>(null);

  useEffect(() => {
    let active = true;
    let pollId: ReturnType<typeof setInterval> | null = null;

    const refresh = () =>
      fetchJobs()
        .then((d) => active && setJobs(d.jobs))
        .catch(() => {});

    refresh();

    try {
      const es = createJobStream(() => {
        refresh();
      });
      esRef.current = es;

      es.onerror = () => {
        es.close();
        esRef.current = null;
        if (!pollId && active) {
          pollId = setInterval(refresh, 3000);
        }
      };
    } catch {
      pollId = setInterval(refresh, 3000);
    }

    return () => {
      active = false;
      if (esRef.current) esRef.current.close();
      if (pollId) clearInterval(pollId);
    };
  }, []);

  const filtered = useMemo(() => {
    if (!search.trim()) return jobs;
    const q = search.toLowerCase();
    return jobs.filter(
      (j) =>
        j.skill.toLowerCase().includes(q) ||
        j.status.toLowerCase().includes(q) ||
        j.id.toLowerCase().includes(q) ||
        (j.priority || "normal").toLowerCase().includes(q)
    );
  }, [jobs, search]);

  const sorted = useMemo(() => {
    const arr = [...filtered];
    arr.sort((a, b) => {
      let cmp = 0;
      switch (sortKey) {
        case "skill":
          cmp = a.skill.localeCompare(b.skill);
          break;
        case "priority":
          cmp =
            PRIORITY_ORDER[a.priority || "normal"] -
            PRIORITY_ORDER[b.priority || "normal"];
          break;
        case "status":
          cmp = a.status.localeCompare(b.status);
          break;
        case "duration_ms":
          cmp = (a.duration_ms || 0) - (b.duration_ms || 0);
          break;
        case "created_at":
          cmp = a.created_at - b.created_at;
          break;
      }
      return sortDir === "asc" ? cmp : -cmp;
    });
    return arr;
  }, [filtered, sortKey, sortDir]);

  const totalPages = Math.max(1, Math.ceil(sorted.length / PAGE_SIZE));
  const safePage = Math.min(page, totalPages - 1);
  const paged = sorted.slice(safePage * PAGE_SIZE, (safePage + 1) * PAGE_SIZE);

  // Reset page when search changes
  useEffect(() => {
    setPage(0);
  }, [search]);

  const handleSort = (key: SortKey) => {
    if (sortKey === key) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "created_at" ? "desc" : "asc");
    }
  };

  const handleRowClick = useCallback(async (jobId: string) => {
    try {
      const job = await fetchJob(jobId);
      setSelectedJob(job);
      setDetailOpen(true);
    } catch {
      // silently fail
    }
  }, []);

  const SortIcon = ({ col }: { col: SortKey }) => {
    if (sortKey !== col) return <ChevronsUpDown className="h-3 w-3 ml-1 opacity-40" />;
    return sortDir === "asc" ? (
      <ChevronUp className="h-3 w-3 ml-1 text-kiln-teal" />
    ) : (
      <ChevronDown className="h-3 w-3 ml-1 text-kiln-teal" />
    );
  };

  if (jobs.length === 0) {
    return (
      <EmptyState
        title="No jobs yet"
        description="Your queue is clear. Head to the Playground to test a skill, or set up a Batch run."
      >
        <Button asChild size="sm" className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold">
          <Link href="/run">Open Playground</Link>
        </Button>
      </EmptyState>
    );
  }

  return (
    <>
      {/* Search & filter bar */}
      <div className="flex items-center gap-3 mb-3">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-clay-500" />
          <Input
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by skill, status, ID..."
            className="pl-9 border-clay-700 bg-clay-900 text-clay-100 placeholder:text-clay-600 focus-visible:ring-kiln-teal/50 focus-visible:border-kiln-teal"
          />
          {search && (
            <button
              onClick={() => setSearch("")}
              className="absolute right-3 top-1/2 -translate-y-1/2 text-clay-500 hover:text-clay-300"
            >
              <X className="h-3.5 w-3.5" />
            </button>
          )}
        </div>
        {search && (
          <span className="text-xs text-clay-500">
            {filtered.length} result{filtered.length !== 1 ? "s" : ""}
          </span>
        )}
        <Button
          variant="outline"
          size="sm"
          className="border-clay-700 text-clay-400 hover:text-clay-200 ml-auto"
          onClick={() => {
            const rows = sorted.map((j) => ({
              id: j.id,
              skill: j.skill,
              status: j.status,
              duration_ms: j.duration_ms || "",
              retries: j.retry_count ?? 0,
              priority: j.priority || "normal",
              created_at: new Date(j.created_at * 1000).toISOString(),
            }));
            const csv = Papa.unparse(rows);
            const blob = new Blob([csv], { type: "text/csv" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `jobs-${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.csv`;
            a.click();
            URL.revokeObjectURL(url);
          }}
        >
          <Download className="h-3.5 w-3.5 mr-1.5" />
          Export CSV
        </Button>
      </div>

      <div className="rounded-xl border border-clay-800 bg-white shadow-sm overflow-hidden" aria-live="polite" aria-atomic="false">
        {/* Desktop table */}
        <div className="hidden sm:block overflow-x-auto">
          <Table>
            <TableHeader>
              <TableRow className="border-clay-800 hover:bg-transparent">
                <TableHead className="text-clay-500 text-xs uppercase tracking-wider w-10 px-3">
                  <Checkbox
                    checked={paged.length > 0 && paged.every((j) => selectedIds.has(j.id))}
                    onCheckedChange={(checked) => {
                      setSelectedIds((prev) => {
                        const next = new Set(prev);
                        paged.forEach((j) => (checked ? next.add(j.id) : next.delete(j.id)));
                        return next;
                      });
                    }}
                    className="border-clay-600 data-[state=checked]:bg-kiln-teal data-[state=checked]:border-kiln-teal"
                  />
                </TableHead>
                <TableHead className="text-clay-500 text-xs uppercase tracking-wider">Job ID</TableHead>
                <TableHead
                  className="text-clay-500 text-xs uppercase tracking-wider cursor-pointer select-none hover:text-clay-300"
                  onClick={() => handleSort("skill")}
                >
                  <span className="inline-flex items-center">
                    Skill <SortIcon col="skill" />
                  </span>
                </TableHead>
                <TableHead className="text-clay-500 text-xs uppercase tracking-wider">Row ID</TableHead>
                <TableHead
                  className="text-clay-500 text-xs uppercase tracking-wider cursor-pointer select-none hover:text-clay-300"
                  onClick={() => handleSort("priority")}
                >
                  <span className="inline-flex items-center">
                    Priority <SortIcon col="priority" />
                  </span>
                </TableHead>
                <TableHead
                  className="text-clay-500 text-xs uppercase tracking-wider cursor-pointer select-none hover:text-clay-300"
                  onClick={() => handleSort("status")}
                >
                  <span className="inline-flex items-center">
                    Status <SortIcon col="status" />
                  </span>
                </TableHead>
                <TableHead className="text-clay-500 text-xs uppercase tracking-wider">Retries</TableHead>
                <TableHead
                  className="text-clay-500 text-xs uppercase tracking-wider cursor-pointer select-none hover:text-clay-300"
                  onClick={() => handleSort("duration_ms")}
                >
                  <span className="inline-flex items-center">
                    Duration <SortIcon col="duration_ms" />
                  </span>
                </TableHead>
                <TableHead
                  className="text-clay-500 text-xs uppercase tracking-wider cursor-pointer select-none hover:text-clay-300"
                  onClick={() => handleSort("created_at")}
                >
                  <span className="inline-flex items-center">
                    Time <SortIcon col="created_at" />
                  </span>
                </TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paged.map((job) => {
                const prio = job.priority || "normal";
                const PrioIcon = PRIORITY_ICONS[prio];
                return (
                  <ContextMenu key={job.id}>
                    <ContextMenuTrigger asChild>
                      <TableRow
                        className="border-clay-800 hover:bg-muted/50 transition-colors cursor-pointer"
                        onClick={() => handleRowClick(job.id)}
                      >
                        <TableCell className="px-3" onClick={(e) => e.stopPropagation()}>
                          <Checkbox
                            checked={selectedIds.has(job.id)}
                            onCheckedChange={(checked) => {
                              setSelectedIds((prev) => {
                                const next = new Set(prev);
                                checked ? next.add(job.id) : next.delete(job.id);
                                return next;
                              });
                            }}
                            className="border-clay-600 data-[state=checked]:bg-kiln-teal data-[state=checked]:border-kiln-teal"
                          />
                        </TableCell>
                        <TableCell className="font-[family-name:var(--font-mono)] text-xs text-clay-400">
                          {job.id.slice(0, 8)}...
                        </TableCell>
                        <TableCell className="text-kiln-teal font-medium">
                          {job.skill}
                        </TableCell>
                        <TableCell className="text-clay-500 font-[family-name:var(--font-mono)] text-xs">
                          {job.row_id || "\u2014"}
                        </TableCell>
                        <TableCell>
                          <span className={`inline-flex items-center gap-1 text-xs font-medium uppercase ${PRIORITY_COLORS[prio]}`}>
                            <PrioIcon className="h-3 w-3" />
                            {prio}
                          </span>
                        </TableCell>
                        <TableCell>
                          <StatusBadge status={job.status} />
                        </TableCell>
                        <TableCell className="font-[family-name:var(--font-mono)] text-xs text-clay-500">
                          {(job.retry_count ?? 0) > 0 ? `${job.retry_count}/3` : "\u2014"}
                        </TableCell>
                        <TableCell className="font-[family-name:var(--font-mono)] text-xs">
                          {job.duration_ms ? formatDuration(job.duration_ms) : "\u2014"}
                        </TableCell>
                        <TableCell className="text-clay-500 text-xs" title={new Date(job.created_at * 1000).toLocaleString()}>
                          {formatRelativeTime(job.created_at)}
                        </TableCell>
                      </TableRow>
                    </ContextMenuTrigger>
                    <ContextMenuContent className="border-clay-700 bg-clay-900 min-w-[160px]">
                      <ContextMenuItem
                        onClick={() => handleRowClick(job.id)}
                        className="text-clay-300 focus:bg-kiln-teal/10 focus:text-kiln-teal"
                      >
                        <Search className="h-3.5 w-3.5 mr-2" />
                        View Details
                      </ContextMenuItem>
                      <ContextMenuItem
                        onClick={() => {
                          navigator.clipboard.writeText(job.id);
                          toast.success("Job ID copied");
                        }}
                        className="text-clay-300 focus:bg-kiln-teal/10 focus:text-kiln-teal"
                      >
                        <Copy className="h-3.5 w-3.5 mr-2" />
                        Copy Job ID
                      </ContextMenuItem>
                      <ContextMenuSeparator className="bg-clay-800" />
                      <ContextMenuItem
                        onClick={() => {
                          window.location.href = `/run?skill=${job.skill}`;
                        }}
                        className="text-clay-300 focus:bg-kiln-teal/10 focus:text-kiln-teal"
                      >
                        <RotateCcw className="h-3.5 w-3.5 mr-2" />
                        Re-run Skill
                      </ContextMenuItem>
                      <ContextMenuItem
                        onClick={() => {
                          const row = {
                            id: job.id,
                            skill: job.skill,
                            status: job.status,
                            duration_ms: job.duration_ms || "",
                            retries: job.retry_count ?? 0,
                            priority: job.priority || "normal",
                            created_at: new Date(job.created_at * 1000).toISOString(),
                          };
                          navigator.clipboard.writeText(JSON.stringify(row, null, 2));
                          toast.success("Job JSON copied");
                        }}
                        className="text-clay-300 focus:bg-kiln-teal/10 focus:text-kiln-teal"
                      >
                        <Download className="h-3.5 w-3.5 mr-2" />
                        Export JSON
                      </ContextMenuItem>
                    </ContextMenuContent>
                  </ContextMenu>
                );
              })}
            </TableBody>
          </Table>
        </div>

        {/* Mobile card view */}
        <div className="sm:hidden divide-y divide-clay-800">
          {paged.map((job) => (
            <button
              key={job.id}
              onClick={() => handleRowClick(job.id)}
              className="w-full text-left px-4 py-3 hover:bg-muted/50 transition-colors"
            >
              <div className="flex items-center justify-between mb-1">
                <span className="text-kiln-teal font-medium text-sm">{job.skill}</span>
                <StatusBadge status={job.status} />
              </div>
              <div className="flex items-center gap-3 text-xs text-clay-500">
                {job.duration_ms ? (
                  <span className="font-[family-name:var(--font-mono)]">{formatDuration(job.duration_ms)}</span>
                ) : null}
                <span>{formatRelativeTime(job.created_at)}</span>
              </div>
            </button>
          ))}
        </div>

        {/* Pagination */}
        {totalPages > 1 && (
          <div className="flex items-center justify-between border-t border-clay-800 px-4 py-2.5">
            <span className="text-xs text-clay-500">
              Showing {safePage * PAGE_SIZE + 1}-{Math.min((safePage + 1) * PAGE_SIZE, sorted.length)} of {sorted.length} jobs
            </span>
            <div className="flex items-center gap-2">
              <Button
                variant="outline"
                size="xs"
                disabled={safePage === 0}
                onClick={() => setPage((p) => p - 1)}
                className="border-clay-700 bg-clay-900 text-clay-400 hover:text-clay-200 disabled:opacity-30"
              >
                Previous
              </Button>
              <span className="text-xs text-clay-500 font-[family-name:var(--font-mono)]">
                {safePage + 1} / {totalPages}
              </span>
              <Button
                variant="outline"
                size="xs"
                disabled={safePage >= totalPages - 1}
                onClick={() => setPage((p) => p + 1)}
                className="border-clay-700 bg-clay-900 text-clay-400 hover:text-clay-200 disabled:opacity-30"
              >
                Next
              </Button>
            </div>
          </div>
        )}
      </div>

      {/* Job Detail Panel */}
      <Sheet open={detailOpen} onOpenChange={setDetailOpen}>
        <SheetContent side="right" className="w-full sm:max-w-lg bg-clay-900 border-clay-800 overflow-y-auto">
          {selectedJob && (
            <>
              <SheetHeader>
                <SheetTitle className="text-clay-100 font-[family-name:var(--font-sans)]">
                  Job Detail
                </SheetTitle>
                <SheetDescription className="text-clay-500 font-[family-name:var(--font-mono)] text-xs">
                  {selectedJob.id}
                </SheetDescription>
              </SheetHeader>
              <div className="space-y-4 px-4 pb-4">
                {/* Status row */}
                <div className="flex items-center gap-3 flex-wrap">
                  <StatusBadge status={selectedJob.status} />
                  <span className="text-kiln-teal font-medium">{selectedJob.skill}</span>
                  {selectedJob.duration_ms > 0 && (
                    <Badge variant="outline" className="bg-clay-800 text-clay-400 border-clay-700 text-xs">
                      {formatDuration(selectedJob.duration_ms)}
                    </Badge>
                  )}
                  {selectedJob.cost_est_usd != null && selectedJob.cost_est_usd > 0 && (
                    <Badge variant="outline" className="bg-clay-800 text-clay-400 border-clay-700 text-xs">
                      ${selectedJob.cost_est_usd.toFixed(4)}
                    </Badge>
                  )}
                </div>

                {/* Quick actions */}
                <div className="flex gap-2 flex-wrap">
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-clay-700 text-clay-400 hover:text-clay-200"
                    onClick={() => {
                      window.location.href = `/run?skill=${selectedJob.skill}`;
                    }}
                  >
                    <RotateCcw className="h-3.5 w-3.5 mr-1.5" />
                    Run again
                  </Button>
                  <Button
                    variant="outline"
                    size="sm"
                    className="border-clay-700 text-clay-400 hover:text-clay-200"
                    onClick={() => {
                      navigator.clipboard.writeText(selectedJob.id);
                      toast.success("Job ID copied");
                    }}
                  >
                    <Copy className="h-3.5 w-3.5 mr-1.5" />
                    Copy ID
                  </Button>
                </div>

                {selectedJob.error && (
                  <div className="rounded-lg bg-kiln-coral/10 border border-kiln-coral/20 p-3">
                    <p className="text-xs font-medium text-kiln-coral mb-1">Error</p>
                    <p className="text-sm text-kiln-coral/80 font-[family-name:var(--font-mono)]">
                      {selectedJob.error}
                    </p>
                  </div>
                )}

                {/* Output — formatted */}
                {selectedJob.result && (
                  <div>
                    <div className="flex items-center justify-between mb-2">
                      <p className="text-xs text-clay-500 uppercase tracking-wider font-[family-name:var(--font-sans)]">
                        Output
                      </p>
                      <button
                        onClick={() => {
                          navigator.clipboard.writeText(JSON.stringify(selectedJob.result, null, 2));
                          toast.success("Output JSON copied");
                        }}
                        className="text-xs text-clay-500 hover:text-clay-300 flex items-center gap-1 transition-colors"
                      >
                        <Copy className="h-3 w-3" />
                        Copy JSON
                      </button>
                    </div>
                    <div className="rounded-lg bg-clay-950 border border-clay-800 overflow-hidden max-h-96 overflow-y-auto">
                      <FormattedResult skill={selectedJob.skill} data={selectedJob.result} />
                    </div>
                  </div>
                )}

                {/* Feedback */}
                {selectedJob.status === "completed" && (
                  <div>
                    <p className="text-xs text-clay-500 uppercase tracking-wider mb-2 font-[family-name:var(--font-sans)]">
                      Rate Output
                    </p>
                    <FeedbackButtons
                      jobId={selectedJob.id}
                      skill={selectedJob.skill}
                      existing={selectedJob.feedback}
                    />
                  </div>
                )}

                {/* Metadata grid */}
                <div className="grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <p className="text-xs text-clay-500 mb-0.5">Priority</p>
                    <p className="text-clay-200 capitalize">{selectedJob.priority || "normal"}</p>
                  </div>
                  <div>
                    <p className="text-xs text-clay-500 mb-0.5">Retries</p>
                    <p className="text-clay-200">{selectedJob.retry_count ?? 0} / 3</p>
                  </div>
                  <div>
                    <p className="text-xs text-clay-500 mb-0.5">Created</p>
                    <p className="text-clay-200 text-xs font-[family-name:var(--font-mono)]">
                      {new Date(selectedJob.created_at * 1000).toLocaleString()}
                    </p>
                  </div>
                  {selectedJob.completed_at && (
                    <div>
                      <p className="text-xs text-clay-500 mb-0.5">Completed</p>
                      <p className="text-clay-200 text-xs font-[family-name:var(--font-mono)]">
                        {new Date(selectedJob.completed_at * 1000).toLocaleString()}
                      </p>
                    </div>
                  )}
                  {selectedJob.input_tokens_est != null && selectedJob.input_tokens_est > 0 && (
                    <div>
                      <p className="text-xs text-clay-500 mb-0.5">Input Tokens</p>
                      <p className="text-clay-200 text-xs font-[family-name:var(--font-mono)]">
                        {selectedJob.input_tokens_est.toLocaleString()}
                      </p>
                    </div>
                  )}
                  {selectedJob.output_tokens_est != null && selectedJob.output_tokens_est > 0 && (
                    <div>
                      <p className="text-xs text-clay-500 mb-0.5">Output Tokens</p>
                      <p className="text-clay-200 text-xs font-[family-name:var(--font-mono)]">
                        {selectedJob.output_tokens_est.toLocaleString()}
                      </p>
                    </div>
                  )}
                </div>
              </div>
            </>
          )}
        </SheetContent>
      </Sheet>

      {/* Floating bulk action bar */}
      <AnimatePresence>
        {selectedIds.size > 0 && (
          <motion.div
            initial={{ y: 80, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            exit={{ y: 80, opacity: 0 }}
            transition={{ type: "spring", damping: 25, stiffness: 300 }}
            className="fixed bottom-16 md:bottom-6 left-1/2 -translate-x-1/2 z-40 flex items-center gap-3 rounded-xl border border-clay-700 bg-clay-900 px-4 py-2.5 shadow-2xl"
          >
            <span className="text-sm text-clay-300 font-medium">
              {selectedIds.size} selected
            </span>
            <div className="h-4 w-px bg-clay-700" />
            <Button
              size="sm"
              variant="outline"
              className="border-clay-700 text-clay-400 hover:text-clay-200"
              onClick={() => {
                const selectedJobs = sorted.filter((j) => selectedIds.has(j.id));
                const rows = selectedJobs.map((j) => ({
                  id: j.id,
                  skill: j.skill,
                  status: j.status,
                  duration_ms: j.duration_ms || "",
                  retries: j.retry_count ?? 0,
                  priority: j.priority || "normal",
                  created_at: new Date(j.created_at * 1000).toISOString(),
                }));
                const csv = Papa.unparse(rows);
                const blob = new Blob([csv], { type: "text/csv" });
                const url = URL.createObjectURL(blob);
                const a = document.createElement("a");
                a.href = url;
                a.download = `jobs-selected-${new Date().toISOString().slice(0, 19).replace(/:/g, "-")}.csv`;
                a.click();
                URL.revokeObjectURL(url);
                toast.success(`Exported ${selectedJobs.length} jobs`);
              }}
            >
              <Download className="h-3.5 w-3.5 mr-1.5" />
              Export
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="text-clay-500 hover:text-clay-300"
              onClick={() => setSelectedIds(new Set())}
            >
              <X className="h-3.5 w-3.5 mr-1" />
              Clear
            </Button>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
