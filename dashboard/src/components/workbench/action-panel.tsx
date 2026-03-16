"use client";

import { motion, AnimatePresence } from "framer-motion";
import { X } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { WorkbenchPhase, StageStatus } from "@/lib/types";
import { SourceActions } from "./source-actions";
import { ResearchActions } from "./research-actions";
import { EnrichActions } from "./enrich-actions";

interface ActionPanelProps {
  phase: WorkbenchPhase | null;
  open: boolean;
  onClose: () => void;
  startPolling: (stage: string, batchId: string, onComplete?: () => void) => void;
  getStageStatus: (stage: string) => StageStatus | null;
  isStageRunning: (stage: string) => boolean;
}

const PHASE_TITLES: Record<WorkbenchPhase, string> = {
  source: "Source",
  research: "Research",
  enrich: "Enrich",
};

export function ActionPanel({
  phase,
  open,
  onClose,
  startPolling,
  getStageStatus,
  isStageRunning,
}: ActionPanelProps) {
  return (
    <AnimatePresence>
      {open && phase && (
        <motion.div
          initial={{ width: 0, opacity: 0 }}
          animate={{ width: 320, opacity: 1 }}
          exit={{ width: 0, opacity: 0 }}
          transition={{ duration: 0.2, ease: "easeInOut" }}
          className="shrink-0 overflow-hidden border-l border-clay-600 bg-clay-800"
        >
          <div className="w-[320px] h-full flex flex-col">
            {/* Panel header */}
            <div className="flex items-center justify-between px-4 py-3 border-b border-clay-600">
              <h3 className="text-sm font-semibold text-clay-100">
                {PHASE_TITLES[phase]}
              </h3>
              <Button
                variant="ghost"
                size="sm"
                onClick={onClose}
                className="h-6 w-6 p-0 text-clay-300 hover:text-clay-100"
              >
                <X className="h-3.5 w-3.5" />
              </Button>
            </div>

            {/* Panel content */}
            <div className="flex-1 overflow-y-auto p-3">
              {phase === "source" && (
                <SourceActions
                  startPolling={startPolling}
                  getStageStatus={getStageStatus}
                  isStageRunning={isStageRunning}
                />
              )}
              {phase === "research" && (
                <ResearchActions
                  startPolling={startPolling}
                  getStageStatus={getStageStatus}
                  isStageRunning={isStageRunning}
                />
              )}
              {phase === "enrich" && (
                <EnrichActions
                  startPolling={startPolling}
                  getStageStatus={getStageStatus}
                  isStageRunning={isStageRunning}
                />
              )}
            </div>
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}
