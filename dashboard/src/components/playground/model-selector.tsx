"use client";

import { MODELS, type Model } from "@/lib/constants";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";

export function ModelSelector({
  value,
  onChange,
}: {
  value: Model;
  onChange: (m: Model) => void;
}) {
  return (
    <div>
      <label className="block text-xs text-clay-500 uppercase tracking-wide mb-1.5 font-[family-name:var(--font-sans)]">
        Model
      </label>
      <div className="flex gap-2">
        {MODELS.map((m) => (
          <Button
            key={m}
            variant="outline"
            size="sm"
            onClick={() => onChange(m)}
            className={cn(
              "transition-all duration-200",
              value === m
                ? "bg-kiln-teal/15 text-kiln-teal border-kiln-teal/40 hover:bg-kiln-teal/20 hover:text-kiln-teal"
                : "bg-clay-900 text-clay-400 border-clay-700 hover:border-clay-600 hover:text-clay-200"
            )}
          >
            {m}
          </Button>
        ))}
      </div>
    </div>
  );
}
