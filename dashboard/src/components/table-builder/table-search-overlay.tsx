"use client";

import { useState, useEffect, useRef, useCallback } from "react";
import { X, ChevronUp, ChevronDown } from "lucide-react";
import { motion, AnimatePresence } from "framer-motion";

interface TableSearchOverlayProps {
  open: boolean;
  onClose: () => void;
  onSearch: (query: string) => void;
  matchCount: number;
  currentMatch: number;
  onNavigate: (direction: "up" | "down") => void;
}

export function TableSearchOverlay({
  open,
  onClose,
  onSearch,
  matchCount,
  currentMatch,
  onNavigate,
}: TableSearchOverlayProps) {
  const [query, setQuery] = useState("");
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (open) {
      inputRef.current?.focus();
      inputRef.current?.select();
    }
  }, [open]);

  useEffect(() => {
    onSearch(query);
  }, [query, onSearch]);

  const handleKeyDown = useCallback(
    (e: React.KeyboardEvent) => {
      if (e.key === "Escape") {
        onClose();
      } else if (e.key === "Enter") {
        e.preventDefault();
        onNavigate(e.shiftKey ? "up" : "down");
      }
    },
    [onClose, onNavigate],
  );

  // Global Cmd+F handler
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if ((e.metaKey || e.ctrlKey) && e.key === "f") {
        e.preventDefault();
        if (!open) {
          // The parent should handle opening — this is just for the overlay
        }
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [open]);

  return (
    <AnimatePresence>
      {open && (
        <motion.div
          initial={{ opacity: 0, y: -8 }}
          animate={{ opacity: 1, y: 0 }}
          exit={{ opacity: 0, y: -8 }}
          transition={{ duration: 0.15 }}
          className="absolute top-2 right-4 z-30 flex items-center gap-2 bg-zinc-900 border border-zinc-700 rounded-lg shadow-xl px-3 py-1.5"
        >
          <input
            ref={inputRef}
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder="Find in table..."
            className="w-48 bg-transparent text-sm text-white outline-none placeholder:text-zinc-500"
          />

          {/* Match count */}
          {query && (
            <span className="text-xs text-zinc-500 tabular-nums shrink-0">
              {matchCount > 0
                ? `${currentMatch + 1} of ${matchCount}`
                : "No matches"}
            </span>
          )}

          {/* Navigation */}
          <div className="flex items-center gap-0.5">
            <button
              onClick={() => onNavigate("up")}
              disabled={matchCount === 0}
              className="p-0.5 rounded hover:bg-zinc-700 text-zinc-400 disabled:opacity-30"
            >
              <ChevronUp className="w-3.5 h-3.5" />
            </button>
            <button
              onClick={() => onNavigate("down")}
              disabled={matchCount === 0}
              className="p-0.5 rounded hover:bg-zinc-700 text-zinc-400 disabled:opacity-30"
            >
              <ChevronDown className="w-3.5 h-3.5" />
            </button>
          </div>

          {/* Close */}
          <button
            onClick={() => {
              setQuery("");
              onClose();
            }}
            className="p-0.5 rounded hover:bg-zinc-700 text-zinc-400"
          >
            <X className="w-3.5 h-3.5" />
          </button>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
