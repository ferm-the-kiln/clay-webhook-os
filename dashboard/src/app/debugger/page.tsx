"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Header } from "@/components/layout/header";
import { DebugFilters } from "@/components/debugger/debug-filters";
import { RequestList } from "@/components/debugger/request-list";
import { RequestDetail } from "@/components/debugger/request-detail";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  fetchJobs,
  fetchStats,
  fetchSkills,
  createJobStream,
} from "@/lib/api";
import type { JobListItem, Stats } from "@/lib/types";
import { cn, formatDuration, formatPercent, formatNumber } from "@/lib/utils";
import {
  Activity,
  Zap,
  AlertTriangle,
  Timer,
  RefreshCw,
  Pause,
  Play,
} from "lucide-react";
import { toast } from "sonner";

export default function DebuggerPage() {
  // --- Data state ---
  const [jobs, setJobs] = useState<JobListItem[]>([]);
  const [stats, setStats] = useState<Stats | null>(null);
  const [skills, setSkills] = useState<string[]>([]);
  const [selectedJobId, setSelectedJobId] = useState<string | null>(null);

  // --- Filter state ---
  const [skillFilter, setSkillFilter] = useState("all");
  const [statusFilter, setStatusFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");

  // --- UI state ---
  const [streaming, setStreaming] = useState(true);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // --- Load initial data ---
  const loadJobs = useCallback(() => {
    fetchJobs()
      .then((res) => {
        setJobs(res.jobs.sort((a, b) => b.created_at - a.created_at));
        setLastUpdated(new Date());
      })
      .catch(() => toast.error("Failed to load jobs"));
  }, []);

  const loadStats = useCallback(() => {
    fetchStats()
      .then((s) => setStats(s))
      .catch(() => {});
  }, []);

  useEffect(() => {
    loadJobs();
    loadStats();
    fetchSkills()
      .then((res) => setSkills(res.skills))
      .catch(() => {});
  }, [loadJobs, loadStats]);

  // --- Auto-refresh stats every 10s ---
  useEffect(() => {
    const id = setInterval(loadStats, 10000);
    return () => clearInterval(id);
  }, [loadStats]);

  // --- SSE Stream ---
  useEffect(() => {
    if (!streaming) {
      if (eventSourceRef.current) {
        eventSourceRef.current.close();
        eventSourceRef.current = null;
      }
      return;
    }

    const es = createJobStream((eventType, data) => {
      const jobData = data as unknown as JobListItem;
      if (eventType === "job_created") {
        setJobs((prev) => [jobData, ...prev]);
        setLastUpdated(new Date());
      } else if (eventType === "job_updated") {
        setJobs((prev) =>
          prev.map((j) => (j.id === jobData.id ? { ...j, ...jobData } : j))
        );
        setLastUpdated(new Date());
      }
    });

    eventSourceRef.current = es;

    es.onerror = () => {
      // EventSource auto-reconnects; we just track the state
    };

    return () => {
      es.close();
      eventSourceRef.current = null;
    };
  }, [streaming]);

  // --- Filtered jobs ---
  const filteredJobs = jobs.filter((job) => {
    if (skillFilter !== "all" && job.skill !== skillFilter) return false;
    if (statusFilter !== "all" && job.status !== statusFilter) return false;
    if (searchQuery) {
      const q = searchQuery.toLowerCase();
      if (
        !job.skill.toLowerCase().includes(q) &&
        !job.id.toLowerCase().includes(q)
      ) {
        return false;
      }
    }
    return true;
  });

  // --- Stats cards ---
  const totalRequests = stats?.total_processed ?? 0;
  const avgDuration = stats?.avg_duration_ms ?? 0;
  const cacheHitRate = stats?.cache_hit_rate ?? 0;
  const errorRate =
    totalRequests > 0
      ? (stats?.total_failed ?? 0) / totalRequests
      : 0;

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Debugger"
        lastUpdated={lastUpdated}
        onRefresh={loadJobs}
      />

      <div className="flex-1 overflow-auto p-4 md:p-6 space-y-6 pb-20 md:pb-6">
        {/* Stats summary */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
          <StatCard
            label="Total Requests"
            value={formatNumber(totalRequests)}
            icon={Activity}
            accent="text-kiln-teal"
          />
          <StatCard
            label="Avg Duration"
            value={formatDuration(avgDuration)}
            icon={Timer}
            accent="text-kiln-indigo"
          />
          <StatCard
            label="Cache Hit Rate"
            value={formatPercent(cacheHitRate)}
            icon={Zap}
            accent="text-kiln-mustard"
          />
          <StatCard
            label="Error Rate"
            value={formatPercent(errorRate)}
            icon={AlertTriangle}
            accent={errorRate > 0.1 ? "text-kiln-coral" : "text-status-success"}
          />
        </div>

        {/* Filters + Stream toggle */}
        <div className="flex items-center justify-between gap-4">
          <DebugFilters
            skills={skills}
            skillFilter={skillFilter}
            onSkillFilterChange={setSkillFilter}
            statusFilter={statusFilter}
            onStatusFilterChange={setStatusFilter}
            searchQuery={searchQuery}
            onSearchQueryChange={setSearchQuery}
          />
          <div className="flex items-center gap-2 shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setStreaming(!streaming)}
              className={cn(
                "border-clay-700 h-9",
                streaming
                  ? "text-status-success hover:text-status-success"
                  : "text-clay-400 hover:text-clay-200"
              )}
            >
              {streaming ? (
                <>
                  <Pause className="h-3.5 w-3.5 mr-1.5" />
                  Live
                </>
              ) : (
                <>
                  <Play className="h-3.5 w-3.5 mr-1.5" />
                  Paused
                </>
              )}
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={loadJobs}
              className="border-clay-700 text-clay-200 hover:text-clay-200 h-9"
            >
              <RefreshCw className="h-3.5 w-3.5 mr-1.5" />
              Refresh
            </Button>
          </div>
        </div>

        {/* Streaming indicator */}
        {streaming && (
          <div className="flex items-center gap-2 text-xs text-clay-400">
            <span className="relative flex h-2 w-2">
              <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-status-success opacity-75" />
              <span className="relative inline-flex rounded-full h-2 w-2 bg-status-success" />
            </span>
            Listening for new requests...
            <Badge variant="secondary" className="text-[10px] ml-1">
              {filteredJobs.length} shown
            </Badge>
          </div>
        )}

        {/* Main content: List + Detail */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 min-h-[500px]">
          {/* Request list */}
          <Card className="flex flex-col overflow-hidden">
            <div className="px-4 py-2.5 bg-clay-800 border-b border-clay-600 flex items-center justify-between">
              <span className="text-xs font-medium text-clay-300 uppercase tracking-wider">
                Request Log
              </span>
              <span className="text-xs text-clay-500 font-mono">
                {filteredJobs.length} / {jobs.length}
              </span>
            </div>
            <RequestList
              jobs={filteredJobs}
              selectedJobId={selectedJobId}
              onSelectJob={setSelectedJobId}
              autoScroll={streaming}
            />
          </Card>

          {/* Detail panel */}
          <div className="flex flex-col">
            {selectedJobId ? (
              <RequestDetail
                jobId={selectedJobId}
                onClose={() => setSelectedJobId(null)}
              />
            ) : (
              <Card className="flex-1 flex items-center justify-center">
                <CardContent className="text-center py-16">
                  <Zap className="h-10 w-10 text-clay-600 mx-auto mb-3" />
                  <p className="text-sm text-clay-400">
                    Select a request to view details
                  </p>
                  <p className="text-xs text-clay-500 mt-1">
                    Click any row in the request log
                  </p>
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

function StatCard({
  label,
  value,
  icon: Icon,
  accent,
}: {
  label: string;
  value: string;
  icon: React.ComponentType<{ className?: string }>;
  accent: string;
}) {
  return (
    <Card>
      <CardContent className="py-3">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-[10px] uppercase tracking-wider text-clay-400 mb-1">
              {label}
            </p>
            <p className="text-lg font-semibold font-mono text-clay-100 tabular-nums">
              {value}
            </p>
          </div>
          <Icon className={cn("h-5 w-5", accent)} />
        </div>
      </CardContent>
    </Card>
  );
}
