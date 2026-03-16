"use client";

import { useState, useCallback, useEffect, useRef } from "react";
import type { WorkbenchPhase, StageStatus } from "@/lib/types";
import { fetchStageStatus } from "@/lib/api";

interface StagePoll {
  batchId: string;
  stage: string;
  status: StageStatus | null;
}

export function useWorkbench() {
  const [activePhase, setActivePhase] = useState<WorkbenchPhase | null>(null);
  const [panelOpen, setPanelOpen] = useState(false);
  const [activeStages, setActiveStages] = useState<Map<string, StagePoll>>(new Map());
  const intervalsRef = useRef<Map<string, ReturnType<typeof setInterval>>>(new Map());

  // Read phase from URL hash on mount
  useEffect(() => {
    const hash = window.location.hash.slice(1) as WorkbenchPhase;
    if (hash === "source" || hash === "research" || hash === "enrich") {
      setActivePhase(hash);
      setPanelOpen(true);
    }
  }, []);

  // Sync phase to URL hash
  useEffect(() => {
    if (activePhase && panelOpen) {
      window.location.hash = activePhase;
    } else if (!panelOpen) {
      history.replaceState(null, "", window.location.pathname);
    }
  }, [activePhase, panelOpen]);

  const togglePhase = useCallback((phase: WorkbenchPhase) => {
    if (activePhase === phase && panelOpen) {
      setPanelOpen(false);
    } else {
      setActivePhase(phase);
      setPanelOpen(true);
    }
  }, [activePhase, panelOpen]);

  const closePanel = useCallback(() => {
    setPanelOpen(false);
  }, []);

  // Start polling for a stage batch
  const startStagePolling = useCallback(
    (datasetId: string, stage: string, batchId: string, onComplete?: () => void) => {
      // Clear any existing poll for this stage
      const existingInterval = intervalsRef.current.get(stage);
      if (existingInterval) clearInterval(existingInterval);

      setActiveStages((prev) => {
        const next = new Map(prev);
        next.set(stage, { batchId, stage, status: null });
        return next;
      });

      const poll = async () => {
        try {
          const s = await fetchStageStatus(datasetId, batchId);
          setActiveStages((prev) => {
            const next = new Map(prev);
            next.set(stage, { batchId, stage, status: s });
            return next;
          });
          if (s.status === "completed" || s.status === "failed") {
            const interval = intervalsRef.current.get(stage);
            if (interval) {
              clearInterval(interval);
              intervalsRef.current.delete(stage);
            }
            onComplete?.();
          }
        } catch {
          // Ignore poll errors
        }
      };

      poll();
      const intervalId = setInterval(poll, 1500);
      intervalsRef.current.set(stage, intervalId);
    },
    []
  );

  const getStageStatus = useCallback(
    (stage: string): StageStatus | null => {
      return activeStages.get(stage)?.status ?? null;
    },
    [activeStages]
  );

  const isStageRunning = useCallback(
    (stage: string): boolean => {
      const s = activeStages.get(stage)?.status;
      return s?.status === "running";
    },
    [activeStages]
  );

  // Cleanup intervals on unmount
  useEffect(() => {
    return () => {
      for (const interval of intervalsRef.current.values()) {
        clearInterval(interval);
      }
    };
  }, []);

  return {
    activePhase,
    panelOpen,
    togglePhase,
    closePanel,
    startStagePolling,
    getStageStatus,
    isStageRunning,
    activeStages,
  };
}
