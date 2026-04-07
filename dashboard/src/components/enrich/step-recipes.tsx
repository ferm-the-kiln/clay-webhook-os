"use client";

import { cn } from "@/lib/utils";
import {
  Mail,
  Building2,
  Target,
  Users,
  Layers,
  Linkedin,
  Sparkles,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import type { WorkflowTemplate } from "@/lib/types";
import { Badge } from "@/components/ui/badge";

const ICON_MAP: Record<string, LucideIcon> = {
  Mail,
  Building2,
  Target,
  Users,
  Layers,
  Linkedin,
  Sparkles,
};

interface StepRecipesProps {
  recipes: WorkflowTemplate[];
  selected: Set<string>;
  onToggle: (id: string) => void;
}

export function StepRecipes({ recipes, selected, onToggle }: StepRecipesProps) {
  return (
    <div className="space-y-6">
      <div className="text-center space-y-1">
        <h2 className="text-lg font-semibold text-clay-100">What do you want to find?</h2>
        <p className="text-sm text-clay-400">
          Pick one or more. We'll handle the rest.
        </p>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
        {recipes.map((recipe) => {
          const Icon = ICON_MAP[recipe.icon] || Sparkles;
          const isSelected = selected.has(recipe.id);

          return (
            <button
              key={recipe.id}
              onClick={() => onToggle(recipe.id)}
              className={cn(
                "relative text-left rounded-lg border p-4 transition-all duration-150",
                isSelected
                  ? "border-kiln-teal bg-kiln-teal/5 ring-1 ring-kiln-teal/30"
                  : "border-clay-700 bg-clay-800/30 hover:border-clay-600 hover:bg-clay-800/50",
              )}
            >
              {/* Checkbox indicator */}
              <div
                className={cn(
                  "absolute top-3 right-3 h-5 w-5 rounded-md border-2 flex items-center justify-center transition-colors",
                  isSelected
                    ? "border-kiln-teal bg-kiln-teal"
                    : "border-clay-600",
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
                      : "bg-clay-700/50 text-clay-400",
                  )}
                >
                  <Icon className="h-4.5 w-4.5" />
                </div>
                <div className="min-w-0 space-y-1.5">
                  <div className="text-sm font-medium text-clay-100">
                    {recipe.name}
                  </div>
                  <div className="text-xs text-clay-400 leading-relaxed">
                    {recipe.description}
                  </div>
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
          );
        })}
      </div>
    </div>
  );
}
