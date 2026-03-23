"use client";

import { useState } from "react";
import { cn } from "@/lib/utils";
import { Check, Plus, X } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { ProjectPhase } from "@/lib/types";

interface ProjectPhaseTrackerProps {
  phases: ProjectPhase[];
  onTogglePhase: (phaseId: string) => void;
  onAddPhase: (name: string) => void;
  onDeletePhase: (phaseId: string) => void;
}

export function ProjectPhaseTracker({
  phases,
  onTogglePhase,
  onAddPhase,
  onDeletePhase,
}: ProjectPhaseTrackerProps) {
  const [adding, setAdding] = useState(false);
  const [newName, setNewName] = useState("");

  const sorted = [...phases].sort((a, b) => a.order - b.order);

  const handleAdd = () => {
    if (newName.trim()) {
      onAddPhase(newName.trim());
      setNewName("");
      setAdding(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-xs font-medium text-clay-300 uppercase tracking-wider">Phases</h3>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setAdding(!adding)}
          className="h-6 text-[11px] text-clay-400 hover:text-clay-200 hover:bg-clay-700 gap-1"
        >
          <Plus className="h-3 w-3" />
        </Button>
      </div>

      {/* Phase list */}
      {sorted.length === 0 && !adding && (
        <p className="text-xs text-clay-500">No phases defined</p>
      )}

      <div className="space-y-1.5">
        {sorted.map((phase, i) => (
          <div key={phase.id} className="flex items-center gap-2 group">
            {/* Step indicator */}
            <button
              onClick={() => onTogglePhase(phase.id)}
              className={cn(
                "h-6 w-6 rounded-full flex items-center justify-center flex-shrink-0 border transition-all",
                phase.status === "completed"
                  ? "bg-emerald-500/20 border-emerald-500/50 text-emerald-400"
                  : phase.status === "active"
                    ? "bg-kiln-teal/20 border-kiln-teal/50 text-kiln-teal"
                    : "bg-clay-700 border-clay-600 text-clay-500"
              )}
            >
              {phase.status === "completed" ? (
                <Check className="h-3 w-3" />
              ) : (
                <span className="text-[10px] font-medium">{i + 1}</span>
              )}
            </button>

            {/* Name + connector */}
            <span
              className={cn(
                "text-sm flex-1 truncate",
                phase.status === "completed"
                  ? "text-clay-400 line-through"
                  : phase.status === "active"
                    ? "text-clay-100 font-medium"
                    : "text-clay-400"
              )}
            >
              {phase.name}
            </span>

            {/* Delete */}
            <button
              onClick={() => onDeletePhase(phase.id)}
              className="opacity-0 group-hover:opacity-100 text-clay-500 hover:text-red-400 transition-opacity"
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        ))}
      </div>

      {/* Add phase inline */}
      {adding && (
        <div className="flex gap-2">
          <input
            type="text"
            value={newName}
            onChange={(e) => setNewName(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            placeholder="Phase name..."
            className="flex-1 bg-clay-900 border border-clay-600 rounded-md px-2.5 py-1 text-sm text-clay-100 placeholder:text-clay-500 focus:outline-none focus:border-kiln-teal"
            autoFocus
          />
          <Button
            variant="outline"
            size="sm"
            onClick={handleAdd}
            disabled={!newName.trim()}
            className="h-7 border-clay-600 text-clay-300 hover:bg-clay-700"
          >
            Add
          </Button>
        </div>
      )}
    </div>
  );
}
