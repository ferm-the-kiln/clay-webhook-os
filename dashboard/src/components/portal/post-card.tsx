"use client";

import { useState, forwardRef, useCallback } from "react";
import {
  Pin, PinOff, Trash2, MoreVertical, FileIcon, Film,
  ChevronDown, ChevronUp, X, FileText, Milestone, Package, FolderOpen,
} from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import Link from "next/link";
import type { PortalUpdate, PortalMedia, ProjectSummary } from "@/lib/types";
import { MarkdownContent } from "./markdown-content";
import { CommentThread } from "./comment-thread";
import { ConfirmDeleteDialog } from "./confirm-delete-dialog";
import { VideoEmbed } from "./video-embed";
import { parseVideoUrls } from "@/lib/video-utils";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://clay.nomynoms.com";

const TYPE_CONFIG: Record<string, {
  label: string;
  textColor: string;
  border: string;
  bg: string;
  icon?: React.ElementType;
}> = {
  update: { label: "Update", textColor: "text-blue-400", border: "border-l-blue-400", bg: "" },
  milestone: { label: "Milestone", textColor: "text-emerald-400", border: "border-l-emerald-400", bg: "bg-emerald-500/[0.03]", icon: Milestone },
  deliverable: { label: "Deliverable", textColor: "text-purple-400", border: "border-l-purple-400", bg: "bg-purple-500/[0.03]", icon: Package },
  note: { label: "Note", textColor: "text-amber-400", border: "border-l-clay-600", bg: "" },
};

const REACTIONS = ["👍", "🔥", "👀", "✅"];

function isImage(mime: string) {
  return mime.startsWith("image/");
}

function isVideo(mime: string) {
  return mime.startsWith("video/");
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes}B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)}KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)}MB`;
}

function formatRelativeTime(epochSeconds: number): string {
  const now = Date.now() / 1000;
  const diff = now - epochSeconds;

  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 172800) return "Yesterday";
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;

  const date = new Date(epochSeconds * 1000);
  const currentYear = new Date().getFullYear();
  const month = date.toLocaleString("default", { month: "short" });
  const day = date.getDate();
  return date.getFullYear() === currentYear ? `${month} ${day}` : `${month} ${day}, ${date.getFullYear()}`;
}

function getReactions(updateId: string): Record<string, boolean> {
  if (typeof window === "undefined") return {};
  try {
    return JSON.parse(localStorage.getItem(`reactions:${updateId}`) || "{}");
  } catch { return {}; }
}

function setReactions(updateId: string, reactions: Record<string, boolean>) {
  localStorage.setItem(`reactions:${updateId}`, JSON.stringify(reactions));
}

interface PostCardProps {
  slug: string;
  update: PortalUpdate;
  media: PortalMedia[];
  onTogglePin: (id: string) => void;
  onDelete: (id: string) => void;
  highlighted?: boolean;
  clientName?: string;
  isNew?: boolean;
  isFocused?: boolean;
  projects?: ProjectSummary[];
  onMoveToProject?: (updateId: string, projectId: string | null) => void;
}

export const PostCard = forwardRef<HTMLDivElement, PostCardProps>(
  function PostCard({ slug, update, media, onTogglePin, onDelete, highlighted, clientName, isNew, isFocused, projects, onMoveToProject }, ref) {
    const [expanded, setExpanded] = useState(false);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);
    const [reactions, setReactionsState] = useState<Record<string, boolean>>(() => getReactions(update.id));
    const [reactionsHovered, setReactionsHovered] = useState(false);
    const [deleteDialogOpen, setDeleteDialogOpen] = useState(false);

    const config = TYPE_CONFIG[update.type] || TYPE_CONFIG.update;
    const TypeIcon = config.icon;

    const attachedMedia = media.filter((m) => update.media_ids?.includes(m.id));

    const isLong = update.body && update.body.length > 300;
    const isShortBody = update.body && update.body.length <= 80 && !update.body.includes("\n");
    const showBody = update.body && (expanded || !isLong);
    const hasBody = !!update.body;

    const isInternal = !update.author_org || update.author_org === "internal";
    const orgLabel = isInternal ? "The Kiln" : (clientName || "Client");
    const hasAuthor = update.author_name || update.author_org;
    const fullDate = new Date(update.created_at * 1000).toLocaleString(undefined, {
      dateStyle: "medium",
      timeStyle: "short",
    });

    const activeReactions = REACTIONS.filter((r) => reactions[r]);

    const toggleReaction = useCallback((emoji: string) => {
      setReactionsState((prev) => {
        const next = { ...prev, [emoji]: !prev[emoji] };
        setReactions(update.id, next);
        return next;
      });
    }, [update.id]);

    const handleBodyClick = useCallback(() => {
      if (isLong) setExpanded((e) => !e);
    }, [isLong]);

    return (
      <>
        <div
          ref={ref}
          tabIndex={0}
          className={cn(
            "rounded-lg border-l-4 bg-clay-800 transition-all group outline-none",
            hasBody ? "px-4 py-3.5" : "px-4 py-3",
            config.border,
            config.bg,
            update.pinned && "ring-1 ring-amber-500/20 bg-amber-500/[0.03]",
            highlighted && "ring-2 ring-kiln-teal/50 animate-pulse",
            isFocused && "ring-2 ring-kiln-teal/40",
          )}
        >
          {/* New indicator */}
          {isNew && (
            <div className="flex items-center gap-1.5 mb-2">
              <span className="h-1.5 w-1.5 rounded-full bg-kiln-teal animate-pulse" />
              <span className="text-[10px] font-semibold text-kiln-teal uppercase tracking-wide">New</span>
            </div>
          )}

          {/* Header section: org + title + metadata + kebab */}
          <div className="flex items-start gap-2 pb-2.5 border-b border-clay-700/40">
            <div className="min-w-0 flex-1">
              {/* Title */}
              <div className="flex items-center gap-2">
                {TypeIcon && <TypeIcon className={cn("h-4 w-4 shrink-0", config.textColor)} />}
                <h4 className="text-lg font-semibold text-clay-50 truncate">{update.title}</h4>
              </div>

              {/* Metadata line: org pill + author + type pill + time */}
              <div className="flex items-center gap-2.5 mt-2 flex-wrap">
                {hasAuthor && (
                  <>
                    <span className={cn(
                      "text-xs font-medium px-2.5 py-0.5 rounded-full border",
                      isInternal
                        ? "bg-kiln-teal/10 text-kiln-teal border-kiln-teal/20"
                        : "bg-purple-500/10 text-purple-400 border-purple-500/20"
                    )}>
                      {orgLabel}
                    </span>
                    {update.author_name && (
                      <span className="text-xs text-clay-300">{update.author_name}</span>
                    )}
                  </>
                )}
                <span className={cn(
                  "text-xs font-medium px-2.5 py-0.5 rounded-full border",
                  config.textColor,
                  "bg-clay-800 border-clay-600/60"
                )}>
                  {config.label}
                </span>
                {update.project_id && projects && (() => {
                  const proj = projects.find((p) => p.id === update.project_id);
                  if (!proj) return null;
                  return (
                    <Link
                      href={`/clients/${slug}/projects/${proj.id}`}
                      className="inline-flex items-center gap-1.5 text-xs font-medium px-2 py-0.5 rounded-full border border-clay-600/60 bg-clay-800 text-clay-300 hover:text-clay-100 hover:border-clay-500 transition-colors"
                      onClick={(e) => e.stopPropagation()}
                    >
                      <span
                        className="h-2 w-2 rounded-full flex-shrink-0"
                        style={{ backgroundColor: proj.color }}
                      />
                      {proj.name}
                    </Link>
                  );
                })()}
                <span className="text-xs text-clay-400" title={fullDate}>
                  {formatRelativeTime(update.created_at)}
                </span>
                {isShortBody && (
                  <>
                    <span className="text-clay-600">&middot;</span>
                    <span className="text-xs text-clay-300 truncate">{update.body}</span>
                  </>
                )}
              </div>
            </div>

            {/* Kebab menu — hidden until hover */}
            <div className="opacity-0 group-hover:opacity-100 transition-opacity">
              <DropdownMenu>
                <DropdownMenuTrigger asChild>
                  <Button variant="ghost" size="icon" className="h-7 w-7 text-clay-500 hover:text-clay-200 shrink-0">
                    <MoreVertical className="h-4 w-4" />
                  </Button>
                </DropdownMenuTrigger>
                <DropdownMenuContent align="end" className="bg-clay-800 border-clay-700">
                  <DropdownMenuItem onClick={() => onTogglePin(update.id)} className="text-xs text-clay-200">
                    {update.pinned ? <PinOff className="h-3.5 w-3.5 mr-2" /> : <Pin className="h-3.5 w-3.5 mr-2" />}
                    {update.pinned ? "Unpin" : "Pin to top"}
                  </DropdownMenuItem>
                  {/* Move to project */}
                  {onMoveToProject && projects && projects.length > 0 && (
                    <>
                      {update.project_id ? (
                        <DropdownMenuItem
                          onClick={() => onMoveToProject(update.id, null)}
                          className="text-xs text-clay-200"
                        >
                          <FolderOpen className="h-3.5 w-3.5 mr-2" />
                          Remove from project
                        </DropdownMenuItem>
                      ) : null}
                      {projects
                        .filter((p) => p.id !== update.project_id)
                        .slice(0, 5)
                        .map((p) => (
                          <DropdownMenuItem
                            key={p.id}
                            onClick={() => onMoveToProject(update.id, p.id)}
                            className="text-xs text-clay-200"
                          >
                            <span
                              className="h-2.5 w-2.5 rounded-full mr-2 flex-shrink-0"
                              style={{ backgroundColor: p.color }}
                            />
                            Move to {p.name}
                          </DropdownMenuItem>
                        ))}
                    </>
                  )}
                  <DropdownMenuItem onClick={() => setDeleteDialogOpen(true)} className="text-xs text-red-400">
                    <Trash2 className="h-3.5 w-3.5 mr-2" />
                    Delete
                  </DropdownMenuItem>
                </DropdownMenuContent>
              </DropdownMenu>
            </div>
          </div>

          {/* Body — click to expand, animated */}
          {update.body && !isShortBody && (
            <AnimatePresence initial={false}>
              <motion.div
                className={cn("mt-3", isLong && "cursor-pointer")}
                onClick={handleBodyClick}
                animate={{ height: "auto" }}
                transition={{ duration: 0.2 }}
              >
                <div className={cn(!showBody && "line-clamp-4")}>
                  <MarkdownContent content={update.body} />
                </div>
              </motion.div>
            </AnimatePresence>
          )}
          {isLong && (
            <button
              onClick={() => setExpanded(!expanded)}
              className="flex items-center gap-1 mt-2 text-xs text-clay-300 font-medium hover:text-clay-200 transition-colors"
            >
              {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
              {expanded ? "Show less" : "Show more"}
            </button>
          )}

          {/* Video embeds from body */}
          {update.body && (() => {
            const videos = parseVideoUrls(update.body);
            if (videos.length === 0) return null;
            return (
              <div className="mt-3 space-y-2">
                {videos.map((v, i) => (
                  <VideoEmbed key={i} video={v} />
                ))}
              </div>
            );
          })()}

          {/* Inline media */}
          {attachedMedia.length > 0 && (
            <div className={cn(
              "mt-3 gap-2",
              attachedMedia.length === 1 ? "block" : "grid grid-cols-2"
            )}>
              {attachedMedia.slice(0, 4).map((m) => {
                const fullUrl = m.url ? `${API_URL}${m.url}` : "";
                const driveUrl = m.drive_file_id
                  ? `https://drive.google.com/file/d/${m.drive_file_id}/view`
                  : null;
                if (isImage(m.mime_type) && fullUrl) {
                  return (
                    <button
                      key={m.id}
                      onClick={() => setPreviewUrl(fullUrl)}
                      className="rounded-md overflow-hidden bg-clay-900 aspect-video w-full"
                    >
                      {/* eslint-disable-next-line @next/next/no-img-element */}
                      <img src={fullUrl} alt={m.caption || m.original_name} className="w-full h-full object-cover" />
                    </button>
                  );
                }
                if (isVideo(m.mime_type)) {
                  return (
                    <div key={m.id} className="rounded-md bg-clay-900 aspect-video flex items-center justify-center">
                      <Film className="h-6 w-6 text-clay-500" />
                      <span className="text-xs text-clay-400 ml-2">{m.original_name}</span>
                    </div>
                  );
                }
                const downloadUrl = driveUrl || fullUrl;
                if (!downloadUrl) return null;
                return (
                  <a
                    key={m.id}
                    href={downloadUrl}
                    target={driveUrl ? "_blank" : undefined}
                    rel={driveUrl ? "noopener noreferrer" : undefined}
                    download={driveUrl ? undefined : m.original_name}
                    className="flex items-center gap-2 rounded-md bg-clay-900 border border-clay-700 px-3 py-2 hover:border-clay-500 transition-colors"
                  >
                    <FileIcon className="h-4 w-4 text-clay-500 shrink-0" />
                    <div className="min-w-0">
                      <p className="text-xs text-clay-200 truncate">{m.original_name}</p>
                      <p className="text-[10px] text-clay-500">{formatBytes(m.size_bytes)}</p>
                    </div>
                  </a>
                );
              })}
              {attachedMedia.length > 4 && (
                <div className="rounded-md bg-clay-900 aspect-video flex items-center justify-center text-xs text-clay-400">
                  +{attachedMedia.length - 4} more
                </div>
              )}
            </div>
          )}

          {/* Divider before reactions (only if there was content above) */}
          {(hasBody || attachedMedia.length > 0) && (
            <div className="border-b border-clay-700/40 mt-3" />
          )}

          {/* Quick reactions — collapse to selected only, expand all on hover */}
          <div
            className={cn(
              "flex items-center gap-1 mt-2.5 transition-opacity",
              activeReactions.length > 0 || reactionsHovered ? "opacity-100" : "opacity-40 group-hover:opacity-100"
            )}
            onMouseEnter={() => setReactionsHovered(true)}
            onMouseLeave={() => setReactionsHovered(false)}
          >
            {REACTIONS.map((emoji) => {
              if (activeReactions.length > 0 && !reactionsHovered && !reactions[emoji]) return null;
              return (
                <button
                  key={emoji}
                  onClick={() => toggleReaction(emoji)}
                  className={cn(
                    "h-7 px-2 rounded-full text-sm transition-all",
                    reactions[emoji]
                      ? "bg-kiln-teal/15 ring-1 ring-kiln-teal/30 scale-110"
                      : "bg-clay-700/50 hover:bg-clay-700"
                  )}
                >
                  {emoji}
                </button>
              );
            })}
          </div>

          {/* Action row: comments + google doc */}
          <div className="flex items-center gap-3 mt-3 pt-2.5 border-t border-clay-700/40">
            <CommentThread slug={slug} updateId={update.id} />
            {update.google_doc_url && (
              <a
                href={update.google_doc_url}
                target="_blank"
                rel="noopener noreferrer"
                className="flex items-center gap-1 text-xs text-blue-400/60 hover:text-blue-400 transition-colors ml-auto"
                title="Open in Google Docs"
              >
                <FileText className="h-3.5 w-3.5" />
                <span>Google Doc</span>
              </a>
            )}
          </div>
        </div>

        {/* Delete confirmation dialog */}
        <ConfirmDeleteDialog
          open={deleteDialogOpen}
          onOpenChange={setDeleteDialogOpen}
          onConfirm={() => {
            setDeleteDialogOpen(false);
            onDelete(update.id);
          }}
          title={update.title}
          mediaCount={attachedMedia.length}
        />

        {/* Lightbox */}
        {previewUrl && (
          <div
            className="fixed inset-0 z-50 bg-black/80 flex items-center justify-center p-8"
            onClick={() => setPreviewUrl(null)}
          >
            <Button
              variant="ghost"
              size="icon"
              onClick={() => setPreviewUrl(null)}
              className="absolute top-4 right-4 text-white hover:bg-white/10"
            >
              <X className="h-6 w-6" />
            </Button>
            {/* eslint-disable-next-line @next/next/no-img-element */}
            <img
              src={previewUrl}
              alt="Preview"
              className="max-w-full max-h-full rounded-lg"
              onClick={(e) => e.stopPropagation()}
            />
          </div>
        )}
      </>
    );
  }
);
