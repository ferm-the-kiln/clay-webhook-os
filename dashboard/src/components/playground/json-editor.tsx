"use client";

import { useState, useEffect } from "react";

export function JsonEditor({
  value,
  onChange,
}: {
  value: string;
  onChange: (v: string) => void;
}) {
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      JSON.parse(value);
      setError(null);
    } catch (e) {
      setError((e as Error).message);
    }
  }, [value]);

  return (
    <div>
      <div className="flex items-center justify-between mb-1.5">
        <label className="text-xs text-zinc-500 uppercase tracking-wide">
          Data (JSON)
        </label>
        {error && (
          <span className="text-xs text-red-400">Invalid JSON</span>
        )}
      </div>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        rows={14}
        spellCheck={false}
        className={`w-full rounded-lg border bg-zinc-800 px-3 py-2 font-mono text-sm text-zinc-100 focus:outline-none resize-none ${
          error ? "border-red-500/50" : "border-zinc-700 focus:border-teal-500"
        }`}
      />
    </div>
  );
}
