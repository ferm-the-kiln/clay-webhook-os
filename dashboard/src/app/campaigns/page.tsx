"use client";

import { Suspense, useState, useEffect, useCallback } from "react";
import { useSearchParams, useRouter } from "next/navigation";
import { Header } from "@/components/layout/header";
import { CampaignList } from "@/components/campaigns/campaign-list";
import { CampaignDetail } from "@/components/campaigns/campaign-detail";
import { CreateCampaignDialog } from "@/components/campaigns/create-campaign-dialog";
import { ReviewStatsBar } from "@/components/review/review-stats";
import { ReviewList } from "@/components/review/review-list";
import { ReviewDetail } from "@/components/review/review-detail";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import type { Campaign, CampaignStatus, ReviewItem, ReviewStats } from "@/lib/types";
import {
  fetchCampaigns,
  fetchCampaign,
  deleteCampaign,
  activateCampaign,
  pauseCampaign,
  runCampaignBatch,
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
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Plus, Loader2, RefreshCw } from "lucide-react";
import { toast } from "sonner";

type ReviewFilterTab = "all" | "pending" | "approved" | "rejected";

function CampaignsInner() {
  const searchParams = useSearchParams();
  const router = useRouter();
  const activeTab = searchParams.get("tab") === "review" ? "review" : "campaigns";

  const setActiveTab = (tab: string) => {
    const params = new URLSearchParams();
    if (tab === "review") params.set("tab", "review");
    router.replace(`/campaigns?${params.toString()}`);
  };

  // ─── Campaigns state ───
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [campaignsLoading, setCampaignsLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [viewing, setViewing] = useState<Campaign | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<Campaign | null>(null);
  const [deleting, setDeleting] = useState(false);

  // ─── Review state ───
  const [reviewItems, setReviewItems] = useState<ReviewItem[]>([]);
  const [reviewStats, setReviewStats] = useState<ReviewStats | null>(null);
  const [reviewTotal, setReviewTotal] = useState(0);
  const [reviewLoading, setReviewLoading] = useState(true);
  const [reviewTab, setReviewTab] = useState<ReviewFilterTab>("all");
  const [reviewCampaignFilter, setReviewCampaignFilter] = useState("all");
  const [selectedReviewItem, setSelectedReviewItem] = useState<ReviewItem | null>(null);

  // ─── Campaigns logic ───
  const loadCampaigns = useCallback(async () => {
    try {
      const filter = statusFilter === "all" ? undefined : statusFilter;
      const res = await fetchCampaigns(filter);
      setCampaigns(res.campaigns);
    } catch {
      toast.error("Failed to load campaigns");
    } finally {
      setCampaignsLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    loadCampaigns();
  }, [loadCampaigns]);

  const handleActivate = async (campaign: Campaign) => {
    try {
      await activateCampaign(campaign.id);
      toast.success(`"${campaign.name}" activated`);
      loadCampaigns();
    } catch (e) {
      toast.error("Failed to activate", {
        description: (e as Error).message,
      });
    }
  };

  const handlePause = async (campaign: Campaign) => {
    try {
      await pauseCampaign(campaign.id);
      toast.success(`"${campaign.name}" paused`);
      loadCampaigns();
    } catch (e) {
      toast.error("Failed to pause", {
        description: (e as Error).message,
      });
    }
  };

  const handleRunBatch = async (campaign: Campaign) => {
    try {
      const result = await runCampaignBatch(campaign.id);
      toast.success("Batch run complete", {
        description: `${result.auto_sent} auto-sent, ${result.queued_for_review} queued for review`,
      });
      loadCampaigns();
    } catch (e) {
      toast.error("Batch run failed", {
        description: (e as Error).message,
      });
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    setDeleting(true);
    try {
      await deleteCampaign(deleteConfirm.id);
      toast.success(`"${deleteConfirm.name}" deleted`);
      setDeleteConfirm(null);
      if (viewing?.id === deleteConfirm.id) {
        setViewing(null);
      }
      loadCampaigns();
    } catch (e) {
      toast.error("Failed to delete", {
        description: (e as Error).message,
      });
    } finally {
      setDeleting(false);
    }
  };

  const handleView = async (campaign: Campaign) => {
    try {
      const full = await fetchCampaign(campaign.id);
      setViewing(full);
    } catch {
      setViewing(campaign);
    }
  };

  const handleCreated = () => {
    loadCampaigns();
  };

  const countByStatus = (s: CampaignStatus) =>
    campaigns.filter((c) => c.status === s).length;
  const activeCampaigns = countByStatus("active");
  const draftCampaigns = countByStatus("draft");
  const pausedCampaigns = countByStatus("paused");

  // ─── Review logic ───
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

  const loadAllReview = useCallback(() => {
    loadReviewStats();
    loadReviewItems();
  }, [loadReviewStats, loadReviewItems]);

  useEffect(() => {
    if (activeTab === "review") {
      loadAllReview();
    }
  }, [activeTab, loadAllReview]);

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
    loadAllReview();
  };

  const getCampaignName = (id: string | null) => {
    if (!id) return null;
    const c = campaigns.find((c) => c.id === id);
    return c?.name || null;
  };

  return (
    <div className="flex-1 overflow-auto p-4 md:p-6 space-y-6 pb-20 md:pb-6">
      <Tabs value={activeTab} onValueChange={setActiveTab}>
        <TabsList className="bg-clay-900 border border-clay-800">
          <TabsTrigger
            value="campaigns"
            className="data-[state=active]:bg-kiln-teal/10 data-[state=active]:text-kiln-teal text-clay-400"
          >
            Campaigns
          </TabsTrigger>
          <TabsTrigger
            value="review"
            className="data-[state=active]:bg-kiln-teal/10 data-[state=active]:text-kiln-teal text-clay-400"
          >
            Review Queue
            {reviewStats && reviewStats.pending > 0 && (
              <span className="ml-1.5 inline-flex items-center justify-center h-5 min-w-[20px] px-1 rounded-full bg-kiln-mustard/20 text-kiln-mustard text-[10px] font-semibold">
                {reviewStats.pending}
              </span>
            )}
          </TabsTrigger>
        </TabsList>
      </Tabs>

      {/* ─── Campaigns Tab ─── */}
      {activeTab === "campaigns" && (
        <>
          {viewing ? (
            <ErrorBoundary>
              <CampaignDetail
                campaign={viewing}
                onBack={() => setViewing(null)}
                onRefresh={loadCampaigns}
              />
            </ErrorBoundary>
          ) : (
            <>
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div className="flex items-center gap-2 flex-wrap">
                  <h3 className="text-sm font-medium text-clay-300 uppercase tracking-wider">
                    Campaigns
                  </h3>
                  {campaigns.length > 0 && (
                    <div className="flex items-center gap-1.5">
                      {activeCampaigns > 0 && (
                        <Badge
                          variant="outline"
                          className="bg-kiln-teal/10 text-kiln-teal border-kiln-teal/30 text-xs"
                        >
                          {activeCampaigns} active
                        </Badge>
                      )}
                      {draftCampaigns > 0 && (
                        <Badge
                          variant="outline"
                          className="bg-clay-500/10 text-clay-500 border-clay-500/30 text-xs"
                        >
                          {draftCampaigns} draft
                        </Badge>
                      )}
                      {pausedCampaigns > 0 && (
                        <Badge
                          variant="outline"
                          className="bg-kiln-mustard/10 text-kiln-mustard border-kiln-mustard/30 text-xs"
                        >
                          {pausedCampaigns} paused
                        </Badge>
                      )}
                    </div>
                  )}
                </div>

                <div className="flex items-center gap-3">
                  <Select
                    value={statusFilter}
                    onValueChange={setStatusFilter}
                  >
                    <SelectTrigger className="w-36 border-clay-700 bg-clay-900 text-clay-200 h-9 text-sm">
                      <SelectValue placeholder="Filter..." />
                    </SelectTrigger>
                    <SelectContent className="border-clay-700 bg-clay-900">
                      <SelectItem value="all">All Statuses</SelectItem>
                      <SelectItem value="draft">Draft</SelectItem>
                      <SelectItem value="active">Active</SelectItem>
                      <SelectItem value="paused">Paused</SelectItem>
                      <SelectItem value="completed">Completed</SelectItem>
                    </SelectContent>
                  </Select>

                  <Button
                    onClick={() => setCreateOpen(true)}
                    className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
                  >
                    <Plus className="h-4 w-4 mr-1.5" />
                    New Campaign
                  </Button>
                </div>
              </div>

              {campaignsLoading ? (
                <div className="flex items-center justify-center py-20">
                  <Loader2 className="h-8 w-8 text-clay-500 animate-spin" />
                </div>
              ) : (
                <ErrorBoundary>
                  <CampaignList
                    campaigns={campaigns}
                    onView={handleView}
                    onActivate={handleActivate}
                    onPause={handlePause}
                    onRunBatch={handleRunBatch}
                    onDelete={(c) => setDeleteConfirm(c)}
                  />
                </ErrorBoundary>
              )}
            </>
          )}
        </>
      )}

      {/* ─── Review Tab ─── */}
      {activeTab === "review" && (
        <>
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
              onClick={loadAllReview}
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
        </>
      )}

      {/* ─── Dialogs ─── */}
      <CreateCampaignDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={handleCreated}
      />

      <Dialog
        open={deleteConfirm !== null}
        onOpenChange={(open) => !open && setDeleteConfirm(null)}
      >
        <DialogContent className="border-clay-800 bg-clay-950">
          <DialogHeader>
            <DialogTitle className="text-clay-100">
              Delete Campaign
            </DialogTitle>
            <DialogDescription className="text-clay-500">
              Are you sure you want to delete &quot;{deleteConfirm?.name}
              &quot;? All progress, audience data, and review items will be
              permanently removed.
            </DialogDescription>
          </DialogHeader>
          <div className="flex justify-end gap-2">
            <Button
              variant="outline"
              onClick={() => setDeleteConfirm(null)}
              className="border-clay-700 text-clay-300"
              disabled={deleting}
            >
              Cancel
            </Button>
            <Button
              onClick={handleDelete}
              disabled={deleting}
              className="bg-kiln-coral text-white hover:bg-kiln-coral/80"
            >
              {deleting && (
                <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              )}
              Delete
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}

export default function CampaignsPage() {
  return (
    <div className="flex flex-col h-full">
      <Header title="Campaigns" />
      <Suspense>
        <CampaignsInner />
      </Suspense>
    </div>
  );
}
