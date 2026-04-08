"use client";

import { useState } from "react";
import { Plus, GripVertical, X, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

interface WaterfallProvider {
  tool: string;
  name: string;
}

interface WaterfallConfigProps {
  providers: WaterfallProvider[];
  onChange: (providers: WaterfallProvider[]) => void;
  availableProviders: { id: string; name: string }[];
}

export function WaterfallConfig({
  providers,
  onChange,
  availableProviders,
}: WaterfallConfigProps) {
  const [addingProvider, setAddingProvider] = useState(false);

  // Filter out already-selected providers
  const remaining = availableProviders.filter(
    (p) => !providers.some((wp) => wp.tool === p.id),
  );

  const moveUp = (idx: number) => {
    if (idx === 0) return;
    const next = [...providers];
    [next[idx - 1], next[idx]] = [next[idx], next[idx - 1]];
    onChange(next);
  };

  const moveDown = (idx: number) => {
    if (idx === providers.length - 1) return;
    const next = [...providers];
    [next[idx], next[idx + 1]] = [next[idx + 1], next[idx]];
    onChange(next);
  };

  const remove = (idx: number) => {
    onChange(providers.filter((_, i) => i !== idx));
  };

  const addProvider = (toolId: string) => {
    const prov = availableProviders.find((p) => p.id === toolId);
    if (prov) {
      onChange([...providers, { tool: prov.id, name: prov.name }]);
    }
    setAddingProvider(false);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center gap-1.5 text-xs text-clay-200">
        <Zap className="w-3 h-3 text-amber-400" />
        Waterfall — tries each provider in order, stops on first success
      </div>

      {/* Provider list */}
      <div className="space-y-1">
        {providers.map((p, idx) => (
          <div
            key={`${p.tool}-${idx}`}
            className="flex items-center gap-2 px-2 py-1.5 rounded bg-clay-700 border border-clay-500 group"
          >
            <GripVertical className="w-3 h-3 text-clay-300 shrink-0" />
            <span className="text-xs text-clay-300 w-4 tabular-nums">
              {idx + 1}.
            </span>
            <span className="text-xs text-clay-100 flex-1 truncate">
              {p.name}
            </span>
            <button
              onClick={() => remove(idx)}
              className="opacity-0 group-hover:opacity-100 p-0.5 rounded hover:bg-clay-500 text-clay-300"
            >
              <X className="w-3 h-3" />
            </button>
          </div>
        ))}
      </div>

      {/* Add fallback */}
      {addingProvider ? (
        <Select onValueChange={addProvider}>
          <SelectTrigger className="h-8 bg-clay-900 border-clay-500 text-xs text-white">
            <SelectValue placeholder="Select provider..." />
          </SelectTrigger>
          <SelectContent className="bg-clay-900 border-clay-500">
            {remaining.map((p) => (
              <SelectItem key={p.id} value={p.id} className="text-xs text-clay-100">
                {p.name}
              </SelectItem>
            ))}
            {remaining.length === 0 && (
              <div className="px-2 py-1.5 text-xs text-clay-300">No more providers</div>
            )}
          </SelectContent>
        </Select>
      ) : (
        <Button
          variant="ghost"
          size="sm"
          className="w-full text-xs text-clay-300 hover:text-clay-100 h-7"
          onClick={() => setAddingProvider(true)}
          disabled={remaining.length === 0}
        >
          <Plus className="w-3 h-3 mr-1" />
          Add fallback
        </Button>
      )}
    </div>
  );
}
