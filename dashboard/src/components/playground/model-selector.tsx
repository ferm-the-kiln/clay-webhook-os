"use client";

import { MODELS, type Model } from "@/lib/constants";

export function ModelSelector({
  value,
  onChange,
}: {
  value: Model;
  onChange: (m: Model) => void;
}) {
  return (
    <div>
      <label className="block text-xs text-zinc-500 uppercase tracking-wide mb-1.5">
        Model
      </label>
      <div className="flex gap-2">
        {MODELS.map((m) => (
          <button
            key={m}
            onClick={() => onChange(m)}
            className={`rounded-lg px-4 py-2 text-sm font-medium transition-colors ${
              value === m
                ? "bg-teal-500/20 text-teal-400 border border-teal-500/40"
                : "bg-zinc-800 text-zinc-400 border border-zinc-700 hover:border-zinc-600"
            }`}
          >
            {m}
          </button>
        ))}
      </div>
    </div>
  );
}
