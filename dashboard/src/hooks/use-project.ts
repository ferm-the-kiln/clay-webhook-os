"use client";

import { useState, useEffect, useCallback } from "react";
import { toast } from "sonner";
import {
  fetchProjectDetail,
  updateProject,
  deleteProject,
  addProjectPhase,
  updateProjectPhase,
  deleteProjectPhase,
  toggleAction,
  deletePortalUpdate,
  toggleUpdatePin,
} from "@/lib/api";
import type { ProjectDetail, PortalProject, PortalUpdate, PortalMedia, PortalAction } from "@/lib/types";

export function useProject(slug: string, projectId: string) {
  const [project, setProject] = useState<PortalProject | null>(null);
  const [updates, setUpdates] = useState<PortalUpdate[]>([]);
  const [media, setMedia] = useState<PortalMedia[]>([]);
  const [actions, setActions] = useState<PortalAction[]>([]);
  const [stats, setStats] = useState<ProjectDetail["stats"] | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const detail = await fetchProjectDetail(slug, projectId);
      setProject(detail.project);
      setUpdates(detail.updates);
      setMedia(detail.media);
      setActions(detail.actions);
      setStats(detail.stats);
    } catch {
      toast.error("Failed to load project");
    } finally {
      setLoading(false);
    }
  }, [slug, projectId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleUpdateProject = useCallback(
    async (updates: Parameters<typeof updateProject>[2]) => {
      try {
        const updated = await updateProject(slug, projectId, updates);
        setProject(updated);
        toast.success("Project updated");
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Failed to update project");
      }
    },
    [slug, projectId],
  );

  const handleDeleteProject = useCallback(async () => {
    try {
      await deleteProject(slug, projectId);
      toast.success("Project deleted");
      return true;
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to delete project");
      return false;
    }
  }, [slug, projectId]);

  const handleAddPhase = useCallback(
    async (name: string) => {
      try {
        const order = project?.phases.length ?? 0;
        await addProjectPhase(slug, projectId, { name, order });
        load();
        toast.success(`Phase "${name}" added`);
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Failed to add phase");
      }
    },
    [slug, projectId, project, load],
  );

  const handleTogglePhase = useCallback(
    async (phaseId: string) => {
      if (!project) return;
      const phase = project.phases.find((p) => p.id === phaseId);
      if (!phase) return;
      const newStatus = phase.status === "completed" ? "pending" : "completed";
      try {
        await updateProjectPhase(slug, projectId, phaseId, { status: newStatus });
        load();
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Failed to update phase");
      }
    },
    [slug, projectId, project, load],
  );

  const handleDeletePhase = useCallback(
    async (phaseId: string) => {
      try {
        await deleteProjectPhase(slug, projectId, phaseId);
        load();
        toast.success("Phase removed");
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Failed to delete phase");
      }
    },
    [slug, projectId, load],
  );

  const handleTogglePin = useCallback(
    async (updateId: string) => {
      try {
        await toggleUpdatePin(slug, updateId);
        load();
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Failed to toggle pin");
      }
    },
    [slug, load],
  );

  const handleDeleteUpdate = useCallback(
    async (updateId: string) => {
      try {
        await deletePortalUpdate(slug, updateId);
        toast.success("Update deleted");
        load();
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Failed to delete update");
      }
    },
    [slug, load],
  );

  const handleToggleAction = useCallback(
    async (actionId: string) => {
      // Optimistic
      setActions((prev) =>
        prev.map((a) =>
          a.id === actionId
            ? { ...a, status: a.status === "done" ? ("open" as const) : ("done" as const) }
            : a,
        ),
      );
      try {
        await toggleAction(slug, actionId);
        load();
      } catch (e) {
        toast.error(e instanceof Error ? e.message : "Failed to toggle action");
        load();
      }
    },
    [slug, load],
  );

  return {
    project,
    updates,
    media,
    actions,
    stats,
    loading,
    reload: load,
    handleUpdateProject,
    handleDeleteProject,
    handleAddPhase,
    handleTogglePhase,
    handleDeletePhase,
    handleTogglePin,
    handleDeleteUpdate,
    handleToggleAction,
  };
}
