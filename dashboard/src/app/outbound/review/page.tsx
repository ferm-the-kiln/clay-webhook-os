"use client";

import { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/layout/header";
import { ReviewStatsBar } from "@/components/review/review-stats";
import { ReviewList } from "@/components/review/review-list";
import { ReviewDetail } from "@/components/review/review-detail";
import type { Campaign, ReviewItem, ReviewStats } from "@/lib/types";
import {
  fetchCampaigns,
  fetchReviewItems,
  fetchReviewStats,
  fetchReviewItem,
} from "@/lib/api";
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Button } from "@/components/ui/button";
import { RefreshCw } from "lucide-react";
import { toast } from "sonner";

type ReviewFilterTab = "all" | "pending" | "approved" | "rejected";

export default function ReviewQueuePage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [reviewItems, setReviewItems] = useState<ReviewItem[]>([]);
  const [reviewStats, setReviewStats] = useState<ReviewStats | null>(null);
  const [reviewTotal, setReviewTotal] = useState(0);
  const [reviewLoading, setReviewLoading] = useState(true);
  const [reviewTab, setReviewTab] = useState<ReviewFilterTab>("all");
  const [reviewCampaignFilter, setReviewCampaignFilter] = useState("all");
  const [selectedReviewItem, setSelectedReviewItem] = useState<ReviewItem | null>(null);

  // Load campaigns for the filter dropdown
  useEffect(() => {
    fetchCampaigns()
      .then((res) => setCampaigns(res.campaigns))
      .catch(() => {});
  }, []);

  const loadReviewStats = useCallback(async () => {
    try {
      const campaignId =
        reviewCampaignFilter !== "all" ? reviewCampaignFilter : undefined;
      const s = await fetchReviewStats(campaignId);
      setReviewStats(s);
    } catch {
      // Stats are non-critical
    }
  }, [reviewCampaignFilter]);

  const loadReviewItems = useCallback(async () => {
    setReviewLoading(true);
    try {
      const params: {
        status?: string;
        campaign_id?: string;
        limit?: number;
      } = { limit: 100 };
      if (reviewTab !== "all") params.status = reviewTab;
      if (reviewCampaignFilter !== "all") params.campaign_id = reviewCampaignFilter;
      const res = await fetchReviewItems(params);
      setReviewItems(res.items);
      setReviewTotal(res.total);
    } catch {
      toast.error("Failed to load review items");
    } finally {
      setReviewLoading(false);
    }
  }, [reviewTab, reviewCampaignFilter]);

  const loadAll = useCallback(() => {
    loadReviewStats();
    loadReviewItems();
  }, [loadReviewStats, loadReviewItems]);

  useEffect(() => {
    loadAll();
  }, [loadAll]);

  const handleSelectReview = async (item: ReviewItem) => {
    try {
      const latest = await fetchReviewItem(item.id);
      setSelectedReviewItem(latest);
    } catch {
      setSelectedReviewItem(item);
    }
  };

  const handleReviewUpdated = () => {
    setSelectedReviewItem(null);
    loadAll();
  };

  const getCampaignName = (id: string | null) => {
    if (!id) return null;
    const c = campaigns.find((c) => c.id === id);
    return c?.name || null;
  };

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Review Queue"
        breadcrumbs={[
          { label: "Outbound", href: "/outbound" },
          { label: "Review Queue" },
        ]}
      />
      <div className="flex-1 overflow-auto p-4 md:p-6 space-y-6 pb-20 md:pb-6">
        <ReviewStatsBar stats={reviewStats} />

        <div className="flex flex-wrap items-center gap-3">
          <Tabs
            value={reviewTab}
            onValueChange={(v) => setReviewTab(v as ReviewFilterTab)}
          >
            <TabsList className="bg-clay-900 border border-clay-800">
              <TabsTrigger
                value="all"
                className="data-[state=active]:bg-kiln-teal/10 data-[state=active]:text-kiln-teal text-clay-400"
              >
                All
                {reviewTotal > 0 && (
                  <span className="ml-1.5 text-xs text-clay-500">
                    {reviewTotal}
                  </span>
                )}
              </TabsTrigger>
              <TabsTrigger
                value="pending"
                className="data-[state=active]:bg-kiln-mustard/10 data-[state=active]:text-kiln-mustard text-clay-400"
              >
                Pending
                {reviewStats && reviewStats.pending > 0 && (
                  <span className="ml-1.5 inline-flex items-center justify-center h-5 min-w-[20px] px-1 rounded-full bg-kiln-mustard/20 text-kiln-mustard text-[10px] font-semibold">
                    {reviewStats.pending}
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

          {campaigns.length > 0 && (
            <Select value={reviewCampaignFilter} onValueChange={setReviewCampaignFilter}>
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
            disabled={reviewLoading}
            className="border-clay-700 text-clay-400 hover:text-clay-200 h-9"
          >
            <RefreshCw
              className={`h-3.5 w-3.5 mr-1.5 ${reviewLoading ? "animate-spin" : ""}`}
            />
            Refresh
          </Button>
        </div>

        <div className="grid grid-cols-1 xl:grid-cols-2 gap-6">
          <div className={selectedReviewItem ? "" : "xl:col-span-2"}>
            <ReviewList
              items={reviewItems}
              loading={reviewLoading}
              onSelect={handleSelectReview}
            />
          </div>

          {selectedReviewItem && (
            <div className="sticky top-0">
              <ReviewDetail
                item={selectedReviewItem}
                campaignName={getCampaignName(selectedReviewItem.campaign_id)}
                onClose={() => setSelectedReviewItem(null)}
                onUpdated={handleReviewUpdated}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
