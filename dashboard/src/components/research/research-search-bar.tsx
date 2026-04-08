"use client";

import { useState, useRef, useEffect } from "react";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Search, X, Building2, User, Clock } from "lucide-react";
import { cn } from "@/lib/utils";
import type { EntityType } from "@/hooks/use-research";
import {
  getResearchHistory,
  type ResearchHistoryEntry,
} from "@/hooks/use-research";
import { formatRelativeTime } from "@/lib/utils";

interface ResearchSearchBarProps {
  onSearch: (query: string) => void;
  onClear: () => void;
  loading: boolean;
  detectedEntityType: EntityType | null;
}

export function ResearchSearchBar({
  onSearch,
  onClear,
  loading,
  detectedEntityType,
}: ResearchSearchBarProps) {
  const [value, setValue] = useState("");
  const [showHistory, setShowHistory] = useState(false);
  const [history, setHistory] = useState<ResearchHistoryEntry[]>([]);
  const inputRef = useRef<HTMLInputElement>(null);
  const wrapperRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  useEffect(() => {
    setHistory(getResearchHistory());
  }, []);

  // Close history dropdown on outside click
  useEffect(() => {
    const handleClick = (e: MouseEvent) => {
      if (
        wrapperRef.current &&
        !wrapperRef.current.contains(e.target as Node)
      ) {
        setShowHistory(false);
      }
    };
    document.addEventListener("mousedown", handleClick);
    return () => document.removeEventListener("mousedown", handleClick);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (value.trim()) {
      setShowHistory(false);
      onSearch(value.trim());
    }
  };

  const handleHistoryClick = (entry: ResearchHistoryEntry) => {
    setValue(entry.query);
    setShowHistory(false);
    onSearch(entry.query);
  };

  const handleClear = () => {
    setValue("");
    onClear();
    inputRef.current?.focus();
  };

  // Detect entity type from current input for the live indicator
  const liveEntityType = value.trim()
    ? value.includes("@")
      ? "person"
      : value.includes(".") && !value.includes(" ")
        ? "company"
        : value.split(/\s+/).length === 2 && !value.includes(".")
          ? "person"
          : "company"
    : null;

  const displayEntityType = detectedEntityType || liveEntityType;

  return (
    <div ref={wrapperRef} className="relative w-full max-w-2xl mx-auto">
      <form onSubmit={handleSubmit} className="relative">
        <div className="relative flex items-center">
          <Search className="absolute left-4 h-4.5 w-4.5 text-clay-300 pointer-events-none" />
          <Input
            ref={inputRef}
            value={value}
            onChange={(e) => setValue(e.target.value)}
            onFocus={() => history.length > 0 && setShowHistory(true)}
            placeholder="Search a company or person..."
            className="pl-11 pr-28 h-12 bg-clay-700/50 border-clay-500 text-clay-100 placeholder:text-clay-300 text-base rounded-xl focus-visible:ring-kiln-teal/40"
            disabled={loading}
          />
          <div className="absolute right-3 flex items-center gap-2">
            {displayEntityType && (
              <Badge
                variant="outline"
                className={cn(
                  "text-[10px] gap-1 border-clay-500",
                  displayEntityType === "company"
                    ? "text-kiln-teal"
                    : "text-purple-400"
                )}
              >
                {displayEntityType === "company" ? (
                  <Building2 className="h-3 w-3" />
                ) : (
                  <User className="h-3 w-3" />
                )}
                {displayEntityType === "company" ? "Company" : "Person"}
              </Badge>
            )}
            {value && !loading && (
              <button
                type="button"
                onClick={handleClear}
                className="text-clay-300 hover:text-clay-100 transition-colors"
              >
                <X className="h-4 w-4" />
              </button>
            )}
          </div>
        </div>
      </form>

      {/* History dropdown */}
      {showHistory && history.length > 0 && !loading && (
        <div className="absolute top-full mt-1.5 w-full bg-clay-700 border border-clay-500 rounded-lg shadow-xl z-50 overflow-hidden">
          <div className="px-3 py-2 border-b border-clay-600">
            <span className="text-[10px] font-semibold uppercase tracking-wider text-clay-300">
              Recent Searches
            </span>
          </div>
          <div className="max-h-60 overflow-y-auto">
            {history.map((entry, i) => (
              <button
                key={i}
                onClick={() => handleHistoryClick(entry)}
                className="w-full flex items-center gap-3 px-3 py-2 hover:bg-clay-600/50 transition-colors text-left"
              >
                <Clock className="h-3.5 w-3.5 text-clay-300 shrink-0" />
                <span className="text-sm text-clay-100 flex-1 truncate">
                  {entry.query}
                </span>
                <Badge
                  variant="outline"
                  className={cn(
                    "text-[9px] border-clay-500 shrink-0",
                    entry.entityType === "company"
                      ? "text-kiln-teal"
                      : "text-purple-400"
                  )}
                >
                  {entry.entityType === "company" ? "Company" : "Person"}
                </Badge>
                <span className="text-[10px] text-clay-300 shrink-0">
                  {formatRelativeTime(entry.timestamp / 1000)}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Keyboard hint */}
      {!value && !loading && (
        <p className="text-center text-xs text-clay-300 mt-3">
          Type a company name, domain, email, or person name and press{" "}
          <kbd className="retro-keycap text-[10px]">Enter</kbd>
        </p>
      )}
    </div>
  );
}
