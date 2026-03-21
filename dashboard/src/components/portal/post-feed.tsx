"use client";

import { Pin } from "lucide-react";
import type { PortalUpdate, PortalMedia } from "@/lib/types";
import { PostCard } from "./post-card";

interface PostFeedProps {
  slug: string;
  updates: PortalUpdate[];
  media: PortalMedia[];
  searchQuery: string;
  highlightedPostId: string | null;
  postRefs: React.MutableRefObject<Record<string, HTMLDivElement | null>>;
  onTogglePin: (id: string) => void;
  onDeleteUpdate: (id: string) => void;
}

export function PostFeed({
  slug,
  updates,
  media,
  searchQuery,
  highlightedPostId,
  postRefs,
  onTogglePin,
  onDeleteUpdate,
}: PostFeedProps) {
  if (updates.length === 0) {
    return (
      <div className="rounded-lg border border-clay-700 bg-clay-800 p-8 text-center">
        <p className="text-sm text-clay-400">
          {searchQuery
            ? "No posts match your search."
            : "No posts yet. Create your first post to start the activity feed."}
        </p>
      </div>
    );
  }

  // Separate pinned from chronological
  const pinned = updates.filter((u) => u.pinned);
  const chronological = updates
    .filter((u) => !u.pinned)
    .sort((a, b) => b.created_at - a.created_at);

  return (
    <div className="space-y-4">
      {/* Pinned posts section */}
      {pinned.length > 0 && (
        <div className="space-y-3">
          <div className="flex items-center gap-2">
            <Pin className="h-3.5 w-3.5 text-amber-400" />
            <span className="text-xs font-semibold text-amber-400 uppercase tracking-wide">Pinned</span>
          </div>
          {pinned.map((update) => (
            <PostCard
              key={update.id}
              ref={(el) => { postRefs.current[update.id] = el; }}
              slug={slug}
              update={update}
              media={media}
              onTogglePin={onTogglePin}
              onDelete={onDeleteUpdate}
              highlighted={update.id === highlightedPostId}
            />
          ))}
          {chronological.length > 0 && (
            <div className="border-b border-clay-700" />
          )}
        </div>
      )}

      {/* Chronological feed */}
      {chronological.map((update) => (
        <PostCard
          key={update.id}
          ref={(el) => { postRefs.current[update.id] = el; }}
          slug={slug}
          update={update}
          media={media}
          onTogglePin={onTogglePin}
          onDelete={onDeleteUpdate}
          highlighted={update.id === highlightedPostId}
        />
      ))}
    </div>
  );
}
