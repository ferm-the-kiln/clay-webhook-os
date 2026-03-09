"use client";

import { useState, useEffect, useCallback } from "react";
import { Header } from "@/components/layout/header";
import { PlayGallery } from "@/components/plays/play-gallery";
import { PlayDetail } from "@/components/plays/play-detail";
import { PlayClayConfig } from "@/components/plays/play-clay-config";
import { PlayForkDialog } from "@/components/plays/play-fork-dialog";
import { PlayForm } from "@/components/plays/play-form";
import { ErrorBoundary } from "@/components/ui/error-boundary";
import type {
  PlayDefinition,
  ClientSummary,
  PipelineDefinition,
} from "@/lib/types";
import {
  fetchPlays,
  fetchPlay,
  deletePlay,
  fetchClients,
  fetchPipelines,
} from "@/lib/api";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Loader2 } from "lucide-react";
import { toast } from "sonner";

export default function PlaysPage() {
  const [plays, setPlays] = useState<PlayDefinition[]>([]);
  const [loading, setLoading] = useState(true);
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [pipelines, setPipelines] = useState<PipelineDefinition[]>([]);

  const [viewing, setViewing] = useState<PlayDefinition | null>(null);
  const [configPlay, setConfigPlay] = useState<PlayDefinition | null>(null);
  const [forkPlay, setForkPlay] = useState<PlayDefinition | null>(null);
  const [createOpen, setCreateOpen] = useState(false);
  const [deleteConfirm, setDeleteConfirm] = useState<PlayDefinition | null>(null);
  const [deleting, setDeleting] = useState(false);

  const loadPlays = useCallback(async () => {
    try {
      const res = await fetchPlays();
      setPlays(res.plays);
    } catch {
      toast.error("Failed to load plays");
    } finally {
      setLoading(false);
    }
  }, []);

  const loadMeta = useCallback(async () => {
    try {
      const [clientsRes, pipelinesRes] = await Promise.all([
        fetchClients(),
        fetchPipelines(),
      ]);
      setClients(clientsRes.clients);
      setPipelines(pipelinesRes.pipelines);
    } catch {
      // Non-critical
    }
  }, []);

  useEffect(() => {
    loadPlays();
    loadMeta();
  }, [loadPlays, loadMeta]);

  const handleView = async (play: PlayDefinition) => {
    try {
      const full = await fetchPlay(play.name);
      setViewing(full);
    } catch {
      setViewing(play);
    }
  };

  const handleDelete = async () => {
    if (!deleteConfirm) return;
    setDeleting(true);
    try {
      await deletePlay(deleteConfirm.name);
      toast.success(`"${deleteConfirm.display_name}" deleted`);
      setDeleteConfirm(null);
      if (viewing?.name === deleteConfirm.name) setViewing(null);
      loadPlays();
    } catch (e) {
      toast.error("Failed to delete", { description: (e as Error).message });
    } finally {
      setDeleting(false);
    }
  };

  const handleForked = () => {
    loadPlays();
  };

  const handleCreated = () => {
    loadPlays();
  };

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Plays"
        breadcrumbs={[
          { label: "Analyze", href: "/analyze" },
          { label: "Plays" },
        ]}
      />
      <div className="flex-1 overflow-auto p-4 md:p-6 space-y-6 pb-20 md:pb-6">
        {viewing ? (
          <ErrorBoundary>
            <PlayDetail
              play={viewing}
              onBack={() => setViewing(null)}
              onClayConfig={() => setConfigPlay(viewing)}
              onFork={() => setForkPlay(viewing)}
            />
          </ErrorBoundary>
        ) : (
          <ErrorBoundary>
            <PlayGallery
              plays={plays}
              loading={loading}
              onView={handleView}
              onFork={(p) => setForkPlay(p)}
              onDelete={(p) => setDeleteConfirm(p)}
              onNew={() => setCreateOpen(true)}
            />
          </ErrorBoundary>
        )}

        {configPlay && (
          <PlayClayConfig
            play={configPlay}
            clients={clients}
            open={configPlay !== null}
            onOpenChange={(open) => !open && setConfigPlay(null)}
          />
        )}

        <PlayForkDialog
          play={forkPlay}
          clients={clients}
          open={forkPlay !== null}
          onOpenChange={(open) => !open && setForkPlay(null)}
          onForked={handleForked}
        />

        <PlayForm
          pipelines={pipelines}
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
              <DialogTitle className="text-clay-100">Delete Play</DialogTitle>
              <DialogDescription className="text-clay-500">
                Are you sure you want to delete &quot;{deleteConfirm?.display_name}&quot;?
                This cannot be undone.
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
    </div>
  );
}
