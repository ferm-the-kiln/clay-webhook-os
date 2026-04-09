"use client";

import { useState, useCallback, useRef } from "react";
import { getLocalRunnerStatus } from "@/lib/api";

export function useRunnerGate() {
  const [modalOpen, setModalOpen] = useState(false);
  const pendingAction = useRef<(() => void) | null>(null);

  const guardedRun = useCallback(async (action: () => void) => {
    try {
      const status = await getLocalRunnerStatus();
      if (status.connected) {
        action();
        return;
      }
    } catch {
      // Runner check failed — show modal
    }
    pendingAction.current = action;
    setModalOpen(true);
  }, []);

  const onConnected = useCallback(() => {
    setModalOpen(false);
    const action = pendingAction.current;
    pendingAction.current = null;
    if (action) action();
  }, []);

  const onOpenChange = useCallback((open: boolean) => {
    setModalOpen(open);
    if (!open) pendingAction.current = null;
  }, []);

  return {
    guardedRun,
    modalProps: { open: modalOpen, onOpenChange, onConnected },
  };
}
