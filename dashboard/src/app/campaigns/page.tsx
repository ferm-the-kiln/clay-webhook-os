"use client";

import { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/layout/header";
import { CampaignList } from "@/components/campaigns/campaign-list";
import { CampaignDetail } from "@/components/campaigns/campaign-detail";
import { CreateCampaignDialog } from "@/components/campaigns/create-campaign-dialog";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import type { Campaign, CampaignStatus } from "@/lib/types";
import {
  fetchCampaigns,
  fetchCampaign,
  deleteCampaign,
  activateCampaign,
  pauseCampaign,
  runCampaignBatch,
} from "@/lib/api";
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
import { Plus, Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function CampaignsPage() {
  const [campaigns, setCampaigns] = useState<Campaign[]>([]);
  const [loading, setLoading] = useState(true);
  const [statusFilter, setStatusFilter] = useState<string>("all");
  const [createOpen, setCreateOpen] = useState(false);
  const [viewing, setViewing] = useState<Campaign | null>(null);
  const [deleteConfirm, setDeleteConfirm] = useState<Campaign | null>(null);
  const [deleting, setDeleting] = useState(false);

  const load = useCallback(async () => {
    try {
      const filter = statusFilter === "all" ? undefined : statusFilter;
      const res = await fetchCampaigns(filter);
      setCampaigns(res.campaigns);
    } catch {
      toast.error("Failed to load campaigns");
    } finally {
      setLoading(false);
    }
  }, [statusFilter]);

  useEffect(() => {
    load();
  }, [load]);

  const handleActivate = async (campaign: Campaign) => {
    try {
      await activateCampaign(campaign.id);
      toast.success(`"${campaign.name}" activated`);
      load();
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
      load();
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
      load();
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
      load();
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
    load();
  };

  // Count by status
  const countByStatus = (s: CampaignStatus) =>
    campaigns.filter((c) => c.status === s).length;
  const activeCampaigns = countByStatus("active");
  const draftCampaigns = countByStatus("draft");
  const pausedCampaigns = countByStatus("paused");

  return (
    <div className="flex flex-col h-full">
      <Header title="Campaigns" />
      <div className="flex-1 overflow-auto p-4 md:p-6 space-y-6 pb-20 md:pb-6">
        {viewing ? (
          <ErrorBoundary>
            <CampaignDetail
              campaign={viewing}
              onBack={() => setViewing(null)}
              onRefresh={load}
            />
          </ErrorBoundary>
        ) : (
          <>
            {/* Top bar: stats + filter + create */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
              <div className="flex items-center gap-2 flex-wrap">
                <h3 className="text-sm font-medium text-clay-300 uppercase tracking-wide">
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

            {/* Campaign list */}
            {loading ? (
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
      </div>

      {/* Create Campaign Dialog */}
      <CreateCampaignDialog
        open={createOpen}
        onOpenChange={setCreateOpen}
        onCreated={handleCreated}
      />

      {/* Delete Confirmation Dialog */}
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
