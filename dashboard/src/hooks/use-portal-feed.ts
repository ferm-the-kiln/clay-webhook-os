import { useState, useMemo, useCallback, useRef } from "react";
import { toast } from "sonner";
import type { PortalUpdate } from "@/lib/types";

interface UsePortalFeedReturn {
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  highlightedPostId: string | null;
  highlightPost: (id: string, title?: string) => void;
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

  const highlightPost = useCallback((id: string, title?: string) => {
    setHighlightedPostId(id);
    // Scroll to the post
    const el = postRefs.current[id];
    if (el) {
      const rect = el.getBoundingClientRect();
      const isOffScreen = rect.top < 0 || rect.bottom > window.innerHeight;
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      if (isOffScreen && title) {
        toast(`Jumped to: ${title}`, { duration: 2000 });
      }
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
