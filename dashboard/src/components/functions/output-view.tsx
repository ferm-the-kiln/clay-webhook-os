"use client";

import { useState } from "react";
import { ChevronDown, ChevronRight, AlertTriangle } from "lucide-react";
import { cn } from "@/lib/utils";

const HIDDEN_KEYS = new Set(["error", "error_message"]);

function isHiddenKey(key: string): boolean {
  return key.startsWith("_") || HIDDEN_KEYS.has(key);
}

function inferType(value: unknown): string {
  if (value === null) return "null";
  if (Array.isArray(value)) return "array";
  return typeof value;
}

function isScoreLike(key: string, value: unknown): boolean {
  if (typeof value !== "number") return false;
  if (value < 0 || value > 1) return false;
  return /confidence|score/i.test(key);
}

interface OutputViewProps {
  result: Record<string, unknown>;
}

export function OutputView({ result }: OutputViewProps) {
  const fields = Object.entries(result).filter(([k]) => !isHiddenKey(k));

  if (fields.length === 0) {
    return (
      <div className="text-xs text-clay-300 py-4 text-center">
        No output fields returned
      </div>
    );
  }

  return (
    <div className="space-y-3">
      {fields.map(([key, value]) => (
        <OutputField key={key} name={key} value={value} />
      ))}
    </div>
  );
}

function OutputField({ name, value }: { name: string; value: unknown }) {
  const type = inferType(value);

  return (
    <div className="rounded bg-clay-900/50 border border-clay-700 px-4 py-3">
      <div className="flex items-center justify-between mb-1">
        <span className="text-xs font-mono text-clay-200">{name}</span>
        <span className="text-[11px] text-clay-300">{type}</span>
      </div>
      <FieldValue name={name} value={value} />
    </div>
  );
}

function FieldValue({ name, value }: { name: string; value: unknown }) {
  const [expanded, setExpanded] = useState(false);
  const [showMore, setShowMore] = useState(false);

  if (value === null) {
    return (
      <span className="text-sm text-amber-400 italic inline-flex items-center gap-1">
        <AlertTriangle className="h-3 w-3" />
        null
      </span>
    );
  }

  if (typeof value === "boolean") {
    return (
      <span
        className={cn(
          "text-xs px-2.5 py-1 rounded-full font-medium",
          value
            ? "bg-emerald-500/15 text-emerald-400"
            : "bg-red-500/15 text-red-400"
        )}
      >
        {String(value)}
      </span>
    );
  }

  if (isScoreLike(name, value)) {
    const pct = Math.round((value as number) * 100);
    return (
      <div className="flex items-center gap-2">
        <div className="flex-1 h-2.5 rounded-full bg-clay-800 overflow-hidden">
          <div
            className="h-full rounded-full bg-kiln-teal transition-all"
            style={{ width: `${pct}%` }}
          />
        </div>
        <span className="text-xs font-mono text-clay-300 shrink-0">
          {pct}%
        </span>
      </div>
    );
  }

  if (typeof value === "number") {
    return <span className="text-sm font-mono text-clay-100">{value}</span>;
  }

  if (typeof value === "string") {
    const truncated = value.length > 200 && !showMore;
    return (
      <div>
        <span className="text-sm text-clay-100">
          {truncated ? value.slice(0, 200) + "..." : value}
        </span>
        {value.length > 200 && (
          <button
            onClick={() => setShowMore(!showMore)}
            className="text-xs text-kiln-teal hover:text-kiln-teal-light ml-1"
          >
            {showMore ? "Show less" : "Show more"}
          </button>
        )}
      </div>
    );
  }

  // Arrays and objects — collapsible JSON
  const json = JSON.stringify(value, null, 2);
  return (
    <div>
      <button
        onClick={() => setExpanded(!expanded)}
        className="flex items-center gap-1 text-xs text-clay-300 hover:text-clay-200"
      >
        {expanded ? (
          <ChevronDown className="h-3 w-3" />
        ) : (
          <ChevronRight className="h-3 w-3" />
        )}
        {Array.isArray(value)
          ? `${value.length} items`
          : `${Object.keys(value as object).length} keys`}
      </button>
      {expanded && (
        <pre className="mt-1 text-xs text-clay-300 bg-clay-950 p-3 rounded border border-clay-800 overflow-auto max-h-64 whitespace-pre-wrap">
          {json}
        </pre>
      )}
    </div>
  );
}
