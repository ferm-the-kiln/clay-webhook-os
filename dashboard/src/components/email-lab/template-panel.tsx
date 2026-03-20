"use client";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { GitFork, Cpu, X, Sparkles } from "lucide-react";
import {
  EMAIL_LAB_TEMPLATES,
  EMAIL_LAB_SKILLS,
  type EmailLabSkill,
  type CustomEmailLabTemplate,
} from "@/lib/email-lab-constants";
import type { VariantDef } from "@/lib/types";
import type { Model } from "@/lib/constants";
import { MODELS } from "@/lib/constants";

const SIGNAL_COLORS: Record<string, string> = {
  expansion: "bg-emerald-500/15 text-emerald-400",
  funding: "bg-amber-500/15 text-amber-400",
  technology: "bg-blue-500/15 text-blue-400",
  leadership: "bg-purple-500/15 text-purple-400",
  competitive: "bg-red-500/15 text-red-400",
};

// Signal type → best template mapping (Rec #10)
const SIGNAL_TO_TEMPLATE: Record<string, string> = {
  expansion: "company-expansion",
  funding: "funding-round",
  technology: "tech-stack-change",
  leadership: "leadership-change",
  competitive: "competitor-displacement",
};

export function TemplatePanel({
  selectedTemplateId,
  onSelectTemplate,
  selectedSkill,
  onSelectSkill,
  selectedModel,
  onSelectModel,
  variants,
  selectedVariant,
  onSelectVariant,
  onFork,
  customTemplates,
  onDeleteCustomTemplate,
  dataJson,
}: {
  selectedTemplateId: string | null;
  onSelectTemplate: (id: string) => void;
  selectedSkill: EmailLabSkill;
  onSelectSkill: (s: EmailLabSkill) => void;
  selectedModel: Model;
  onSelectModel: (m: Model) => void;
  variants: VariantDef[];
  selectedVariant: string | null;
  onSelectVariant: (id: string | null) => void;
  onFork: () => void;
  customTemplates: CustomEmailLabTemplate[];
  onDeleteCustomTemplate: (id: string) => void;
  dataJson?: string;
}) {
  // Detect signal type from data for smart suggestions (Rec #10)
  let suggestedTemplateId: string | null = null;
  if (dataJson) {
    try {
      const parsed = JSON.parse(dataJson);
      const signalType = parsed.signal_type as string;
      if (signalType && SIGNAL_TO_TEMPLATE[signalType]) {
        suggestedTemplateId = SIGNAL_TO_TEMPLATE[signalType];
      }
    } catch {
      // ignore
    }
  }
  return (
    <div className="flex flex-col h-full overflow-y-auto p-3 space-y-5">
      {/* ── Templates ── */}
      <div>
        <h3 className="text-[11px] font-semibold text-clay-300 uppercase tracking-[0.1em] mb-2">
          Templates
        </h3>
        <div className="space-y-1.5">
          {EMAIL_LAB_TEMPLATES.map((tpl) => {
            const active = tpl.id === selectedTemplateId;
            const isSuggested = suggestedTemplateId === tpl.id && !active;
            const color = SIGNAL_COLORS[tpl.signalType] ?? "bg-clay-500/15 text-clay-300";
            return (
              <button
                key={tpl.id}
                onClick={() => onSelectTemplate(tpl.id)}
                className={cn(
                  "w-full text-left rounded-lg px-3 py-2.5 transition-all duration-150 border",
                  active
                    ? "border-kiln-teal/40 bg-kiln-teal/5"
                    : isSuggested
                      ? "border-kiln-teal/20 bg-kiln-teal/5 ring-1 ring-kiln-teal/10"
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
                    {tpl.signalType}
                  </span>
                  {isSuggested && (
                    <Sparkles className="h-3 w-3 text-kiln-teal shrink-0" />
                  )}
                </div>
                <p className="text-xs text-clay-300 line-clamp-1">
                  {tpl.data.company_name as string} &middot; {tpl.data.title as string}
                </p>
                {isSuggested && (
                  <p className="text-[9px] text-kiln-teal/70 mt-0.5">
                    Best match for your signal type
                  </p>
                )}
              </button>
            );
          })}
        </div>
      </div>

      {/* ── Custom/Saved Templates (Feature 4) ── */}
      {customTemplates.length > 0 && (
        <div>
          <h3 className="text-[11px] font-semibold text-clay-300 uppercase tracking-[0.1em] mb-2">
            Saved
          </h3>
          <div className="space-y-1.5">
            {customTemplates.map((tpl) => {
              const active = tpl.id === selectedTemplateId;
              return (
                <div key={tpl.id} className="relative group">
                  <button
                    onClick={() => onSelectTemplate(tpl.id)}
                    className={cn(
                      "w-full text-left rounded-lg px-3 py-2.5 transition-all duration-150 border",
                      active
                        ? "border-kiln-teal/40 bg-kiln-teal/5"
                        : "border-transparent hover:bg-clay-700/50"
                    )}
                  >
                    <span className="text-sm font-medium text-clay-100 truncate block">
                      {tpl.name}
                    </span>
                    <p className="text-xs text-clay-300 line-clamp-1">
                      {tpl.description}
                    </p>
                  </button>
                  <button
                    onClick={(e) => {
                      e.stopPropagation();
                      onDeleteCustomTemplate(tpl.id);
                    }}
                    className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 h-5 w-5 flex items-center justify-center rounded text-clay-300 hover:text-red-400 transition-all"
                  >
                    <X className="h-3 w-3" />
                  </button>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* ── Skill Selector ── */}
      <div>
        <h3 className="text-[11px] font-semibold text-clay-300 uppercase tracking-[0.1em] mb-2">
          Skill
        </h3>
        <Select value={selectedSkill} onValueChange={(v) => onSelectSkill(v as EmailLabSkill)}>
          <SelectTrigger className="w-full">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            {EMAIL_LAB_SKILLS.map((s) => (
              <SelectItem key={s.value} value={s.value}>
                {s.label}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>

        {/* Variants */}
        {variants.length > 0 && (
          <div className="mt-2 space-y-1">
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
