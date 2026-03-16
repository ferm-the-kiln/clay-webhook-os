"use client";

import { cn } from "@/lib/utils";
import { UserSearch, Search, Mail, Check } from "lucide-react";
import type { WorkbenchPhase, StageStatus } from "@/lib/types";

interface PhaseConfig {
  id: WorkbenchPhase;
  label: string;
  icon: React.ElementType;
  stages: string[];
}

const PHASES: PhaseConfig[] = [
  { id: "source", label: "Source", icon: UserSearch, stages: ["import"] },
  { id: "research", label: "Research", icon: Search, stages: ["company-research", "people-research", "classify"] },
  { id: "enrich", label: "Enrich", icon: Mail, stages: ["find-email", "verify-email"] },
];

interface PhaseStepperProps {
  activePhase: WorkbenchPhase | null;
  panelOpen: boolean;
  onPhaseClick: (phase: WorkbenchPhase) => void;
  completedStages: string[];
  getStageStatus: (stage: string) => StageStatus | null;
}

export function PhaseStepper({
  activePhase,
  panelOpen,
  onPhaseClick,
  completedStages,
  getStageStatus,
}: PhaseStepperProps) {
  const getPhaseState = (phase: PhaseConfig): "done" | "running" | "pending" => {
    // Check if any stage in this phase is currently running
    for (const stage of phase.stages) {
      const status = getStageStatus(stage);
      if (status?.status === "running") return "running";
    }
    // Check if all stages in this phase are completed
    const anyCompleted = phase.stages.some((s) => completedStages.includes(s));
    if (anyCompleted) return "done";
    return "pending";
  };

  return (
    <div className="flex items-center gap-1 px-4 py-3 border-b border-clay-600 bg-clay-800/50">
      {PHASES.map((phase, idx) => {
        const state = getPhaseState(phase);
        const isActive = activePhase === phase.id && panelOpen;

        return (
          <div key={phase.id} className="flex items-center">
            {idx > 0 && (
              <div
                className={cn(
                  "w-8 h-px mx-1",
                  state === "done" || (idx <= PHASES.findIndex((p) => p.id === activePhase))
                    ? "bg-kiln-teal/50"
                    : "bg-clay-600"
                )}
              />
            )}
            <button
              onClick={() => onPhaseClick(phase.id)}
              className={cn(
                "flex items-center gap-2 px-3 py-1.5 rounded-lg text-sm transition-all duration-150",
                isActive
                  ? "bg-kiln-teal/15 text-kiln-teal ring-1 ring-kiln-teal/30"
                  : state === "done"
                    ? "text-kiln-teal hover:bg-kiln-teal/10"
                    : state === "running"
                      ? "text-kiln-teal hover:bg-kiln-teal/10"
                      : "text-clay-300 hover:bg-clay-700 hover:text-clay-100"
              )}
            >
              {/* Step number / status indicator */}
              <span
                className={cn(
                  "flex items-center justify-center h-5 w-5 rounded-full text-[10px] font-bold shrink-0",
                  state === "done"
                    ? "bg-kiln-teal/20 text-kiln-teal"
                    : state === "running"
                      ? "bg-kiln-teal/20 text-kiln-teal"
                      : "bg-clay-600 text-clay-300"
                )}
              >
                {state === "done" ? (
                  <Check className="h-3 w-3" />
                ) : state === "running" ? (
                  <span className="h-2 w-2 rounded-full bg-kiln-teal animate-pulse" />
                ) : (
                  idx + 1
                )}
              </span>

              <phase.icon className="h-3.5 w-3.5 hidden sm:block" />
              <span className="font-medium">{phase.label}</span>
            </button>
          </div>
        );
      })}
    </div>
  );
}

export { PHASES };
export type { PhaseConfig };
