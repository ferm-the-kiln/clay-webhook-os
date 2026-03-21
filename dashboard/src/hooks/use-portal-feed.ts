import { useState, useMemo, useCallback, useRef } from "react";
import type { PortalUpdate } from "@/lib/types";

interface UsePortalFeedReturn {
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  highlightedPostId: string | null;
  highlightPost: (id: string) => void;
  clearHighlight: () => void;
  filteredUpdates: PortalUpdate[];
  postRefs: React.MutableRefObject<Record<string, HTMLDivElement | null>>;
}

export function usePortalFeed(updates: PortalUpdate[]): UsePortalFeedReturn {
  const [searchQuery, setSearchQuery] = useState("");
  const [highlightedPostId, setHighlightedPostId] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const postRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const filteredUpdates = useMemo(() => {
    const q = searchQuery.trim().toLowerCase();
    if (!q) return updates;
    return updates.filter(
      (u) =>
        u.title.toLowerCase().includes(q) ||
        u.body.toLowerCase().includes(q) ||
        u.type.toLowerCase().includes(q)
    );
  }, [updates, searchQuery]);

  const highlightPost = useCallback((id: string) => {
    setHighlightedPostId(id);
    // Scroll to the post
    const el = postRefs.current[id];
    if (el) {
      el.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    // Auto-clear after 3 seconds
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => setHighlightedPostId(null), 3000);
  }, []);

  const clearHighlight = useCallback(() => {
    setHighlightedPostId(null);
    if (timerRef.current) clearTimeout(timerRef.current);
  }, []);

  return {
    searchQuery,
    setSearchQuery,
    highlightedPostId,
    highlightPost,
    clearHighlight,
    filteredUpdates,
    postRefs,
  };
}
