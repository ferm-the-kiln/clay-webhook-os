"use client";

import { MessageSquare, Paperclip, CheckCircle2, AlertCircle } from "lucide-react";
import type { ProjectDetail, PortalProject, PortalMedia, PortalAction } from "@/lib/types";
import { ProjectPhaseTracker } from "./project-phase-tracker";
import { ProjectMediaSection } from "./project-media-section";
import { ProjectActionsSection } from "./project-actions-section";

interface ProjectSidebarProps {
  slug: string;
  projectId: string;
  project: PortalProject;
  stats: ProjectDetail["stats"] | null;
  media: PortalMedia[];
  actions: PortalAction[];
  onTogglePhase: (phaseId: string) => void;
  onAddPhase: (name: string) => void;
  onDeletePhase: (phaseId: string) => void;
  onDeleteMedia: (mediaId: string) => void;
  onToggleAction: (actionId: string) => void;
  onReload: () => void;
}

export function ProjectSidebar({
  slug,
  projectId,
  project,
  stats,
  media,
  actions,
  onTogglePhase,
  onAddPhase,
  onDeletePhase,
  onDeleteMedia,
  onToggleAction,
  onReload,
}: ProjectSidebarProps) {
  return (
    <div className="sticky top-4 space-y-5 max-h-[calc(100vh-6rem)] overflow-y-auto">
      {/* Quick stats */}
      {stats && (
        <div className="rounded-xl border border-clay-600 bg-clay-800 p-4">
          <h3 className="text-xs font-medium text-clay-300 uppercase tracking-wider mb-3">Stats</h3>
          <div className="grid grid-cols-2 gap-3">
            <div className="flex items-center gap-2">
              <MessageSquare className="h-3.5 w-3.5 text-clay-500" />
              <div>
                <p className="text-lg font-semibold text-clay-100">{stats.update_count}</p>
                <p className="text-[10px] text-clay-500">Posts</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Paperclip className="h-3.5 w-3.5 text-clay-500" />
              <div>
                <p className="text-lg font-semibold text-clay-100">{stats.media_count}</p>
                <p className="text-[10px] text-clay-500">Files</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <CheckCircle2 className="h-3.5 w-3.5 text-clay-500" />
              <div>
                <p className="text-lg font-semibold text-clay-100">{stats.action_count}</p>
                <p className="text-[10px] text-clay-500">Actions</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <AlertCircle className="h-3.5 w-3.5 text-clay-500" />
              <div>
                <p className="text-lg font-semibold text-clay-100">{stats.open_actions}</p>
                <p className="text-[10px] text-clay-500">Open</p>
              </div>
            </div>
          </div>

          {/* Completion bar */}
          {project.phases.length > 0 && (
            <div className="mt-3 pt-3 border-t border-clay-700">
              <div className="flex items-center justify-between mb-1.5">
                <span className="text-[10px] text-clay-500">Completion</span>
                <span className="text-[10px] text-clay-400 font-medium">
                  {Math.round(stats.completion_pct * 100)}%
                </span>
              </div>
              <div className="h-1.5 bg-clay-700 rounded-full overflow-hidden">
                <div
                  className="h-full bg-kiln-teal rounded-full transition-all"
                  style={{ width: `${stats.completion_pct * 100}%` }}
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Phases */}
      <div className="rounded-xl border border-clay-600 bg-clay-800 p-4">
        <ProjectPhaseTracker
          phases={project.phases}
          onTogglePhase={onTogglePhase}
          onAddPhase={onAddPhase}
          onDeletePhase={onDeletePhase}
        />
      </div>

      {/* Media */}
      {media.length > 0 && (
        <ProjectMediaSection
          slug={slug}
          media={media}
          onDelete={onDeleteMedia}
        />
      )}

      {/* Actions */}
      <ProjectActionsSection
        slug={slug}
        projectId={projectId}
        actions={actions}
        onToggle={onToggleAction}
        onReload={onReload}
      />
    </div>
  );
}
