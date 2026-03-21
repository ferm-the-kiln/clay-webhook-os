"use client";

import { useState, useEffect } from "react";
import { Users, Search, Plus, ArrowUpDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { fetchPortals } from "@/lib/api";
import { ClientCard } from "@/components/portal/client-card";
import { NewClientDialog } from "@/components/portal/new-client-dialog";
import type { PortalOverview } from "@/lib/types";

type SortKey = "name" | "activity" | "health";

function healthScore(p: PortalOverview): number {
  let score = 0;
  if (p.overdue_action_count > 0) score += 100 + p.overdue_action_count;
  if (p.days_since_last_update !== null && p.days_since_last_update >= 7) score += 50;
  if (p.last_viewed_at === null) score += 25;
  if (p.unacked_sop_count > 0) score += 10;
  return score;
}

export default function ClientsPage() {
  const [portals, setPortals] = useState<PortalOverview[]>([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [sortBy, setSortBy] = useState<SortKey>("health");
  const [newClientOpen, setNewClientOpen] = useState(false);

  useEffect(() => {
    fetchPortals()
      .then((res) => setPortals(res.portals))
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  const filtered = portals.filter((p) => {
    const matchesSearch =
      !search ||
      p.name.toLowerCase().includes(search.toLowerCase()) ||
      p.slug.toLowerCase().includes(search.toLowerCase());
    const matchesStatus = statusFilter === "all" || p.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  const sorted = [...filtered].sort((a, b) => {
    if (sortBy === "health") return healthScore(b) - healthScore(a);
    if (sortBy === "activity") return (b.last_activity ?? 0) - (a.last_activity ?? 0);
    return a.name.localeCompare(b.name);
  });

  const statuses = ["all", ...new Set(portals.map((p) => p.status))];

  const cycleSortBy = () => {
    const order: SortKey[] = ["health", "activity", "name"];
    const idx = order.indexOf(sortBy);
    setSortBy(order[(idx + 1) % order.length]);
  };

  return (
    <div className="max-w-6xl mx-auto space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-clay-100 flex items-center gap-3">
            <Users className="h-6 w-6 text-kiln-teal" />
            Clients
          </h1>
          <p className="text-sm text-clay-400 mt-1">
            Manage client portals — SOPs, updates, deliverables, and media
          </p>
        </div>
        <Button
          size="sm"
          onClick={() => setNewClientOpen(true)}
          className="bg-kiln-teal text-clay-900 hover:bg-kiln-teal/90 gap-1.5"
        >
          <Plus className="h-3.5 w-3.5" />
          New Client
        </Button>
      </div>

      {/* Filters */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="relative flex-1 max-w-sm">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-clay-500" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search clients..."
            className="w-full bg-clay-800 border border-clay-600 rounded-lg pl-9 pr-3 py-2 text-sm text-clay-100 placeholder:text-clay-500 focus:outline-none focus:border-kiln-teal"
          />
        </div>

        <div className="flex gap-1">
          {statuses.map((s) => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`text-xs px-3 py-1.5 rounded-lg transition-colors ${
                statusFilter === s
                  ? "bg-kiln-teal/15 text-kiln-teal border border-kiln-teal/30"
                  : "bg-clay-800 text-clay-300 border border-clay-600 hover:border-clay-500"
              }`}
            >
              {s === "all" ? "All" : s.charAt(0).toUpperCase() + s.slice(1)}
            </button>
          ))}
        </div>

        <button
          onClick={cycleSortBy}
          className="flex items-center gap-1.5 text-xs text-clay-400 hover:text-clay-200 bg-clay-800 border border-clay-600 rounded-lg px-3 py-1.5"
          title={`Sort by ${sortBy}`}
        >
          <ArrowUpDown className="h-3 w-3" />
          {sortBy === "health" ? "Urgency" : sortBy === "activity" ? "Recent" : "Name"}
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {[1, 2, 3].map((i) => (
            <div key={i} className="rounded-xl border border-clay-600 bg-clay-800 p-5 animate-pulse">
              <div className="h-5 bg-clay-700 rounded w-2/3 mb-3" />
              <div className="h-4 bg-clay-700 rounded w-1/2" />
            </div>
          ))}
        </div>
      ) : sorted.length === 0 ? (
        <div className="text-center py-16">
          <Users className="h-12 w-12 text-clay-600 mx-auto mb-3" />
          <p className="text-clay-400">
            {portals.length === 0
              ? "No clients yet. Add a client profile to get started."
              : "No clients match your filters."}
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {sorted.map((portal) => (
            <ClientCard key={portal.slug} portal={portal} />
          ))}
        </div>
      )}

      <NewClientDialog open={newClientOpen} onOpenChange={setNewClientOpen} />
    </div>
  );
}
