"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import {
  fetchPortal,
  fetchSyncStatus,
  syncPortal,
  deleteSOP,
  toggleUpdatePin,
  deletePortalUpdate,
  deletePortalMedia,
  toggleAction,
  deleteAction,
} from "@/lib/api";
import type { PortalDetail, PortalSyncStatus } from "@/lib/types";
import { PortalHeader } from "@/components/portal/portal-header";
import { PortalTabs, type PortalTab } from "@/components/portal/portal-tabs";
import { OverviewTab } from "@/components/portal/overview-tab";
import { SOPList } from "@/components/portal/sop-list";
import { UpdateFeed } from "@/components/portal/update-feed";
import { UpdateComposer } from "@/components/portal/update-composer";
import { MediaGrid } from "@/components/portal/media-grid";
import { MediaUpload } from "@/components/portal/media-upload";
import { ActionList } from "@/components/portal/action-list";
import { ShareDialog } from "@/components/portal/share-dialog";

export default function ClientPortalPage() {
  const params = useParams();
  const slug = params.slug as string;

  const [portal, setPortal] = useState<PortalDetail | null>(null);
  const [syncStatus, setSyncStatus] = useState<PortalSyncStatus | null>(null);
  const [activeTab, setActiveTab] = useState<PortalTab>("overview");
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);

  const loadPortal = useCallback(async () => {
    try {
      const [p, ss] = await Promise.all([
        fetchPortal(slug),
        fetchSyncStatus(slug).catch(() => null),
      ]);
      setPortal(p);
      setSyncStatus(ss);
    } catch {
      toast.error("Failed to load portal");
    } finally {
      setLoading(false);
    }
  }, [slug]);

  useEffect(() => {
    loadPortal();
  }, [loadPortal]);

  const handleSync = async () => {
    setSyncing(true);
    try {
      const result = await syncPortal(slug);
      toast.success("Synced to Google Workspace");
      setSyncStatus({
        slug,
        synced: true,
        available: true,
        last_synced_at: result.synced_at,
        doc_id: result.doc_id,
        url: result.url,
      });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const handleDeleteSOP = async (sopId: string) => {
    try {
      await deleteSOP(slug, sopId);
      toast.success("SOP deleted");
      loadPortal();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to delete SOP");
    }
  };

  const handleTogglePin = async (updateId: string) => {
    try {
      await toggleUpdatePin(slug, updateId);
      loadPortal();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to toggle pin");
    }
  };

  const handleDeleteUpdate = async (updateId: string) => {
    try {
      await deletePortalUpdate(slug, updateId);
      toast.success("Update deleted");
      loadPortal();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to delete update");
    }
  };

  const handleDeleteMedia = async (mediaId: string) => {
    try {
      await deletePortalMedia(slug, mediaId);
      toast.success("Media deleted");
      loadPortal();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to delete media");
    }
  };

  const handleToggleAction = async (actionId: string) => {
    try {
      await toggleAction(slug, actionId);
      loadPortal();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to toggle action");
    }
  };

  const handleDeleteAction = async (actionId: string) => {
    try {
      await deleteAction(slug, actionId);
      toast.success("Action deleted");
      loadPortal();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to delete action");
    }
  };

  if (loading) {
    return (
      <div className="max-w-4xl mx-auto space-y-6">
        <div className="h-12 bg-clay-700 rounded-lg animate-pulse" />
        <div className="h-10 bg-clay-700 rounded-lg animate-pulse w-1/2" />
        <div className="h-64 bg-clay-700 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (!portal) {
    return (
      <div className="max-w-4xl mx-auto text-center py-16">
        <p className="text-clay-400">Client not found.</p>
      </div>
    );
  }

  return (
    <div className="max-w-4xl mx-auto space-y-6">
      <PortalHeader
        name={portal.name}
        status={portal.meta.status}
        syncAvailable={syncStatus?.available ?? false}
        syncing={syncing}
        lastSyncedAt={syncStatus?.last_synced_at ?? null}
        shareToken={portal.meta.share_token}
        onSync={handleSync}
        onShareClick={() => setShareDialogOpen(true)}
      />

      <PortalTabs
        active={activeTab}
        onChange={setActiveTab}
        counts={{
          sops: portal.sops.length,
          updates: portal.recent_updates.length,
          media: portal.media.length,
          actions: portal.actions.filter((a) => a.status !== "done").length,
        }}
      />

      <div className="min-h-[400px]">
        {activeTab === "overview" && (
          <OverviewTab
            portal={portal}
            slug={slug}
            onPortalUpdated={loadPortal}
            onTabChange={setActiveTab}
            onToggleAction={handleToggleAction}
          />
        )}

        {activeTab === "sops" && (
          <SOPList
            slug={slug}
            sops={portal.sops}
            onCreated={loadPortal}
            onUpdated={loadPortal}
            onDelete={handleDeleteSOP}
          />
        )}

        {activeTab === "updates" && (
          <div className="space-y-4">
            <UpdateComposer slug={slug} onPosted={loadPortal} />
            <UpdateFeed
              updates={portal.recent_updates}
              onTogglePin={handleTogglePin}
              onDelete={handleDeleteUpdate}
            />
          </div>
        )}

        {activeTab === "media" && (
          <div className="space-y-4">
            <MediaUpload slug={slug} onUploaded={loadPortal} />
            <MediaGrid media={portal.media} onDelete={handleDeleteMedia} />
          </div>
        )}

        {activeTab === "actions" && (
          <ActionList
            slug={slug}
            actions={portal.actions}
            onCreated={loadPortal}
            onUpdated={loadPortal}
            onToggle={handleToggleAction}
            onDelete={handleDeleteAction}
          />
        )}
      </div>

      <ShareDialog
        slug={slug}
        shareToken={portal.meta.share_token}
        open={shareDialogOpen}
        onOpenChange={setShareDialogOpen}
        onChanged={loadPortal}
      />
    </div>
  );
}
