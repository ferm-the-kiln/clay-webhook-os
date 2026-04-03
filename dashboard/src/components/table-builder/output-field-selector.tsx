"use client";

import { Check } from "lucide-react";

interface ToolOutput {
  key: string;
  type: string;
  description?: string;
}

interface OutputFieldSelectorProps {
  outputs: ToolOutput[];
  selectedOutputs: string[];
  onToggle: (key: string) => void;
}

const TYPE_BADGES: Record<string, string> = {
  string: "bg-blue-500/10 text-blue-400",
  number: "bg-emerald-500/10 text-emerald-400",
  boolean: "bg-amber-500/10 text-amber-400",
  json: "bg-purple-500/10 text-purple-400",
  url: "bg-blue-500/10 text-blue-400",
  email: "bg-teal-500/10 text-teal-400",
};

/**
 * Checklist of tool output fields. Users check which outputs
 * they want as separate columns. The first checked output becomes
 * the primary column's output_key; additional ones create child columns.
 */
export function OutputFieldSelector({
  outputs,
  selectedOutputs,
  onToggle,
}: OutputFieldSelectorProps) {
  if (outputs.length <= 1) return null;

  return (
    <div className="space-y-1.5">
      <div className="flex items-center justify-between">
        <label className="text-zinc-400 text-xs">Output Fields</label>
        <span className="text-[10px] text-zinc-600">
          {selectedOutputs.length} of {outputs.length} selected
        </span>
      </div>
      <p className="text-[11px] text-zinc-600 -mt-1">
        Each checked field becomes its own column
      </p>
      <div className="rounded-md border border-zinc-800 divide-y divide-zinc-800/50 overflow-hidden">
        {outputs.map((out, i) => {
          const isSelected = selectedOutputs.includes(out.key);
          const isPrimary = selectedOutputs[0] === out.key;
          const badgeColor = TYPE_BADGES[out.type] || TYPE_BADGES.string;

          return (
            <button
              key={out.key}
              onClick={() => onToggle(out.key)}
              className={`w-full flex items-center gap-2.5 px-3 py-2 text-left transition-colors ${
                isSelected
                  ? "bg-zinc-800/50 text-zinc-200"
                  : "text-zinc-500 hover:bg-zinc-900 hover:text-zinc-400"
              }`}
            >
              {/* Checkbox */}
              <div
                className={`w-4 h-4 rounded border flex items-center justify-center shrink-0 transition-colors ${
                  isSelected
                    ? "bg-kiln-teal/20 border-kiln-teal text-kiln-teal"
                    : "border-zinc-600"
                }`}
              >
                {isSelected && <Check className="w-3 h-3" />}
              </div>

              {/* Field name + type */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  <span className="text-xs font-medium truncate">{out.key}</span>
                  <span
                    className={`px-1.5 py-0.5 rounded text-[10px] font-medium shrink-0 ${badgeColor}`}
                  >
                    {out.type}
                  </span>
                  {isPrimary && (
                    <span className="px-1.5 py-0.5 rounded text-[10px] font-medium bg-kiln-teal/10 text-kiln-teal shrink-0">
                      primary
                    </span>
                  )}
                </div>
                {out.description && (
                  <p className="text-[11px] text-zinc-600 truncate mt-0.5">
                    {out.description}
                  </p>
                )}
              </div>
            </button>
          );
        })}
      </div>
    </div>
  );
}
