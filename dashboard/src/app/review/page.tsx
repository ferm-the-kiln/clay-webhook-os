"use client";

import { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/layout/header";
import { ReviewStatsBar } from "@/components/review/review-stats";
import { ReviewList } from "@/components/review/review-list";
import { ReviewDetail } from "@/components/review/review-detail";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import type { ReviewItem, ReviewStats, Campaign } from "@/lib/types";
import {
  fetchReviewItems,
  fetchReviewStats,
  fetchReviewItem,
  fetchCampaigns,
} from "@/lib/api";
import { RefreshCw } from "lucide-react";
import { toast } from "sonner";

type FilterTab = "all" | "pending" | "approved" | "rejected";

export default function ReviewPage() {
  const [items, setItems] = useState<ReviewItem[]>([]);
  const [stats, setStats] = useState<ReviewStats | null>(null);
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);

  // Filters
  const [tab, setTab] = useState<FilterTab>("all");
  const [campaignFilter, setCampaignFilter] = useState("all");

  // Detail panel
  const [selectedItem, setSelectedItem] = useState<ReviewItem | null>(null);

  const loadStats = useCallback(async () => {
    try {
      const campaignId =
        campaignFilter !== "all" ? campaignFilter : undefined;
      const s = await fetchReviewStats(campaignId);
      setStats(s);
    } catch {
      // Stats are non-critical
    }
  }, [campaignFilter]);

  const loadItems = useCallback(async () => {
    setLoading(true);
    try {
      const params: {
        status?: string;
        campaign_id?: string;
        limit?: number;
      } = { limit: 100 };
      if (tab !== "all") params.status = tab;
      if (campaignFilter !== "all") params.campaign_id = campaignFilter;
      const res = await fetchReviewItems(params);
      setItems(res.items);
      setTotal(res.total);
    } catch {
      toast.error("Failed to load review items");
    } finally {
      setLoading(false);
    }
  }, [tab, campaignFilter]);

  const loadCampaigns = useCallback(async () => {
    try {
      const res = await fetchCampaigns();
      setCampaigns(res.campaigns);
    } catch {
      // Campaigns are optional
    }
  }, []);

  const loadAll = useCallback(() => {
    loadStats();
    loadItems();
  }, [loadStats, loadItems]);

  useEffect(() => {
    loadCampaigns();
  }, [loadCampaigns]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const handleSelect = async (item: ReviewItem) => {
    try {
      // Fetch the latest version
      const latest = await fetchReviewItem(item.id);
      setSelectedItem(latest);
    } catch {
      // Fall back to the list version
      setSelectedItem(item);
    }
  };

  const handleUpdated = () => {
    setSelectedItem(null);
    loadAll();
  };

  const getCampaignName = (id: string | null) => {
    if (!id) return null;
    const c = campaigns.find((c) => c.id === id);
    return c?.name || null;
  };

  return (
    <div className="flex flex-col h-full">
      <Header title="Review Queue" />
      <div className="flex-1 overflow-auto p-4 md:p-6 space-y-6 pb-20 md:pb-6">
        {/* Stats bar */}
        <ReviewStatsBar stats={stats} />

        {/* Filters row */}
        <div className="flex flex-wrap items-center gap-3">
          <Tabs
            value={tab}
            onValueChange={(v) => setTab(v as FilterTab)}
          >
            <TabsList className="bg-clay-900 border border-clay-800">
              <TabsTrigger
                value="all"
                className="data-[state=active]:bg-kiln-teal/10 data-[state=active]:text-kiln-teal text-clay-400"
              >
                All
                {total > 0 && (
                  <span className="ml-1.5 text-xs text-clay-500">
                    {total}
                  </span>
                )}
              </TabsTrigger>
              <TabsTrigger
                value="pending"
                className="data-[state=active]:bg-kiln-mustard/10 data-[state=active]:text-kiln-mustard text-clay-400"
              >
                Pending
                {stats && stats.pending > 0 && (
                  <span className="ml-1.5 inline-flex items-center justify-center h-5 min-w-[20px] px-1 rounded-full bg-kiln-mustard/20 text-kiln-mustard text-[10px] font-semibold">
                    {stats.pending}
                  </span>
                )}
              </TabsTrigger>
              <TabsTrigger
                value="approved"
                className="data-[state=active]:bg-kiln-teal/10 data-[state=active]:text-kiln-teal text-clay-400"
              >
                Approved
              </TabsTrigger>
              <TabsTrigger
                value="rejected"
                className="data-[state=active]:bg-kiln-coral/10 data-[state=active]:text-kiln-coral text-clay-400"
              >
                Rejected
              </TabsTrigger>
            </TabsList>
          </Tabs>

          {/* Campaign filter */}
          {campaigns.length > 0 && (
            <Select value={campaignFilter} onValueChange={setCampaignFilter}>
              <SelectTrigger className="w-48 border-clay-700 bg-clay-900 text-clay-200 h-9 text-sm">
                <SelectValue placeholder="All campaigns" />
              </SelectTrigger>
              <SelectContent className="border-clay-700 bg-clay-900">
                <SelectItem value="all">All campaigns</SelectItem>
                {campaigns.map((c) => (
                  <SelectItem key={c.id} value={c.id}>
                    {c.name}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          )}

          <Button
            variant="outline"
            size="sm"
            onClick={loadAll}
            disabled={loading}
            className="border-clay-700 text-clay-400 hover:text-clay-200 h-9"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 mr-1.5 ${loading ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>
        </div>

        {/* Main content */}
        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          {/* Item list */}
          <div className={selectedItem ? "" : "xl:col-span-2"}>
            <ReviewList
              items={items}
              loading={loading}
              onSelect={handleSelect}
            />
          </div>

          {/* Detail panel */}
          {selectedItem && (
            <div className="sticky top-0">
              <ReviewDetail
                item={selectedItem}
                campaignName={getCampaignName(selectedItem.campaign_id)}
                onClose={() => setSelectedItem(null)}
                onUpdated={handleUpdated}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
