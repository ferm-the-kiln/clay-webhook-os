"use client";

import { Loader2, Check, X } from "lucide-react";
import { cn } from "@/lib/utils";
import { PREP_SKILL_LABELS, type PrepSkillKey, type SkillResultState } from "@/lib/prep-types";

interface PrepSkillStatusProps {
  skillStates: Record<PrepSkillKey, SkillResultState>;
}

export function PrepSkillStatus({ skillStates }: PrepSkillStatusProps) {
  const skills = Object.entries(skillStates) as [PrepSkillKey, SkillResultState][];
  const completed = skills.filter(([, s]) => s.status === "complete").length;
  const total = skills.length;

  return (
    <div className="flex flex-col items-center gap-3">
      <div className="flex items-center gap-2 flex-wrap justify-center">
        {skills.map(([key, state]) => (
          <div
            key={key}
            className={cn(
              "flex items-center gap-1.5 px-2.5 py-1 rounded-full text-[11px] font-medium border transition-all duration-300",
              state.status === "pending" &&
                "border-clay-600 text-clay-300 bg-clay-800",
              state.status === "running" &&
                "border-kiln-teal/40 text-kiln-teal bg-kiln-teal/5",
              state.status === "complete" &&
                "border-green-500/30 text-green-400 bg-green-500/5",
              state.status === "error" &&
                "border-red-500/30 text-red-400 bg-red-500/5"
            )}
          >
            {state.status === "running" && (
              <Loader2 className="h-3 w-3 animate-spin" />
            )}
            {state.status === "complete" && <Check className="h-3 w-3" />}
            {state.status === "error" && <X className="h-3 w-3" />}
            {PREP_SKILL_LABELS[key]}
          </div>
        ))}
      </div>
      {total > 0 && (
        <span className="text-[10px] text-clay-300">
          {completed === total
            ? "All skills complete"
            : `${completed} of ${total} complete`}
        </span>
      )}
    </div>
  );
}
