"use client";

import { Pin } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
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

function TimeGroupHeader({ label }: { label: string }) {
  return (
    <div className="flex items-center gap-2 pt-1">
      <span className="text-[10px] font-semibold text-clay-500 uppercase tracking-wider">
        {label}
      </span>
      <div className="h-px flex-1 bg-clay-700" />
    </div>
  );
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

  // Group chronological by relative time
  const now = Date.now() / 1000;
  const groups = [
    { label: "Today", posts: chronological.filter((u) => now - u.created_at < 86400) },
    { label: "This Week", posts: chronological.filter((u) => now - u.created_at >= 86400 && now - u.created_at < 604800) },
    { label: "Earlier", posts: chronological.filter((u) => now - u.created_at >= 604800) },
  ].filter((g) => g.posts.length > 0);

  let animIndex = 0;

  return (
    <div className="space-y-4">
      {/* Pinned posts section */}
      <AnimatePresence>
        {pinned.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Pin className="h-3.5 w-3.5 text-amber-400" />
              <span className="text-xs font-semibold text-amber-400 uppercase tracking-wide">Pinned</span>
            </div>
            {pinned.map((update) => {
              const idx = animIndex++;
              return (
                <motion.div
                  key={update.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: idx * 0.05 }}
                >
                  <PostCard
                    ref={(el) => { postRefs.current[update.id] = el; }}
                    slug={slug}
                    update={update}
                    media={media}
                    onTogglePin={onTogglePin}
                    onDelete={onDeleteUpdate}
                    highlighted={update.id === highlightedPostId}
                  />
                </motion.div>
              );
            })}

            {/* Divider between pinned and chronological */}
            {groups.length > 0 && (
              <div className="flex items-center gap-3 mt-2 pt-2">
                <div className="h-px flex-1 bg-clay-700" />
                <span className="text-[10px] font-semibold text-clay-500 uppercase tracking-wider">Recent</span>
                <div className="h-px flex-1 bg-clay-700" />
              </div>
            )}
          </div>
        )}
      </AnimatePresence>

      {/* Chronological feed grouped by time */}
      <AnimatePresence>
        {groups.map((group) => (
          <div key={group.label} className="space-y-3">
            {/* Only show group header when there are multiple groups or pinned posts */}
            {(groups.length > 1 || pinned.length > 0) && (
              <TimeGroupHeader label={group.label} />
            )}
            {group.posts.map((update) => {
              const idx = animIndex++;
              return (
                <motion.div
                  key={update.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ duration: 0.3, delay: idx * 0.05 }}
                >
                  <PostCard
                    ref={(el) => { postRefs.current[update.id] = el; }}
                    slug={slug}
                    update={update}
                    media={media}
                    onTogglePin={onTogglePin}
                    onDelete={onDeleteUpdate}
                    highlighted={update.id === highlightedPostId}
                  />
                </motion.div>
              );
            })}
          </div>
        ))}
      </AnimatePresence>
    </div>
  );
}
