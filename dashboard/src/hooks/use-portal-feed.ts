import { useState, useMemo, useCallback, useRef } from "react";
import { toast } from "sonner";
import type { PortalUpdate } from "@/lib/types";

export type AuthorFilter = "all" | "internal" | "client";

const ALL_TYPES = new Set(["update", "milestone", "deliverable", "note"]);

interface UsePortalFeedReturn {
  searchQuery: string;
  setSearchQuery: (q: string) => void;
  authorFilter: AuthorFilter;
  setAuthorFilter: (f: AuthorFilter) => void;
  typeFilters: Set<string>;
  setTypeFilters: (f: Set<string>) => void;
  pinnedOnly: boolean;
  setPinnedOnly: (v: boolean) => void;
  highlightedPostId: string | null;
  highlightPost: (id: string, title?: string) => void;
  clearHighlight: () => void;
  filteredUpdates: PortalUpdate[];
  postRefs: React.MutableRefObject<Record<string, HTMLDivElement | null>>;
  hasActiveFilters: boolean;
  clearAllFilters: () => void;
}

export function usePortalFeed(updates: PortalUpdate[]): UsePortalFeedReturn {
  const [searchQuery, setSearchQuery] = useState("");
  const [authorFilter, setAuthorFilter] = useState<AuthorFilter>("all");
  const [typeFilters, setTypeFilters] = useState<Set<string>>(new Set(ALL_TYPES));
  const [pinnedOnly, setPinnedOnly] = useState(false);
  const [highlightedPostId, setHighlightedPostId] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const postRefs = useRef<Record<string, HTMLDivElement | null>>({});

  const filteredUpdates = useMemo(() => {
    let result = updates;

    // Author filter
    if (authorFilter !== "all") {
      result = result.filter((u) => {
        const isInternal = !u.author_org || u.author_org === "internal";
        return authorFilter === "internal" ? isInternal : !isInternal;
      });
    }

    // Type filter (only apply if not all types selected)
    if (typeFilters.size < ALL_TYPES.size) {
      result = result.filter((u) => typeFilters.has(u.type));
    }

    // Pinned only
    if (pinnedOnly) {
      result = result.filter((u) => u.pinned);
    }

    // Text search
    const q = searchQuery.trim().toLowerCase();
    if (q) {
      result = result.filter(
        (u) =>
          u.title.toLowerCase().includes(q) ||
          u.body.toLowerCase().includes(q) ||
          u.type.toLowerCase().includes(q)
      );
    }

    return result;
  }, [updates, searchQuery, authorFilter, typeFilters, pinnedOnly]);

  const hasActiveFilters = searchQuery !== "" || authorFilter !== "all" || typeFilters.size < ALL_TYPES.size || pinnedOnly;

  const clearAllFilters = useCallback(() => {
    setSearchQuery("");
    setAuthorFilter("all");
    setTypeFilters(new Set(ALL_TYPES));
    setPinnedOnly(false);
  }, []);

  const highlightPost = useCallback((id: string, title?: string) => {
    setHighlightedPostId(id);
    const el = postRefs.current[id];
    if (el) {
      const rect = el.getBoundingClientRect();
      const isOffScreen = rect.top < 0 || rect.bottom > window.innerHeight;
      el.scrollIntoView({ behavior: "smooth", block: "center" });
      if (isOffScreen && title) {
        toast(`Jumped to: ${title}`, { duration: 2000 });
      }
    }
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
    authorFilter,
    setAuthorFilter,
    typeFilters,
    setTypeFilters,
    pinnedOnly,
    setPinnedOnly,
    highlightedPostId,
    highlightPost,
    clearHighlight,
    filteredUpdates,
    postRefs,
    hasActiveFilters,
    clearAllFilters,
  };
}
