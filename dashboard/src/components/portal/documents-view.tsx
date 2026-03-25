"use client";

import { useState } from "react";
import {
  FolderOpen,
  ExternalLink,
  Package,
  FileText,
  ChevronDown,
  ChevronUp,
  CheckCircle,
  Clock,
  RotateCcw,
  Paperclip,
} from "lucide-react";
import { cn, formatRelativeTime } from "@/lib/utils";
import type { PortalUpdate, PortalMedia, ProjectSummary } from "@/lib/types";
import { MediaGrid } from "./media-grid";
import { MediaUpload } from "./media-upload";
import { MarkdownContent } from "./markdown-content";
import { ApprovalBanner } from "./approval-banner";

const APPROVAL_BADGES: Record<string, { label: string; color: string; bg: string }> = {
  pending_review: { label: "Pending Review", color: "text-amber-400", bg: "bg-amber-500/10" },
  approved: { label: "Approved", color: "text-emerald-400", bg: "bg-emerald-500/10" },
  revision_requested: { label: "Revision Requested", color: "text-orange-400", bg: "bg-orange-500/10" },
  resubmitted: { label: "Resubmitted", color: "text-purple-400", bg: "bg-purple-500/10" },
};

interface DocumentsViewProps {
  slug: string;
  gwsFolderId: string | null;
  projects: ProjectSummary[];
  media: PortalMedia[];
  updates: PortalUpdate[];
  onMediaDeleted: (mediaId: string) => void;
  onMediaUploaded: () => void;
  onUpdated: () => void;
  clientName?: string;
}

export function DocumentsView({
  slug,
  gwsFolderId,
  projects,
  media,
  updates,
  onMediaDeleted,
  onMediaUploaded,
  onUpdated,
  clientName,
}: DocumentsViewProps) {
  const [expandedDeliverable, setExpandedDeliverable] = useState<string | null>(null);
  const [showUpload, setShowUpload] = useState(false);

  const deliverables = updates
    .filter((u) => u.type === "deliverable")
    .sort((a, b) => b.created_at - a.created_at);

  const projectsWithDrive = projects.filter((p) => p.drive_folder_url);

  // Group media by project
  const projectMediaMap = new Map<string | null, PortalMedia[]>();
  for (const m of media) {
    const key = m.project_id || null;
    if (!projectMediaMap.has(key)) projectMediaMap.set(key, []);
    projectMediaMap.get(key)!.push(m);
  }

  const projectLookup = new Map(projects.map((p) => [p.id, p]));

  return (
    <div className="space-y-6">
      {/* Section A: Quick Access */}
      <div>
        <h3 className="text-xs font-semibold text-clay-300 uppercase tracking-wider mb-3">
          Quick Access
        </h3>
        <div className="flex flex-wrap gap-3">
          {/* Client Drive Folder */}
          {gwsFolderId ? (
            <a
              href={`https://drive.google.com/drive/folders/${gwsFolderId}`}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 rounded-lg border border-clay-700 bg-clay-850 px-4 py-3 hover:border-clay-500 hover:bg-clay-800 transition-colors retro-raised group"
            >
              <div className="h-9 w-9 rounded-lg bg-blue-500/10 flex items-center justify-center shrink-0">
                <FolderOpen className="h-5 w-5 text-blue-400" />
              </div>
              <div>
                <p className="text-sm font-medium text-clay-100">Client Drive Folder</p>
                <p className="text-[11px] text-clay-400">Google Drive — all assets</p>
              </div>
              <ExternalLink className="h-3.5 w-3.5 text-clay-500 group-hover:text-clay-300 ml-2 shrink-0" />
            </a>
          ) : (
            <div className="flex items-center gap-3 rounded-lg border border-clay-700/50 bg-clay-850/50 px-4 py-3 opacity-50">
              <div className="h-9 w-9 rounded-lg bg-clay-700 flex items-center justify-center shrink-0">
                <FolderOpen className="h-5 w-5 text-clay-500" />
              </div>
              <div>
                <p className="text-sm font-medium text-clay-400">No Drive Folder</p>
                <p className="text-[11px] text-clay-500">Sync not configured</p>
              </div>
            </div>
          )}

          {/* Project Drive Folders */}
          {projectsWithDrive.map((project) => (
            <a
              key={project.id}
              href={project.drive_folder_url!}
              target="_blank"
              rel="noopener noreferrer"
              className="flex items-center gap-3 rounded-lg border border-clay-700 bg-clay-850 px-4 py-3 hover:border-clay-500 hover:bg-clay-800 transition-colors retro-raised group"
            >
              <div className="h-9 w-9 rounded-lg bg-clay-700 flex items-center justify-center shrink-0">
                <span
                  className="h-4 w-4 rounded"
                  style={{ backgroundColor: project.color }}
                />
              </div>
              <div>
                <p className="text-sm font-medium text-clay-100">{project.name}</p>
                <p className="text-[11px] text-clay-400">Project folder — {project.media_count} files</p>
              </div>
              <ExternalLink className="h-3.5 w-3.5 text-clay-500 group-hover:text-clay-300 ml-2 shrink-0" />
            </a>
          ))}
        </div>
      </div>

      {/* Section B: Deliverables */}
      <div>
        <h3 className="text-xs font-semibold text-clay-300 uppercase tracking-wider mb-3 flex items-center gap-2">
          <Package className="h-3.5 w-3.5" />
          Deliverables
          {deliverables.length > 0 && (
            <span className="text-[10px] bg-clay-700 text-clay-400 px-1.5 py-0.5 rounded-full">
              {deliverables.length}
            </span>
          )}
        </h3>

        {deliverables.length === 0 ? (
          <div className="rounded-lg border border-clay-700 bg-clay-800 p-6 text-center">
            <Package className="h-8 w-8 text-clay-600 mx-auto mb-2" />
            <p className="text-sm text-clay-400">No deliverables yet.</p>
            <p className="text-[11px] text-clay-500 mt-1">Create a post with type "Deliverable" to see it here.</p>
          </div>
        ) : (
          <div className="space-y-2">
            {deliverables.map((d) => {
              const isExpanded = expandedDeliverable === d.id;
              const approvalBadge = d.approval_status ? APPROVAL_BADGES[d.approval_status] : null;
              const attachedCount = d.media_ids?.length || 0;
              const isInternal = !d.author_org || d.author_org === "internal";

              return (
                <div
                  key={d.id}
                  className="rounded-lg border border-purple-500/20 bg-clay-850 overflow-hidden retro-raised"
                >
                  <button
                    onClick={() => setExpandedDeliverable(isExpanded ? null : d.id)}
                    className="w-full flex items-center gap-3 px-4 py-3 text-left hover:bg-clay-800 transition-colors"
                  >
                    {isExpanded ? (
                      <ChevronDown className="h-4 w-4 text-clay-400 shrink-0" />
                    ) : (
                      <ChevronUp className="h-4 w-4 text-clay-400 shrink-0 rotate-180" />
                    )}

                    <div className="min-w-0 flex-1">
                      <p className="text-sm font-medium text-clay-100 truncate">{d.title}</p>
                      <div className="flex items-center gap-2 mt-0.5 flex-wrap">
                        <span className="text-[11px] text-clay-400">
                          {d.author_name || (isInternal ? "The Kiln" : clientName || "Client")}
                        </span>
                        <span className="text-clay-600 text-[10px]">&middot;</span>
                        <span className="text-[11px] text-clay-500">
                          {formatRelativeTime(d.created_at)}
                        </span>
                        {attachedCount > 0 && (
                          <>
                            <span className="text-clay-600 text-[10px]">&middot;</span>
                            <span className="flex items-center gap-0.5 text-[11px] text-clay-400">
                              <Paperclip className="h-2.5 w-2.5" />
                              {attachedCount}
                            </span>
                          </>
                        )}
                      </div>
                    </div>

                    {/* Approval badge */}
                    {approvalBadge && (
                      <span className={cn(
                        "text-[10px] font-medium px-2 py-0.5 rounded-full shrink-0",
                        approvalBadge.color, approvalBadge.bg
                      )}>
                        {approvalBadge.label}
                      </span>
                    )}

                    {/* Google Doc link */}
                    {d.google_doc_url && (
                      <a
                        href={d.google_doc_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        onClick={(e) => e.stopPropagation()}
                        className="text-blue-400/60 hover:text-blue-400 transition-colors shrink-0"
                        title="Open Google Doc"
                      >
                        <FileText className="h-4 w-4" />
                      </a>
                    )}
                  </button>

                  {isExpanded && (
                    <div className="border-t border-clay-700/40 px-4 py-3 space-y-3">
                      {d.body && <MarkdownContent content={d.body} />}

                      {/* Approval workflow */}
                      {d.approval_status && (
                        <ApprovalBanner slug={slug} update={d} onUpdated={onUpdated} />
                      )}
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        )}
      </div>

      {/* Section C: All Files */}
      <div>
        <div className="flex items-center justify-between mb-3">
          <h3 className="text-xs font-semibold text-clay-300 uppercase tracking-wider flex items-center gap-2">
            <Paperclip className="h-3.5 w-3.5" />
            All Files
            {media.length > 0 && (
              <span className="text-[10px] bg-clay-700 text-clay-400 px-1.5 py-0.5 rounded-full">
                {media.length}
              </span>
            )}
          </h3>
          <button
            onClick={() => setShowUpload(!showUpload)}
            className={cn(
              "text-xs px-3 py-1.5 rounded-lg transition-colors border",
              showUpload
                ? "bg-kiln-teal/10 text-kiln-teal border-kiln-teal/20"
                : "bg-clay-800 text-clay-300 border-clay-700 hover:border-clay-500"
            )}
          >
            {showUpload ? "Close" : "Upload File"}
          </button>
        </div>

        {showUpload && (
          <div className="mb-4">
            <MediaUpload
              slug={slug}
              onUploaded={() => { onMediaUploaded(); setShowUpload(false); }}
            />
          </div>
        )}

        {/* Grouped by project */}
        {Array.from(projectMediaMap.entries())
          .sort(([a], [b]) => {
            // Projects first, then unlinked
            if (a === null) return 1;
            if (b === null) return -1;
            return 0;
          })
          .map(([projectId, files]) => {
            const project = projectId ? projectLookup.get(projectId) : null;
            return (
              <div key={projectId || "unlinked"} className="mb-4">
                {/* Group header */}
                {(projectMediaMap.size > 1 || projectId) && (
                  <div className="flex items-center gap-2 mb-2">
                    {project ? (
                      <>
                        <span
                          className="h-2.5 w-2.5 rounded"
                          style={{ backgroundColor: project.color }}
                        />
                        <span className="text-xs font-medium text-clay-200">{project.name}</span>
                        <span className="text-[10px] text-clay-500">{files.length} files</span>
                      </>
                    ) : (
                      <>
                        <span className="h-2.5 w-2.5 rounded bg-clay-600" />
                        <span className="text-xs font-medium text-clay-300">General</span>
                        <span className="text-[10px] text-clay-500">{files.length} files</span>
                      </>
                    )}
                  </div>
                )}
                <MediaGrid media={files} onDelete={onMediaDeleted} />
              </div>
            );
          })}

        {media.length === 0 && !showUpload && (
          <div className="rounded-lg border border-clay-700 bg-clay-800 p-6 text-center">
            <Paperclip className="h-8 w-8 text-clay-600 mx-auto mb-2" />
            <p className="text-sm text-clay-400">No files uploaded yet.</p>
          </div>
        )}
      </div>
    </div>
  );
}
