"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Pin, ChevronDown, ChevronUp } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";
import type { PortalUpdate, PortalMedia, ProjectSummary } from "@/lib/types";
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
  onMoveToProject?: (updateId: string, projectId: string | null) => void;
  onUpdated?: () => void;
  clientName?: string;
  projects?: ProjectSummary[];
}

function getLastSeenTimestamp(slug: string): number {
  if (typeof window === "undefined") return 0;
  return Number(localStorage.getItem(`lastSeen:${slug}`) || "0");
}

function markAsSeen(slug: string) {
  localStorage.setItem(`lastSeen:${slug}`, String(Math.floor(Date.now() / 1000)));
}

function TimeGroupHeader({ label, sticky }: { label: string; sticky?: boolean }) {
  return (
    <div className={sticky
      ? "flex items-center gap-2 pt-1 sticky top-0 z-10 bg-clay-900/95 backdrop-blur-sm pb-2 -mx-1 px-1"
      : "flex items-center gap-2 pt-1"
    }>
      <span className="text-[11px] font-semibold text-clay-300 uppercase tracking-wider">
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
  onMoveToProject,
  onUpdated,
  clientName,
  projects,
}: PostFeedProps) {
  const [earlierExpanded, setEarlierExpanded] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const [lastSeen] = useState(() => getLastSeenTimestamp(slug));
  const containerRef = useRef<HTMLDivElement>(null);

  // Mark as seen after mount
  useEffect(() => {
    const timer = setTimeout(() => markAsSeen(slug), 2000);
    return () => clearTimeout(timer);
  }, [slug]);

  // Build flat list of all visible update IDs for keyboard nav
  const pinned = updates.filter((u) => u.pinned);
  const chronological = updates
    .filter((u) => !u.pinned)
    .sort((a, b) => b.created_at - a.created_at);

  const now = Date.now() / 1000;
  const groups = [
    { label: "Today", posts: chronological.filter((u) => now - u.created_at < 86400) },
    { label: "This Week", posts: chronological.filter((u) => now - u.created_at >= 86400 && now - u.created_at < 604800) },
    { label: "Earlier", posts: chronological.filter((u) => now - u.created_at >= 604800) },
  ].filter((g) => g.posts.length > 0);

  const earlierGroup = groups.find((g) => g.label === "Earlier");
  const nonEarlierGroups = groups.filter((g) => g.label !== "Earlier");

  // Flat ordered list of all visible IDs
  const allVisibleIds = [
    ...pinned.map((u) => u.id),
    ...nonEarlierGroups.flatMap((g) => g.posts.map((u) => u.id)),
    ...(earlierExpanded && earlierGroup ? earlierGroup.posts.map((u) => u.id) : []),
  ];

  // Keyboard navigation
  const handleKeyDown = useCallback((e: KeyboardEvent) => {
    if (e.target instanceof HTMLInputElement || e.target instanceof HTMLTextAreaElement) return;

    if (e.key === "j" || e.key === "ArrowDown") {
      e.preventDefault();
      setFocusedIndex((prev) => {
        const next = Math.min(prev + 1, allVisibleIds.length - 1);
        const id = allVisibleIds[next];
        if (id && postRefs.current[id]) {
          postRefs.current[id]?.scrollIntoView({ behavior: "smooth", block: "center" });
          postRefs.current[id]?.focus();
        }
        return next;
      });
    } else if (e.key === "k" || e.key === "ArrowUp") {
      e.preventDefault();
      setFocusedIndex((prev) => {
        const next = Math.max(prev - 1, 0);
        const id = allVisibleIds[next];
        if (id && postRefs.current[id]) {
          postRefs.current[id]?.scrollIntoView({ behavior: "smooth", block: "center" });
          postRefs.current[id]?.focus();
        }
        return next;
      });
    }
  }, [allVisibleIds, postRefs]);

  useEffect(() => {
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

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

  let animIndex = 0;

  function renderCard(update: PortalUpdate) {
    const idx = animIndex++;
    const isNew = lastSeen > 0 && update.created_at > lastSeen;
    const globalIdx = allVisibleIds.indexOf(update.id);

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
          clientName={clientName}
          isNew={isNew}
          isFocused={globalIdx === focusedIndex}
          projects={projects}
          onMoveToProject={onMoveToProject}
          onUpdated={onUpdated}
        />
      </motion.div>
    );
  }

  return (
    <div ref={containerRef} className="space-y-5">
      {/* Pinned posts */}
      <AnimatePresence>
        {pinned.length > 0 && (
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Pin className="h-3.5 w-3.5 text-amber-400" />
              <span className="text-xs font-semibold text-amber-400 uppercase tracking-wide">Pinned</span>
            </div>
            {pinned.map(renderCard)}

            {(nonEarlierGroups.length > 0 || earlierGroup) && (
              <div className="flex items-center gap-3 mt-2 pt-2">
                <div className="h-px flex-1 bg-clay-700" />
                <span className="text-[11px] font-semibold text-clay-300 uppercase tracking-wider">Recent</span>
                <div className="h-px flex-1 bg-clay-700" />
              </div>
            )}
          </div>
        )}
      </AnimatePresence>

      {/* Non-earlier groups with sticky headers */}
      <AnimatePresence>
        {nonEarlierGroups.map((group) => (
          <div key={group.label} className="space-y-3">
            {(groups.length > 1 || pinned.length > 0) && (
              <TimeGroupHeader label={group.label} sticky />
            )}
            {group.posts.map(renderCard)}
          </div>
        ))}
      </AnimatePresence>

      {/* Earlier — collapsible */}
      {earlierGroup && (
        <div className="space-y-3">
          <button
            onClick={() => setEarlierExpanded(!earlierExpanded)}
            className="flex items-center gap-2 pt-1 w-full group/earlier"
          >
            <span className="text-[11px] font-semibold text-clay-300 uppercase tracking-wider">
              Earlier
            </span>
            <span className="text-[11px] bg-clay-700 text-clay-300 px-1.5 py-0.5 rounded-full">
              {earlierGroup.posts.length}
            </span>
            {earlierExpanded
              ? <ChevronUp className="h-3 w-3 text-clay-400" />
              : <ChevronDown className="h-3 w-3 text-clay-400" />
            }
            <div className="h-px flex-1 bg-clay-700" />
          </button>

          <AnimatePresence>
            {earlierExpanded && (
              <motion.div
                initial={{ opacity: 0, height: 0 }}
                animate={{ opacity: 1, height: "auto" }}
                exit={{ opacity: 0, height: 0 }}
                transition={{ duration: 0.3 }}
                className="space-y-3 overflow-hidden"
              >
                {earlierGroup.posts.map(renderCard)}
              </motion.div>
            )}
          </AnimatePresence>
        </div>
      )}
    </div>
  );
}
