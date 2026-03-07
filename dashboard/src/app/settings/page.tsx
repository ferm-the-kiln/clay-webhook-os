"use client";

import { Suspense, useState, useEffect, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Header } from "@/components/layout/header";
import { ContextTab } from "@/components/settings/context-tab";
import { DestinationForm } from "@/components/destinations/destination-form";
import { DestinationList } from "@/components/destinations/destination-list";
import { AnalyticsSummary } from "@/components/analytics/analytics-summary";
import { SkillPerformanceTable } from "@/components/analytics/skill-performance-table";
import { ApprovalChart } from "@/components/analytics/approval-chart";
import { ClientBreakdown } from "@/components/analytics/client-breakdown";
import type { Destination, DestinationType, FeedbackSummary } from "@/lib/types";
import {
  fetchDestinations,
  createDestination,
  updateDestination,
  deleteDestination,
  testDestination,
  fetchFeedbackAnalytics,
  fetchSkills,
} from "@/lib/api";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Plus, RefreshCw } from "lucide-react";
import { toast } from "sonner";

const TIME_RANGES = [
  { label: "7 days", value: "7" },
  { label: "30 days", value: "30" },
  { label: "90 days", value: "90" },
  { label: "All time", value: "all" },
];

type SettingsTab = "context" | "destinations" | "analytics";

function SettingsInner() {
  const searchParams = useSearchParams();
  const router = useRouter();

  const rawTab = searchParams.get("tab");
  const activeTab: SettingsTab =
    rawTab === "analytics" ? "analytics" :
    rawTab === "context" ? "context" :
    "destinations";

  const setActiveTab = (tab: string) => {
    const params = new URLSearchParams();
    if (tab !== "destinations") params.set("tab", tab);
    router.replace(`/settings?${params.toString()}`);
  };

  // ─── Destinations state ───
  const [destinations, setDestinations] = useState<Destination[]>([]);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editing, setEditing] = useState<Destination | null>(null);
  const [saving, setSaving] = useState(false);
  const [testingId, setTestingId] = useState<string | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<Destination | null>(null);

  // ─── Analytics state ───
  const [analyticsData, setAnalyticsData] = useState<FeedbackSummary | null>(null);
  const [skills, setSkills] = useState<string[]>([]);
  const [skillFilter, setSkillFilter] = useState("all");
  const [timeRange, setTimeRange] = useState("all");
  const [analyticsLoading, setAnalyticsLoading] = useState(true);

  // ─── Destinations logic ───
  const loadDestinations = useCallback(() => {
    fetchDestinations()
      .then((res) => setDestinations(res.destinations))
      .catch(() => toast.error("Failed to load destinations"));
  }, []);

  useEffect(() => {
    loadDestinations();
  }, [loadDestinations]);

  const handleCreate = async (data: {
    name: string;
    type: DestinationType;
    url: string;
    auth_header_name: string;
    auth_header_value: string;
    client_slug: string | null;
  }) => {
    setSaving(true);
    try {
      await createDestination(data);
      toast.success("Destination created");
      setDialogOpen(false);
      loadDestinations();
    } catch (e) {
      toast.error("Failed to create destination", {
        description: (e as Error).message,
      });
    } finally {
      setSaving(false);
    }
  };

  const handleUpdate = async (data: {
    name: string;
    type: DestinationType;
    url: string;
    auth_header_name: string;
    auth_header_value: string;
    client_slug: string | null;
  }) => {
    if (!editing) return;
    setSaving(true);
    try {
      await updateDestination(editing.id, data);
      toast.success("Destination updated");
      setEditing(null);
      setDialogOpen(false);
      loadDestinations();
    } catch (e) {
      toast.error("Failed to update destination", {
        description: (e as Error).message,
      });
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    try {
      await deleteDestination(deleteConfirm.id);
      toast.success("Destination deleted");
      setDeleteConfirm(null);
      loadDestinations();
    } catch (e) {
      toast.error("Failed to delete destination", {
        description: (e as Error).message,
      });
    }
  };

  const handleTest = async (dest: Destination) => {
    setTestingId(dest.id);
    try {
      const result = await testDestination(dest.id);
      if (result.ok) {
        toast.success("Connection successful", {
          description: `${dest.name} responded with status ${result.status_code}`,
        });
      } else {
        toast.error("Connection failed", {
          description: result.error || `Status ${result.status_code}`,
        });
      }
    } catch (e) {
      toast.error("Test failed", { description: (e as Error).message });
    } finally {
      setTestingId(null);
    }
  };

  // ─── Analytics logic ───
  const loadAnalytics = useCallback(async () => {
    setAnalyticsLoading(true);
    try {
      const params: { skill?: string; days?: number } = {};
      if (skillFilter !== "all") params.skill = skillFilter;
      if (timeRange !== "all") params.days = parseInt(timeRange);
      const summary = await fetchFeedbackAnalytics(params);
      setAnalyticsData(summary);
    } catch {
      toast.error("Failed to load analytics");
    } finally {
      setAnalyticsLoading(false);
    }
  }, [skillFilter, timeRange]);

  useEffect(() => {
    fetchSkills()
      .then((res) => setSkills(res.skills))
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (activeTab === "analytics") {
      loadAnalytics();
    }
  }, [activeTab, loadAnalytics]);

  return (
    <div className="flex-1 overflow-auto p-4 md:p-6 space-y-6 pb-20 md:pb-6">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-clay-900 border border-clay-800">
          <TabsTrigger
            value="context"
            className="data-[state=active]:bg-kiln-teal/10 data-[state=active]:text-kiln-teal text-clay-400"
          >
            Context
          </TabsTrigger>
          <TabsTrigger
            value="destinations"
            className="data-[state=active]:bg-kiln-teal/10 data-[state=active]:text-kiln-teal text-clay-400"
          >
            Destinations
          </TabsTrigger>
          <TabsTrigger
            value="analytics"
            className="data-[state=active]:bg-kiln-teal/10 data-[state=active]:text-kiln-teal text-clay-400"
          >
            Analytics
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {/* ─── Context Tab ─── */}
      {activeTab === "context" && <ContextTab />}

      {/* ─── Destinations Tab ─── */}
      {activeTab === "destinations" && (
        <>
          <div className="flex items-center justify-between">
            <div>
              <h3 className="text-lg font-semibold text-clay-100">Destinations</h3>
              <p className="text-sm text-clay-500">
                Push batch results to Clay tables or webhook endpoints.
              </p>
            </div>
            <Button
              onClick={() => {
                setEditing(null);
                setDialogOpen(true);
              }}
              className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
            >
              <Plus className="h-4 w-4 mr-2" />
              Add Destination
            </Button>
          </div>

          <DestinationList
            destinations={destinations}
            onEdit={(dest) => {
              setEditing(dest);
              setDialogOpen(true);
            }}
            onDelete={(dest) => setDeleteConfirm(dest)}
            onTest={handleTest}
            testingId={testingId}
          />

          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogContent className="border-clay-800 bg-clay-950">
              <DialogHeader>
                <DialogTitle className="text-clay-100">
                  {editing ? "Edit Destination" : "New Destination"}
                </DialogTitle>
                <DialogDescription className="text-clay-500">
                  {editing
                    ? "Update the destination configuration."
                    : "Configure where to push batch results."}
                </DialogDescription>
              </DialogHeader>
              <DestinationForm
                initial={editing}
                onSubmit={editing ? handleUpdate : handleCreate}
                loading={saving}
              />
            </DialogContent>
          </Dialog>

          <Dialog
            open={deleteConfirm !== null}
            onOpenChange={(open) => !open && setDeleteConfirm(null)}
          >
            <DialogContent className="border-clay-800 bg-clay-950">
              <DialogHeader>
                <DialogTitle className="text-clay-100">Delete Destination</DialogTitle>
                <DialogDescription className="text-clay-500">
                  Are you sure you want to delete &quot;{deleteConfirm?.name}&quot;? This
                  action cannot be undone.
                </DialogDescription>
              </DialogHeader>
              <div className="flex justify-end gap-2">
                <Button
                  variant="outline"
                  onClick={() => setDeleteConfirm(null)}
                  className="border-clay-700 text-clay-300"
                >
                  Cancel
                </Button>
                <Button
                  onClick={handleDelete}
                  className="bg-kiln-coral text-white hover:bg-kiln-coral/80"
                >
                  Delete
                </Button>
              </div>
            </DialogContent>
          </Dialog>
        </>
      )}

      {/* ─── Analytics Tab ─── */}
      {activeTab === "analytics" && (
        <>
          <div className="flex flex-wrap items-center gap-3">
            <Select value={skillFilter} onValueChange={setSkillFilter}>
              <SelectTrigger className="w-44 border-clay-700 bg-clay-900 text-clay-200 h-9 text-sm">
                <SelectValue placeholder="All skills" />
              </SelectTrigger>
              <SelectContent className="border-clay-700 bg-clay-900">
                <SelectItem value="all">All skills</SelectItem>
                {skills.map((s) => (
                  <SelectItem key={s} value={s}>
                    {s}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Select value={timeRange} onValueChange={setTimeRange}>
              <SelectTrigger className="w-36 border-clay-700 bg-clay-900 text-clay-200 h-9 text-sm">
                <SelectValue />
              </SelectTrigger>
              <SelectContent className="border-clay-700 bg-clay-900">
                {TIME_RANGES.map((r) => (
                  <SelectItem key={r.value} value={r.value}>
                    {r.label}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>

            <Button
              variant="outline"
              size="sm"
              onClick={loadAnalytics}
              disabled={analyticsLoading}
              className="border-clay-700 text-clay-400 hover:text-clay-200 h-9"
            >
              <RefreshCw className={`h-3.5 w-3.5 mr-1.5 ${analyticsLoading ? "animate-spin" : ""}`} />
              Refresh
            </Button>
          </div>

          <AnalyticsSummary data={analyticsData} />

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            <ApprovalChart skills={analyticsData?.by_skill || []} />
            <ClientBreakdown byClient={analyticsData?.by_client || {}} />
          </div>

          <div>
            <h3 className="text-sm font-medium text-clay-300 mb-3">
              Skill Performance
            </h3>
            <SkillPerformanceTable skills={analyticsData?.by_skill || []} />
          </div>
        </>
      )}
    </div>
  );
}

export default function SettingsPage() {
  return (
    <div className="flex flex-col h-full">
      <Header title="Settings" />
      <Suspense>
        <SettingsInner />
      </Suspense>
    </div>
  );
}
