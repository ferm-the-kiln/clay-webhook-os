"use client";

import { useState, forwardRef } from "react";
import { Pin, PinOff, Trash2, MoreVertical, Milestone, Package, StickyNote, Bell, FileIcon, Film, ChevronDown, ChevronUp, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { cn } from "@/lib/utils";
import type { PortalUpdate, PortalMedia } from "@/lib/types";
import { MarkdownContent } from "./markdown-content";
import { CommentThread } from "./comment-thread";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://clay.nomynoms.com";

const TYPE_CONFIG: Record<string, { icon: React.ElementType; label: string; color: string; border: string }> = {
  update: { icon: Bell, label: "Update", color: "text-blue-400 bg-blue-500/10", border: "border-l-blue-400" },
  milestone: { icon: Milestone, label: "Milestone", color: "text-emerald-400 bg-emerald-500/10", border: "border-l-emerald-400" },
  deliverable: { icon: Package, label: "Deliverable", color: "text-purple-400 bg-purple-500/10", border: "border-l-purple-400" },
  note: { icon: StickyNote, label: "Note", color: "text-amber-400 bg-amber-500/10", border: "border-l-clay-700" },
};

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

interface PostCardProps {
  slug: string;
  update: PortalUpdate;
  media: PortalMedia[];
  onTogglePin: (id: string) => void;
  onDelete: (id: string) => void;
  highlighted?: boolean;
}

export const PostCard = forwardRef<HTMLDivElement, PostCardProps>(
  function PostCard({ slug, update, media, onTogglePin, onDelete, highlighted }, ref) {
    const [expanded, setExpanded] = useState(false);
    const [previewUrl, setPreviewUrl] = useState<string | null>(null);

    const config = TYPE_CONFIG[update.type] || TYPE_CONFIG.update;
    const Icon = config.icon;

    // Resolve media attached to this post
    const attachedMedia = media.filter((m) => update.media_ids?.includes(m.id));

    // Determine if body is long (> 4 lines / ~300 chars)
    const isLong = update.body && update.body.length > 300;
    const showBody = update.body && (expanded || !isLong);

    return (
      <>
        <div
          ref={ref}
          className={cn(
            "rounded-lg border-l-4 border bg-clay-800 p-4 transition-all",
            config.border,
            update.pinned ? "border-amber-500/30 bg-amber-500/[0.03]" : "border-clay-700",
            highlighted && "ring-2 ring-kiln-teal/50 animate-pulse"
          )}
        >
          {/* Header: type badge + title + actions */}
          <div className="flex items-start gap-3">
            <div className={cn("p-1.5 rounded-md shrink-0 mt-0.5", config.color)}>
              <Icon className="h-4 w-4" />
            </div>
            <div className="min-w-0 flex-1">
              <div className="flex items-center gap-2 mb-1">
                <span className={cn("text-[10px] px-1.5 py-0.5 rounded font-medium uppercase", config.color)}>
                  {config.label}
                </span>
                <h4 className="text-sm font-medium text-clay-100 truncate">{update.title}</h4>
                {update.pinned && <Pin className="h-3 w-3 text-amber-400 shrink-0" />}
              </div>

              {/* Body */}
              {update.body && (
                <div className={cn(!showBody && "line-clamp-4")}>
                  <MarkdownContent content={update.body} />
                </div>
              )}
              {isLong && (
                <button
                  onClick={() => setExpanded(!expanded)}
                  className="flex items-center gap-1 mt-1 text-[11px] text-clay-400 hover:text-clay-200"
                >
                  {expanded ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                  {expanded ? "Show less" : "Show more"}
                </button>
              )}

              {/* Inline media */}
              {attachedMedia.length > 0 && (
                <div className={cn(
                  "mt-3 gap-2",
                  attachedMedia.length === 1 ? "block" : "grid grid-cols-2"
                )}>
                  {attachedMedia.slice(0, 4).map((m) => {
                    const fullUrl = `${API_URL}${m.url}`;
                    if (isImage(m.mime_type)) {
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
                    return (
                      <a
                        key={m.id}
                        href={fullUrl}
                        download={m.original_name}
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

              {/* Timestamp + comments */}
              <div className="flex items-center gap-3 mt-2">
                <span className="text-[10px] text-clay-500">
                  {new Date(update.created_at * 1000).toLocaleString()}
                </span>
              </div>
              <CommentThread slug={slug} updateId={update.id} />
            </div>

            {/* Kebab menu */}
            <DropdownMenu>
              <DropdownMenuTrigger asChild>
                <Button variant="ghost" size="icon" className="h-7 w-7 text-clay-400 hover:text-clay-200 shrink-0">
                  <MoreVertical className="h-4 w-4" />
                </Button>
              </DropdownMenuTrigger>
              <DropdownMenuContent align="end" className="bg-clay-800 border-clay-700">
                <DropdownMenuItem onClick={() => onTogglePin(update.id)} className="text-xs text-clay-200">
                  {update.pinned ? <PinOff className="h-3.5 w-3.5 mr-2" /> : <Pin className="h-3.5 w-3.5 mr-2" />}
                  {update.pinned ? "Unpin" : "Pin to top"}
                </DropdownMenuItem>
                <DropdownMenuItem onClick={() => onDelete(update.id)} className="text-xs text-red-400">
                  <Trash2 className="h-3.5 w-3.5 mr-2" />
                  Delete
                </DropdownMenuItem>
              </DropdownMenuContent>
            </DropdownMenu>
          </div>
        </div>

        {/* Lightbox for inline images */}
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
