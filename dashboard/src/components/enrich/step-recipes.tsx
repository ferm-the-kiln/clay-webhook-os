"use client";

import { useState, useMemo } from "react";
import { cn } from "@/lib/utils";
import {
  Mail,
  Building2,
  Target,
  Users,
  Layers,
  Linkedin,
  Sparkles,
  ChevronDown,
  Zap,
  Star,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { WorkflowTemplate } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { normalize, SYNONYMS } from "@/lib/csv-utils";

/* ─── Icon map ─────────────────────────────────────────── */

const ICON_MAP: Record<string, LucideIcon> = {
  Mail,
  Building2,
  Target,
  Users,
  Layers,
  Linkedin,
  Sparkles,
};

/* ─── Sample output values for preview ─────────────────── */

const SAMPLE_VALUES: Record<string, string> = {
  email: "alex.rivera@acme.com",
  confidence: "98%",
  summary: "Acme Corp builds enterprise workflow automation...",
  employee_count: "250-500",
  industry: "SaaS / B2B Software",
  fit_score: "82",
  reasoning: "Strong ICP fit — mid-market SaaS, rapid growth signals",
  tier: "A",
  title: "VP of Revenue Operations",
  linkedin_url: "linkedin.com/in/alex-rivera",
  phone: "+1 (407) 555-0142",
  source: "Findymail",
  company_summary: "Acme Corp builds enterprise workflow automation...",
  contact_title: "VP of Revenue Operations",
  company_name: "Acme Corp",
  seniority_level: "VP",
  location: "Orlando, FL",
  headquarters: "San Francisco, CA",
  signals: "Hiring SDRs, Series B, new CRO",
};

/* ─── Recipe combos ────────────────────────────────────── */

interface RecipeCombo {
  id: string;
  name: string;
  description: string;
  icon: LucideIcon;
  recipeIds: string[];
}

const RECIPE_COMBOS: RecipeCombo[] = [
  {
    id: "full-contact-enrichment",
    name: "Full Contact Enrichment",
    description: "Email + LinkedIn + contact details in one go",
    icon: Zap,
    recipeIds: ["find-emails", "find-linkedin", "enrich-contacts"],
  },
  {
    id: "score-and-research",
    name: "Score & Research",
    description: "Research the company then score the lead",
    icon: Star,
    recipeIds: ["research-companies", "score-leads"],
  },
];

/* ─── Smart matching logic ─────────────────────────────── */

function canSatisfyInputs(
  recipe: WorkflowTemplate,
  csvHeaders: string[],
): boolean {
  const normalizedHeaders = csvHeaders.map(normalize);

  const requiredInputs = recipe.expected_inputs.filter(
    (input) => input.required !== false,
  );

  return requiredInputs.every((input) => {
    const inputNorm = normalize(input.name);

    // 1. Exact match
    if (normalizedHeaders.some((h) => h === inputNorm)) return true;

    // 2. Synonym match
    const syns = SYNONYMS[inputNorm] || [];
    if (normalizedHeaders.some((h) => syns.includes(h))) return true;

    // 3. Substring containment
    if (
      normalizedHeaders.some(
        (h) => h.includes(inputNorm) || inputNorm.includes(h),
      )
    )
      return true;

    return false;
  });
}

/* ─── Props ────────────────────────────────────────────── */

interface StepRecipesProps {
  recipes: WorkflowTemplate[];
  selected: Set<string>;
  onToggle: (id: string) => void;
  csvHeaders?: string[];
}

/* ─── Main component ───────────────────────────────────── */

export function StepRecipes({
  recipes,
  selected,
  onToggle,
  csvHeaders,
}: StepRecipesProps) {
  const { recommended, remaining } = useMemo(() => {
    if (!csvHeaders || csvHeaders.length === 0) {
      return { recommended: [] as WorkflowTemplate[], remaining: recipes };
    }

    const rec: WorkflowTemplate[] = [];
    const rest: WorkflowTemplate[] = [];

    for (const recipe of recipes) {
      if (canSatisfyInputs(recipe, csvHeaders)) {
        rec.push(recipe);
      } else {
        rest.push(recipe);
      }
    }

    return { recommended: rec, remaining: rest };
  }, [recipes, csvHeaders]);

  const visibleCombos = useMemo(() => {
    if (recommended.length === 0) return [];
    const recommendedIds = new Set(recommended.map((r) => r.id));
    return RECIPE_COMBOS.filter((combo) =>
      combo.recipeIds.some((id) => recommendedIds.has(id)),
    );
  }, [recommended]);

  const handleComboClick = (combo: RecipeCombo) => {
    const allSelected = combo.recipeIds.every((id) => selected.has(id));
    for (const id of combo.recipeIds) {
      if (allSelected) {
        if (selected.has(id)) onToggle(id);
      } else {
        if (!selected.has(id)) onToggle(id);
      }
    }
  };

  return (
    <div className="space-y-6">
      <div className="text-center space-y-1">
        <h2 className="text-lg font-semibold text-clay-100">
          What do you want to find?
        </h2>
        <p className="text-sm text-clay-400">
          Pick one or more. We&apos;ll handle the rest.
        </p>
      </div>

      {/* Recipe Combos */}
      {visibleCombos.length > 0 && (
        <div className="flex items-center gap-2 overflow-x-auto pb-1">
          {visibleCombos.map((combo) => {
            const allSelected = combo.recipeIds.every((id) =>
              selected.has(id),
            );
            const ComboIcon = combo.icon;

            return (
              <button
                key={combo.id}
                onClick={() => handleComboClick(combo)}
                className={cn(
                  "flex items-center gap-2 px-4 py-2 rounded-full border whitespace-nowrap transition-all duration-150 shrink-0",
                  allSelected
                    ? "border-kiln-teal bg-kiln-teal/10 text-kiln-teal"
                    : "border-clay-600 bg-clay-800/50 text-clay-300 hover:border-clay-500 hover:text-clay-200",
                )}
              >
                <ComboIcon className="h-3.5 w-3.5" />
                <span className="text-xs font-medium">{combo.name}</span>
                <span className="text-[10px] text-clay-500">
                  {combo.recipeIds.length} recipes
                </span>
              </button>
            );
          })}
        </div>
      )}

      {/* Recommended recipes */}
      {recommended.length > 0 && (
        <div className="space-y-2">
          <div className="flex items-center gap-2">
            <div className="text-[10px] text-kiln-teal uppercase tracking-wider font-medium">
              Recommended for your data
            </div>
            <div className="flex-1 h-px bg-clay-700" />
          </div>
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {recommended.map((recipe) => (
              <RecipeCard
                key={recipe.id}
                recipe={recipe}
                isSelected={selected.has(recipe.id)}
                isRecommended
                onToggle={() => onToggle(recipe.id)}
              />
            ))}
          </div>
        </div>
      )}

      {/* All / remaining recipes */}
      {remaining.length > 0 && (
        <div className="space-y-2">
          {recommended.length > 0 && (
            <div className="flex items-center gap-2">
              <div className="text-[10px] text-clay-500 uppercase tracking-wider font-medium">
                All recipes
              </div>
              <div className="flex-1 h-px bg-clay-700" />
            </div>
          )}
          <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
            {remaining.map((recipe) => (
              <RecipeCard
                key={recipe.id}
                recipe={recipe}
                isSelected={selected.has(recipe.id)}
                isRecommended={false}
                onToggle={() => onToggle(recipe.id)}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

/* ─── Recipe card with output preview ──────────────────── */

function RecipeCard({
  recipe,
  isSelected,
  isRecommended,
  onToggle,
}: {
  recipe: WorkflowTemplate;
  isSelected: boolean;
  isRecommended: boolean;
  onToggle: () => void;
}) {
  const [previewOpen, setPreviewOpen] = useState(false);
  const Icon = ICON_MAP[recipe.icon] || Sparkles;

  return (
    <div
      className={cn(
        "relative rounded-lg border transition-all duration-150",
        isSelected
          ? "border-kiln-teal bg-kiln-teal/5 ring-1 ring-kiln-teal/30"
          : isRecommended
            ? "border-kiln-teal/20 bg-clay-800/40 hover:border-kiln-teal/40 hover:bg-clay-800/60"
            : "border-clay-700 bg-clay-800/30 hover:border-clay-600 hover:bg-clay-800/50",
      )}
    >
      <button onClick={onToggle} className="w-full text-left p-4 pb-2">
        <div
          className={cn(
            "absolute top-3 right-3 h-5 w-5 rounded-md border-2 flex items-center justify-center transition-colors",
            isSelected ? "border-kiln-teal bg-kiln-teal" : "border-clay-600",
          )}
        >
          {isSelected && (
            <svg className="h-3 w-3 text-black" viewBox="0 0 12 12" fill="none">
              <path d="M2.5 6L5 8.5L9.5 3.5" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" />
            </svg>
          )}
        </div>

        <div className="flex items-start gap-3 pr-6">
          <div
            className={cn(
              "flex items-center justify-center h-9 w-9 rounded-lg shrink-0",
              isSelected
                ? "bg-kiln-teal/15 text-kiln-teal"
                : isRecommended
                  ? "bg-kiln-teal/10 text-kiln-teal/70"
                  : "bg-clay-700/50 text-clay-400",
            )}
          >
            <Icon className="h-4.5 w-4.5" />
          </div>
          <div className="min-w-0 space-y-1.5">
            <div className="text-sm font-medium text-clay-100">{recipe.name}</div>
            <div className="text-xs text-clay-400 leading-relaxed">{recipe.description}</div>
            <div className="flex flex-wrap gap-1">
              {recipe.produced_outputs.map((o) => (
                <Badge
                  key={o.name}
                  variant="secondary"
                  className="text-[10px] py-0 h-4 bg-clay-700/50 text-clay-300 border-clay-600"
                >
                  {o.name}
                </Badge>
              ))}
            </div>
          </div>
        </div>
      </button>

      {/* Output preview toggle */}
      <button
        onClick={(e) => {
          e.stopPropagation();
          setPreviewOpen((prev) => !prev);
        }}
        className="w-full flex items-center justify-center gap-1 py-1.5 text-[10px] text-clay-500 hover:text-clay-400 transition-colors border-t border-transparent hover:border-clay-700/50"
      >
        <span>Sample output</span>
        <ChevronDown
          className={cn(
            "h-3 w-3 transition-transform duration-200",
            previewOpen && "rotate-180",
          )}
        />
      </button>

      {previewOpen && (
        <div className="px-4 pb-3 border-t border-clay-700/50">
          <div className="pt-2 space-y-1">
            {recipe.produced_outputs.map((output) => {
              const sampleValue =
                SAMPLE_VALUES[output.name] ||
                SAMPLE_VALUES[normalize(output.name)] ||
                "\u2014";
              return (
                <div key={output.name} className="flex items-baseline gap-2 text-[11px]">
                  <span className="font-mono text-clay-500 shrink-0">{output.name}</span>
                  <span className="text-clay-600">:</span>
                  <span className="text-clay-300 truncate">{sampleValue}</span>
                </div>
              );
            })}
          </div>
        </div>
      )}
    </div>
  );
}
