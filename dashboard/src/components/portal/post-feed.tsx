"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { Pin, ChevronDown, ChevronUp, LayoutList, LayoutGrid, Plus, FileText, FolderPlus, MessageSquare, X } from "lucide-react";
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
  hasActiveFilters?: boolean;
  onClearFilters?: () => void;
  onOpenComposer?: () => void;
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

function getDensityPref(): boolean {
  if (typeof window === "undefined") return false;
  return localStorage.getItem("portal-density-preference") === "compact";
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
  hasActiveFilters,
  onClearFilters,
  onOpenComposer,
}: PostFeedProps) {
  const [earlierExpanded, setEarlierExpanded] = useState(false);
  const [focusedIndex, setFocusedIndex] = useState(-1);
  const [lastSeen] = useState(() => getLastSeenTimestamp(slug));
  const [compact, setCompact] = useState(getDensityPref);
  const containerRef = useRef<HTMLDivElement>(null);

  function toggleDensity() {
    const next = !compact;
    setCompact(next);
    localStorage.setItem("portal-density-preference", next ? "compact" : "comfortable");
  }

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
    // Filtered empty state
    if (hasActiveFilters) {
      return (
        <div className="rounded-lg border border-clay-700 bg-clay-800 p-8 text-center space-y-3">
          <MessageSquare className="h-8 w-8 text-clay-600 mx-auto" />
          <p className="text-sm text-clay-400">No posts match your filters.</p>
          {onClearFilters && (
            <button
              onClick={onClearFilters}
              className="inline-flex items-center gap-1.5 text-xs text-kiln-teal hover:text-kiln-teal/80 transition-colors"
            >
              <X className="h-3 w-3" />
              Clear all filters
            </button>
          )}
        </div>
      );
    }

    // Welcome empty state for new portals
    return (
      <div className="rounded-lg border border-clay-700 bg-clay-800 p-8 text-center space-y-4">
        <div className="space-y-2">
          <MessageSquare className="h-10 w-10 text-clay-600 mx-auto" />
          <h3 className="text-base font-semibold text-clay-200">
            Welcome to {clientName ? `${clientName}'s` : "this"} portal
          </h3>
          <p className="text-sm text-clay-400">
            Start by posting your first update to build the activity feed.
          </p>
        </div>
        {onOpenComposer && (
          <div className="flex items-center justify-center gap-2">
            <button
              onClick={onOpenComposer}
              className="inline-flex items-center gap-1.5 text-sm px-4 py-2 rounded-lg bg-kiln-teal/10 text-kiln-teal border border-kiln-teal/20 hover:bg-kiln-teal/20 transition-colors"
            >
              <Plus className="h-3.5 w-3.5" />
              Create Update
            </button>
          </div>
        )}
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
          compact={compact}
        />
      </motion.div>
    );
  }

  return (
    <div ref={containerRef} className="space-y-5">
      {/* Density toggle */}
      <div className="flex items-center justify-end">
        <div className="flex items-center gap-0.5 bg-clay-800 border border-clay-700 rounded-md p-0.5">
          <button
            onClick={() => { if (compact) toggleDensity(); }}
            className={`h-6 w-6 rounded flex items-center justify-center transition-colors ${
              !compact ? "bg-clay-700 text-clay-200" : "text-clay-500 hover:text-clay-300"
            }`}
            title="Comfortable view"
          >
            <LayoutGrid className="h-3.5 w-3.5" />
          </button>
          <button
            onClick={() => { if (!compact) toggleDensity(); }}
            className={`h-6 w-6 rounded flex items-center justify-center transition-colors ${
              compact ? "bg-clay-700 text-clay-200" : "text-clay-500 hover:text-clay-300"
            }`}
            title="Compact view"
          >
            <LayoutList className="h-3.5 w-3.5" />
          </button>
        </div>
      </div>

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
