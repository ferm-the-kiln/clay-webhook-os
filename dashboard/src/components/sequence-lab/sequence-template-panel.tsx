"use client";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { GitFork, Cpu } from "lucide-react";
import {
  SEQUENCE_LAB_TEMPLATES,
  SEQUENCE_TYPE_COLORS,
  SEQUENCE_TYPES,
  type SequenceType,
} from "@/lib/sequence-lab-constants";
import type { VariantDef } from "@/lib/types";
import type { Model } from "@/lib/constants";
import { MODELS } from "@/lib/constants";

export function SequenceTemplatePanel({
  selectedTemplateId,
  onSelectTemplate,
  selectedModel,
  onSelectModel,
  variants,
  selectedVariant,
  onSelectVariant,
  onFork,
  dataJson,
  onDataChange,
}: {
  selectedTemplateId: string | null;
  onSelectTemplate: (id: string) => void;
  selectedModel: Model;
  onSelectModel: (m: Model) => void;
  variants: VariantDef[];
  selectedVariant: string | null;
  onSelectVariant: (id: string | null) => void;
  onFork: () => void;
  dataJson: string;
  onDataChange: (v: string) => void;
}) {
  // Quick-toggle sequence type in the data JSON
  const handleSequenceType = (type: SequenceType) => {
    try {
      const parsed = JSON.parse(dataJson);
      parsed.sequence_type = type;
      onDataChange(JSON.stringify(parsed, null, 2));
    } catch {
      // invalid JSON — ignore
    }
  };

  // Detect current sequence_type from data
  let currentType: SequenceType | null = null;
  try {
    const parsed = JSON.parse(dataJson);
    if (SEQUENCE_TYPES.includes(parsed.sequence_type)) {
      currentType = parsed.sequence_type as SequenceType;
    }
  } catch {
    // ignore
  }

  return (
    <div className="flex flex-col h-full overflow-y-auto p-3 space-y-5">
      {/* ── Templates ── */}
      <div>
        <h3 className="text-[11px] font-semibold text-clay-300 uppercase tracking-[0.1em] mb-2">
          Templates
        </h3>
        <div className="space-y-1.5">
          {SEQUENCE_LAB_TEMPLATES.map((tpl) => {
            const active = tpl.id === selectedTemplateId;
            const color =
              SEQUENCE_TYPE_COLORS[tpl.sequenceType] ?? "bg-clay-500/15 text-clay-300";
            return (
              <button
                key={tpl.id}
                onClick={() => onSelectTemplate(tpl.id)}
                className={cn(
                  "w-full text-left rounded-lg px-3 py-2.5 transition-all duration-150 border",
                  active
                    ? "border-kiln-teal/40 bg-kiln-teal/5"
                    : "border-transparent hover:bg-clay-700/50"
                )}
              >
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-sm font-medium text-clay-100 truncate">
                    {tpl.name}
                  </span>
                  <span
                    className={cn(
                      "text-[10px] px-1.5 py-0.5 rounded-full font-medium shrink-0",
                      color
                    )}
                  >
                    {tpl.sequenceType}
                  </span>
                </div>
                <p className="text-xs text-clay-300 line-clamp-1">
                  {tpl.data.company_name as string} &middot; {tpl.data.title as string}
                </p>
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Sequence Type Toggle ── */}
      <div>
        <h3 className="text-[11px] font-semibold text-clay-300 uppercase tracking-[0.1em] mb-2">
          Sequence Type
        </h3>
        <div className="flex gap-1">
          {SEQUENCE_TYPES.map((type) => (
            <button
              key={type}
              onClick={() => handleSequenceType(type)}
              className={cn(
                "flex-1 text-[10px] py-1.5 rounded-md transition-colors font-medium",
                currentType === type
                  ? cn(SEQUENCE_TYPE_COLORS[type], "border border-current/20")
                  : "text-clay-300 hover:text-clay-200 hover:bg-clay-700/50 border border-transparent"
              )}
            >
              {type}
            </button>
          ))}
        </div>
      </div>

      {/* ── Skill Variants ── */}
      <div>
        <h3 className="text-[11px] font-semibold text-clay-300 uppercase tracking-[0.1em] mb-2">
          Skill
        </h3>
        <p className="text-xs text-clay-300 mb-2">sequence-writer</p>

        {variants.length > 0 && (
          <div className="space-y-1">
            <button
              onClick={() => onSelectVariant(null)}
              className={cn(
                "w-full text-left text-xs px-2.5 py-1.5 rounded-md transition-colors",
                selectedVariant === null
                  ? "bg-kiln-teal/10 text-kiln-teal"
                  : "text-clay-300 hover:text-clay-200 hover:bg-clay-700/50"
              )}
            >
              Default (production)
            </button>
            {variants.map((v) => (
              <button
                key={v.id}
                onClick={() => onSelectVariant(v.id)}
                className={cn(
                  "w-full text-left text-xs px-2.5 py-1.5 rounded-md transition-colors truncate",
                  selectedVariant === v.id
                    ? "bg-kiln-teal/10 text-kiln-teal"
                    : "text-clay-300 hover:text-clay-200 hover:bg-clay-700/50"
                )}
              >
                {v.label}
              </button>
            ))}
          </div>
        )}

        <Button
          variant="ghost"
          size="sm"
          onClick={onFork}
          className="mt-2 w-full text-xs text-clay-300 hover:text-kiln-teal"
        >
          <GitFork className="h-3.5 w-3.5 mr-1.5" />
          Fork Skill
        </Button>
      </div>

      {/* ── Model Selector ── */}
      <div>
        <h3 className="text-[11px] font-semibold text-clay-300 uppercase tracking-[0.1em] mb-2">
          Model
        </h3>
        <div className="flex gap-1">
          {MODELS.map((m) => (
            <button
              key={m}
              onClick={() => onSelectModel(m)}
              className={cn(
                "flex-1 text-xs py-1.5 rounded-md transition-colors font-medium flex items-center justify-center gap-1",
                selectedModel === m
                  ? "bg-kiln-teal/15 text-kiln-teal border border-kiln-teal/30"
                  : "text-clay-300 hover:text-clay-200 hover:bg-clay-700/50 border border-transparent"
              )}
            >
              <Cpu className="h-3 w-3" />
              {m}
            </button>
          ))}
        </div>
      </div>
    </div>
  );
}
