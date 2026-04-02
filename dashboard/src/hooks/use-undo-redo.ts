"use client";

import { useState, useCallback, useEffect, useRef } from "react";

interface UndoAction {
  type: string;
  description: string;
  undo: () => void | Promise<void>;
  redo: () => void | Promise<void>;
}

const MAX_STACK = 20;

export function useUndoRedo() {
  const undoStack = useRef<UndoAction[]>([]);
  const redoStack = useRef<UndoAction[]>([]);
  const [canUndo, setCanUndo] = useState(false);
  const [canRedo, setCanRedo] = useState(false);

  const updateState = useCallback(() => {
    setCanUndo(undoStack.current.length > 0);
    setCanRedo(redoStack.current.length > 0);
  }, []);

  const pushAction = useCallback(
    (action: UndoAction) => {
      undoStack.current.push(action);
      if (undoStack.current.length > MAX_STACK) {
        undoStack.current.shift();
      }
      redoStack.current = []; // Clear redo on new action
      updateState();
    },
    [updateState],
  );

  const undo = useCallback(async () => {
    const action = undoStack.current.pop();
    if (!action) return;
    await action.undo();
    redoStack.current.push(action);
    updateState();
  }, [updateState]);

  const redo = useCallback(async () => {
    const action = redoStack.current.pop();
    if (!action) return;
    await action.redo();
    undoStack.current.push(action);
    updateState();
  }, [updateState]);

  // Keyboard shortcuts
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      const meta = e.metaKey || e.ctrlKey;
      if (!meta) return;

      if (e.key === "z" && !e.shiftKey) {
        e.preventDefault();
        undo();
      } else if ((e.key === "z" && e.shiftKey) || e.key === "y") {
        e.preventDefault();
        redo();
      }
    };
    window.addEventListener("keydown", handler);
    return () => window.removeEventListener("keydown", handler);
  }, [undo, redo]);

  return { pushAction, undo, redo, canUndo, canRedo };
}
