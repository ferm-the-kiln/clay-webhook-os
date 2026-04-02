"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Loader2 } from "lucide-react";
import type { CellState } from "@/lib/types";

interface EnrichmentCellProps {
  value: unknown;
  status: CellState;
  error?: string;
}

/** Format a value for display in a cell */
function formatValue(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "boolean") return value ? "true" : "false";
  if (typeof value === "number") return String(value);
  if (typeof value === "object") return JSON.stringify(value).slice(0, 80);
  return String(value).slice(0, 120);
}

export function EnrichmentCell({ value, status, error }: EnrichmentCellProps) {
  return (
    <AnimatePresence mode="wait">
      {/* Empty */}
      {status === "empty" && (
        <span key="empty" className="text-zinc-600">
          —
        </span>
      )}

      {/* Pending — skeleton shimmer */}
      {status === "pending" && (
        <motion.div
          key="pending"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="h-4 w-full max-w-[140px] rounded bg-zinc-800 shimmer"
        />
      )}

      {/* Running — spinner */}
      {status === "running" && (
        <motion.div
          key="running"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="flex items-center gap-1.5 text-zinc-400"
        >
          <Loader2 className="w-3 h-3 animate-spin text-blue-400" />
          <span className="text-xs">Running...</span>
        </motion.div>
      )}

      {/* Done — green dot + value */}
      {status === "done" && (
        <motion.div
          key="done"
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="flex items-center gap-1.5 min-w-0"
        >
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
          <span className="truncate text-zinc-200 text-xs">
            {formatValue(value) || "—"}
          </span>
        </motion.div>
      )}

      {/* Error — red dot + message */}
      {status === "error" && (
        <motion.div
          key="error"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center gap-1.5"
          title={error}
        >
          <div className="w-1.5 h-1.5 rounded-full bg-red-500 shrink-0" />
          <span className="text-red-400 text-xs truncate">Error</span>
        </motion.div>
      )}

      {/* Skipped */}
      {status === "skipped" && (
        <span key="skipped" className="text-zinc-600 text-xs">
          Skipped
        </span>
      )}

      {/* Filtered — row excluded by gate */}
      {status === "filtered" && (
        <span key="filtered" className="text-zinc-600 text-xs line-through">
          Filtered
        </span>
      )}
    </AnimatePresence>
  );
}
