"use client";

import { motion, AnimatePresence } from "framer-motion";
import { Loader2, ExternalLink, Mail, Check, X, Ban } from "lucide-react";
import type { CellState } from "@/lib/types";

interface EnrichmentCellProps {
  value: unknown;
  status: CellState;
  error?: string;
  skipReason?: string;
  upstreamColumnName?: string;
}

/** Detect value type for conditional formatting */
function detectType(value: unknown): "boolean" | "url" | "email" | "number" | "text" {
  if (typeof value === "boolean") return "boolean";
  if (typeof value === "number") return "number";
  if (typeof value === "string") {
    if (/^https?:\/\//i.test(value)) return "url";
    if (/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) return "email";
  }
  return "text";
}

/** Number heat-map: 0-33 = red tint, 34-66 = amber tint, 67-100 = green tint */
function numberHeatColor(value: number): string {
  if (value <= 33) return "text-red-400";
  if (value <= 66) return "text-amber-400";
  return "text-emerald-400";
}

/** Format a value for display with conditional formatting */
function FormattedValue({ value }: { value: unknown }) {
  if (value === null || value === undefined) return <span className="text-clay-300">—</span>;

  const type = detectType(value);

  switch (type) {
    case "boolean":
      return value ? (
        <span className="flex items-center gap-1 text-emerald-400">
          <Check className="w-3 h-3" /> true
        </span>
      ) : (
        <span className="flex items-center gap-1 text-red-400">
          <X className="w-3 h-3" /> false
        </span>
      );

    case "url":
      return (
        <span className="flex items-center gap-1 text-blue-400 truncate">
          <ExternalLink className="w-3 h-3 shrink-0" />
          <span className="truncate">{String(value).replace(/^https?:\/\/(www\.)?/, "")}</span>
        </span>
      );

    case "email":
      return (
        <span className="flex items-center gap-1 text-blue-400 truncate">
          <Mail className="w-3 h-3 shrink-0" />
          <span className="truncate">{String(value)}</span>
        </span>
      );

    case "number": {
      const n = value as number;
      const color = n >= 0 && n <= 100 ? numberHeatColor(n) : "text-clay-100";
      return <span className={`tabular-nums ${color}`}>{String(n)}</span>;
    }

    default:
      if (typeof value === "object") {
        return (
          <span className="text-clay-200 truncate">
            {JSON.stringify(value).slice(0, 80)}
          </span>
        );
      }
      return <span className="truncate text-clay-100">{String(value).slice(0, 120)}</span>;
  }
}

export function EnrichmentCell({ value, status, error, skipReason, upstreamColumnName }: EnrichmentCellProps) {
  return (
    <AnimatePresence mode="wait">
      {/* Empty */}
      {status === "empty" && (
        <span key="empty" className="text-clay-300">
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
          className="h-4 w-full max-w-[140px] rounded bg-clay-700 shimmer"
        />
      )}

      {/* Running — spinner */}
      {status === "running" && (
        <motion.div
          key="running"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          exit={{ opacity: 0 }}
          className="flex items-center gap-1.5 text-clay-200"
        >
          <Loader2 className="w-3 h-3 animate-spin text-blue-400" />
          <span className="text-xs">Running...</span>
        </motion.div>
      )}

      {/* Done — green dot + formatted value */}
      {status === "done" && (
        <motion.div
          key="done"
          initial={{ opacity: 0, y: 4 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.2 }}
          className="flex items-center gap-1.5 min-w-0 text-xs"
        >
          <div className="w-1.5 h-1.5 rounded-full bg-emerald-500 shrink-0" />
          <FormattedValue value={value} />
        </motion.div>
      )}

      {/* Error — red dot + message */}
      {status === "error" && (
        <motion.div
          key="error"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="flex items-center gap-1.5 bg-red-500/5 rounded px-1 -mx-1"
          title={error}
        >
          <div className="w-1.5 h-1.5 rounded-full bg-red-500 shrink-0" />
          <span className="text-red-400 text-xs truncate">
            {error ? error.slice(0, 50) : "Error"}
          </span>
        </motion.div>
      )}

      {/* Skipped — upstream error cascade */}
      {status === "skipped" && skipReason === "upstream_error" && (
        <span
          key="skipped-upstream"
          className="flex items-center gap-1 text-clay-300 text-xs"
          title={upstreamColumnName ? `Skipped: ${upstreamColumnName} errored` : "Skipped: upstream error"}
        >
          <Ban className="w-3 h-3 shrink-0" />
          <span className="truncate">
            {upstreamColumnName ? `${upstreamColumnName} failed` : "Upstream error"}
          </span>
        </span>
      )}

      {/* Skipped — generic */}
      {status === "skipped" && skipReason !== "upstream_error" && (
        <span key="skipped" className="text-clay-300 text-xs">
          Skipped
        </span>
      )}

      {/* Filtered — row excluded by gate */}
      {status === "filtered" && (
        <span key="filtered" className="text-clay-300 text-xs line-through">
          Filtered
        </span>
      )}
    </AnimatePresence>
  );
}
