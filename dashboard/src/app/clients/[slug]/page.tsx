"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams } from "next/navigation";
import { toast } from "sonner";
import { Plus } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  fetchPortal,
  fetchSyncStatus,
  syncPortal,
  deleteSOP,
  toggleUpdatePin,
  deletePortalUpdate,
  toggleAction,
} from "@/lib/api";
import type { PortalDetail, PortalSyncStatus } from "@/lib/types";
import { PortalHeader } from "@/components/portal/portal-header";
import { SOPPills } from "@/components/portal/sop-pills";
import { AttentionStrip } from "@/components/portal/attention-strip";
import { SearchBar } from "@/components/portal/search-bar";
import { PostFeed } from "@/components/portal/post-feed";
import { TimelineSidebar } from "@/components/portal/timeline-sidebar";
import { UpdateComposer } from "@/components/portal/update-composer";
import { ShareDialog } from "@/components/portal/share-dialog";
import { ProjectList } from "@/components/portal/project-list";
import { usePortalFeed } from "@/hooks/use-portal-feed";

export default function ClientPortalPage() {
  const params = useParams();
  const slug = params.slug as string;

  const [portal, setPortal] = useState<PortalDetail | null>(null);
  const [syncStatus, setSyncStatus] = useState<PortalSyncStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);
  const [shareDialogOpen, setShareDialogOpen] = useState(false);
  const [composerOpen, setComposerOpen] = useState(false);

  const {
    searchQuery,
    setSearchQuery,
    highlightedPostId,
    highlightPost,
    filteredUpdates,
    postRefs,
  } = usePortalFeed(portal?.recent_updates ?? []);

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

  // ── Handlers ──

  const handleSync = async () => {
    setSyncing(true);
    try {
      const result = await syncPortal(slug);
      toast.success("Synced to Google Workspace");
      setSyncStatus({
        slug, synced: true, available: true,
        last_synced_at: result.synced_at, doc_id: result.doc_id, url: result.url,
      });
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Sync failed");
    } finally {
      setSyncing(false);
    }
  };

  const handleDeleteSOP = async (sopId: string) => {
    try { await deleteSOP(slug, sopId); toast.success("SOP deleted"); loadPortal(); }
    catch (e) { toast.error(e instanceof Error ? e.message : "Failed to delete SOP"); }
  };

  const handleTogglePin = async (updateId: string) => {
    try { await toggleUpdatePin(slug, updateId); loadPortal(); }
    catch (e) { toast.error(e instanceof Error ? e.message : "Failed to toggle pin"); }
  };

  const handleDeleteUpdate = async (updateId: string) => {
    try { await deletePortalUpdate(slug, updateId); toast.success("Update deleted"); loadPortal(); }
    catch (e) { toast.error(e instanceof Error ? e.message : "Failed to delete update"); }
  };

  const handleToggleAction = async (actionId: string) => {
    // Optimistic update
    if (portal) {
      setPortal({
        ...portal,
        actions: portal.actions.map((a) =>
          a.id === actionId
            ? { ...a, status: a.status === "done" ? "open" as const : "done" as const }
            : a
        ),
      });
    }
    try {
      await toggleAction(slug, actionId);
      loadPortal();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to toggle action");
      loadPortal(); // revert
    }
  };

  // Keyboard shortcut: N to open composer
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if (e.key === "n" && !e.metaKey && !e.ctrlKey && !e.altKey) {
        const tag = (e.target as HTMLElement).tagName;
        if (tag === "INPUT" || tag === "TEXTAREA" || (e.target as HTMLElement).isContentEditable) return;
        e.preventDefault();
        setComposerOpen(true);
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  // ── Loading / empty states ──

  if (loading) {
    return (
      <div className="max-w-6xl mx-auto space-y-4 px-4">
        <div className="h-12 bg-clay-700 rounded-lg animate-pulse" />
        <div className="h-10 bg-clay-700 rounded-lg animate-pulse w-1/2" />
        <div className="h-64 bg-clay-700 rounded-lg animate-pulse" />
      </div>
    );
  }

  if (!portal) {
    return (
      <div className="max-w-6xl mx-auto text-center py-16 px-4">
        <p className="text-clay-400">Client not found.</p>
      </div>
    );
  }

  const today = new Date().toISOString().split("T")[0];
  const clientActions = portal.actions.filter(
    (a) => a.owner === "client" && a.status !== "done"
  );
  const overdueActions = portal.actions.filter(
    (a) => a.status !== "done" && a.due_date && a.due_date < today
  );

  return (
    <div className="max-w-6xl mx-auto px-4 pb-12">
      <div className="space-y-5">
        {/* Header */}
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

        {/* Quick-access bar: SOP pills + create post */}
        <div className="flex items-center gap-3 flex-wrap">
          <SOPPills
            slug={slug}
            sops={portal.sops}
            sopAcks={portal.sop_acks || {}}
            onCreated={loadPortal}
            onUpdated={loadPortal}
            onDelete={handleDeleteSOP}
          />
          <div className="ml-auto shrink-0">
            <Button
              variant="outline"
              size="sm"
              onClick={() => setComposerOpen(!composerOpen)}
              className="border-clay-600 text-clay-200 hover:bg-clay-700 gap-1.5"
            >
              <Plus className="h-3.5 w-3.5" />
              Create Post
            </Button>
          </div>
        </div>

        {/* Projects */}
        <ProjectList
          slug={slug}
          projects={portal.projects ?? []}
          onProjectCreated={loadPortal}
        />

        {/* Attention strip */}
        <AttentionStrip
          clientActions={clientActions}
          overdueActions={overdueActions}
          onToggleAction={handleToggleAction}
        />

        {/* Two-column: feed + timeline sidebar */}
        <div className="grid grid-cols-1 lg:grid-cols-[1fr_340px] gap-6">
          {/* Left: Post feed */}
          <div className="space-y-4 min-w-0">
            <SearchBar
              value={searchQuery}
              onChange={setSearchQuery}
              resultCount={filteredUpdates.length}
              totalCount={portal.recent_updates.length}
            />

            {composerOpen && (
              <UpdateComposer
                slug={slug}
                clientName={portal.name}
                projects={portal.projects}
                onPosted={() => { loadPortal(); setComposerOpen(false); }}
              />
            )}

            <PostFeed
              slug={slug}
              updates={filteredUpdates}
              media={portal.media}
              searchQuery={searchQuery}
              highlightedPostId={highlightedPostId}
              postRefs={postRefs}
              onTogglePin={handleTogglePin}
              onDeleteUpdate={handleDeleteUpdate}
              clientName={portal.name}
              projects={portal.projects}
            />
          </div>

          {/* Right: Timeline sidebar */}
          <TimelineSidebar
            portal={portal}
            onSelectUpdate={highlightPost}
            activeUpdateId={highlightedPostId}
            slug={slug}
            onToggleAction={handleToggleAction}
            onPortalUpdated={loadPortal}
          />
        </div>
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
