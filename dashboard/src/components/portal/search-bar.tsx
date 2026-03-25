"use client";

import { useRef, useEffect, useState } from "react";
import { Search, X, Pin } from "lucide-react";
import { cn } from "@/lib/utils";
import type { AuthorFilter } from "@/hooks/use-portal-feed";

const AUTHOR_FILTERS: { id: AuthorFilter; label: string }[] = [
  { id: "all", label: "All" },
  { id: "internal", label: "Internal" },
  { id: "client", label: "Client" },
];

const TYPE_CHIPS: { id: string; label: string; color: string; activeColor: string }[] = [
  { id: "update", label: "Update", color: "text-blue-400", activeColor: "text-blue-400 border-blue-400/20 bg-blue-500/10" },
  { id: "milestone", label: "Milestone", color: "text-emerald-400", activeColor: "text-emerald-400 border-emerald-400/20 bg-emerald-500/10" },
  { id: "deliverable", label: "Deliverable", color: "text-purple-400", activeColor: "text-purple-400 border-purple-400/20 bg-purple-500/10" },
  { id: "note", label: "Note", color: "text-amber-400", activeColor: "text-amber-400 border-amber-400/20 bg-amber-500/10" },
];

interface SearchBarProps {
  value: string;
  onChange: (value: string) => void;
  resultCount: number;
  totalCount: number;
  authorFilter?: AuthorFilter;
  onAuthorFilterChange?: (filter: AuthorFilter) => void;
  typeFilters?: Set<string>;
  onTypeFiltersChange?: (filters: Set<string>) => void;
  pinnedOnly?: boolean;
  onPinnedOnlyChange?: (v: boolean) => void;
}

export function SearchBar({
  value,
  onChange,
  resultCount,
  totalCount,
  authorFilter = "all",
  onAuthorFilterChange,
  typeFilters,
  onTypeFiltersChange,
  pinnedOnly = false,
  onPinnedOnlyChange,
}: SearchBarProps) {
  const [local, setLocal] = useState(value);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setLocal(value);
  }, [value]);

  // Cmd+K to focus search
  useEffect(() => {
    function handleKeyDown(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === "k") {
        e.preventDefault();
        inputRef.current?.focus();
      }
    }
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  function handleChange(v: string) {
    setLocal(v);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => onChange(v), 300);
  }

  function handleClear() {
    setLocal("");
    onChange("");
  }

  function toggleType(typeId: string) {
    if (!typeFilters || !onTypeFiltersChange) return;
    const next = new Set(typeFilters);
    if (next.has(typeId)) {
      // Don't allow removing all types
      if (next.size > 1) next.delete(typeId);
    } else {
      next.add(typeId);
    }
    onTypeFiltersChange(next);
  }

  const isFiltered = value || authorFilter !== "all" || (typeFilters && typeFilters.size < 4) || pinnedOnly;

  return (
    <div className="space-y-2">
      <div className="relative">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-clay-500" />
        <input
          ref={inputRef}
          type="text"
          value={local}
          onChange={(e) => handleChange(e.target.value)}
          placeholder="Search posts... (\u2318K)"
          className="w-full rounded-lg border border-clay-700 bg-clay-900 pl-9 pr-20 py-2 text-sm text-clay-100 placeholder:text-clay-500 focus:border-clay-500 focus:outline-none"
        />
        <div className="absolute right-3 top-1/2 -translate-y-1/2 flex items-center gap-2">
          {isFiltered && (
            <>
              <span className="text-[10px] text-clay-500">
                {resultCount} of {totalCount}
              </span>
              {value && (
                <button onClick={handleClear} className="text-clay-500 hover:text-clay-300">
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </>
          )}
        </div>
      </div>

      {/* Filter chips row */}
      <div className="flex items-center gap-3 flex-wrap">
        {/* Type filters */}
        {onTypeFiltersChange && typeFilters && (
          <div className="flex items-center gap-1">
            {TYPE_CHIPS.map((t) => {
              const active = typeFilters.has(t.id);
              return (
                <button
                  key={t.id}
                  onClick={() => toggleType(t.id)}
                  className={cn(
                    "px-2 py-0.5 rounded-full text-[11px] font-medium transition-all border",
                    active
                      ? t.activeColor
                      : "text-clay-500 border-clay-700 bg-transparent opacity-50 hover:opacity-75"
                  )}
                >
                  {t.label}
                </button>
              );
            })}
          </div>
        )}

        {/* Separator */}
        {onTypeFiltersChange && onAuthorFilterChange && (
          <div className="h-4 w-px bg-clay-700" />
        )}

        {/* Author filters */}
        {onAuthorFilterChange && (
          <div className="flex items-center gap-1">
            {AUTHOR_FILTERS.map((f) => {
              const active = authorFilter === f.id;
              return (
                <button
                  key={f.id}
                  onClick={() => onAuthorFilterChange(f.id)}
                  className={cn(
                    "px-2 py-0.5 rounded-full text-[11px] font-medium transition-all border",
                    active
                      ? f.id === "client"
                        ? "text-purple-400 border-purple-400/20 bg-purple-500/10"
                        : f.id === "internal"
                          ? "text-kiln-teal border-kiln-teal/20 bg-kiln-teal/10"
                          : "text-clay-200 border-clay-500 bg-clay-700"
                      : "text-clay-500 border-clay-700 bg-transparent hover:text-clay-300 hover:border-clay-600"
                  )}
                >
                  {f.label}
                </button>
              );
            })}
          </div>
        )}

        {/* Pinned toggle */}
        {onPinnedOnlyChange && (
          <>
            <div className="h-4 w-px bg-clay-700" />
            <button
              onClick={() => onPinnedOnlyChange(!pinnedOnly)}
              className={cn(
                "flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] font-medium transition-all border",
                pinnedOnly
                  ? "text-amber-400 border-amber-400/20 bg-amber-500/10"
                  : "text-clay-500 border-clay-700 bg-transparent hover:text-clay-300 hover:border-clay-600"
              )}
            >
              <Pin className="h-2.5 w-2.5" />
              Pinned
            </button>
          </>
        )}
      </div>
    </div>
  );
}
