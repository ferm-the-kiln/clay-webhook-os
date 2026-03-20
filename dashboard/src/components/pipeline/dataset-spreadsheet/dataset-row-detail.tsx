"use client";

import type { DatasetRow } from "@/lib/types";

export function DatasetRowDetail({ data }: { data: DatasetRow }) {
  const entries = Object.entries(data).filter(([key]) => key !== "_row_id");

  return (
    <div className="bg-clay-950 border-b border-clay-500 px-6 py-4">
      <p className="text-xs text-clay-200 uppercase tracking-wider mb-3">
        Row Details
      </p>
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-2">
        {entries.map(([key, val]) => (
          <div key={key} className="flex gap-2 text-xs">
            <span className="text-clay-200 font-[family-name:var(--font-mono)] shrink-0">
              {key}:
            </span>
            <span className="text-clay-300 truncate">
              {val === null || val === undefined
                ? "\u2014"
                : typeof val === "object"
                  ? JSON.stringify(val)
                  : String(val)}
            </span>
          </div>
        ))}
        {entries.length === 0 && (
          <p className="text-xs text-clay-300">No data</p>
        )}
      </div>
      <div className="mt-3 pt-2 border-t border-clay-700">
        <span className="text-[10px] text-clay-300 font-[family-name:var(--font-mono)]">
          ID: {data._row_id}
        </span>
      </div>
    </div>
  );
}
