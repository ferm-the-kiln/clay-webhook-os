"use client";

import Link from "next/link";
import { Pin, MessageSquare, Paperclip, FileIcon, Image } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PortalUpdate, PortalMedia } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

function isImage(mime: string) {
  return mime.startsWith("image/");
}

function formatRelativeTime(epochSeconds: number): string {
  const diff = Date.now() / 1000 - epochSeconds;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  const date = new Date(epochSeconds * 1000);
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

interface PinnedStripProps {
  slug: string;
  pinnedUpdates: PortalUpdate[];
  media: PortalMedia[];
  onSelectUpdate?: (updateId: string) => void;
}

export function PinnedStrip({ slug, pinnedUpdates, media, onSelectUpdate }: PinnedStripProps) {
  if (pinnedUpdates.length === 0) return null;

  return (
    <div className="rounded-lg border border-amber-500/20 bg-amber-500/[0.03] px-4 py-2.5">
      <div className="flex items-center gap-2 mb-2">
        <Pin className="h-3 w-3 text-amber-400" />
        <span className="text-[11px] font-semibold text-amber-400 uppercase tracking-wider">
          Pinned
        </span>
        <span className="text-[11px] text-clay-300">{pinnedUpdates.length}</span>
      </div>

      <div className="flex gap-3 overflow-x-auto pb-1 -mx-1 px-1 scrollbar-thin scrollbar-thumb-clay-600">
        {pinnedUpdates.map((update) => {
          // Find first image attachment for thumbnail
          const firstImageId = update.media_ids?.find((id) => {
            const m = media.find((med) => med.id === id);
            return m && isImage(m.mime_type);
          });
          const thumbnail = firstImageId
            ? media.find((m) => m.id === firstImageId)
            : null;
          const thumbnailUrl = thumbnail?.url ? `${API_URL}${thumbnail.url}` : null;

          return (
            <button
              key={update.id}
              onClick={() => onSelectUpdate?.(update.id)}
              className="flex-shrink-0 group flex items-center gap-2.5 rounded-md bg-clay-800/60 border border-clay-700/50 px-3 py-2 hover:border-clay-600 hover:bg-clay-800 transition-all max-w-[280px]"
            >
              {/* Thumbnail or icon */}
              {thumbnailUrl ? (
                <div className="h-8 w-8 rounded overflow-hidden flex-shrink-0 bg-clay-900">
                  {/* eslint-disable-next-line @next/next/no-img-element */}
                  <img src={thumbnailUrl} alt="" className="h-full w-full object-cover" />
                </div>
              ) : update.media_ids && update.media_ids.length > 0 ? (
                <div className="h-8 w-8 rounded bg-clay-700 flex items-center justify-center flex-shrink-0">
                  <Paperclip className="h-3.5 w-3.5 text-clay-400" />
                </div>
              ) : (
                <div className="h-8 w-8 rounded bg-clay-700 flex items-center justify-center flex-shrink-0">
                  <MessageSquare className="h-3.5 w-3.5 text-clay-400" />
                </div>
              )}

              {/* Text */}
              <div className="min-w-0 text-left">
                <p className="text-xs font-medium text-clay-200 truncate group-hover:text-clay-100">
                  {update.title}
                </p>
                <p className="text-[11px] text-clay-400">
                  {formatRelativeTime(update.created_at)}
                </p>
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
