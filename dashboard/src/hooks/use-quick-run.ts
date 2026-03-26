"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { fetchFunction, executeFunction } from "@/lib/api";
import type { FunctionDefinition } from "@/lib/types";

interface RecentRun {
  funcId: string;
  funcName: string;
  timestamp: number;
  inputSummary: string;
}

const RECENTS_KEY = "kiln_recent_functions";
const MAX_RECENTS = 10;

export function useQuickRun(functionId: string) {
  const [func, setFunc] = useState<FunctionDefinition | null>(null);
  const [inputs, setInputs] = useState<Record<string, string>>({});
  const [result, setResult] = useState<Record<string, unknown> | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const abortRef = useRef<AbortController | null>(null);

  // Load function definition
  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    fetchFunction(functionId)
      .then((f) => {
        if (cancelled) return;
        setFunc(f);
        // Initialize inputs with empty strings
        const initial: Record<string, string> = {};
        for (const inp of f.inputs) {
          initial[inp.name] = "";
        }
        setInputs(initial);
      })
      .catch((e) => {
        if (!cancelled) setError(e instanceof Error ? e.message : "Failed to load function");
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });
    return () => { cancelled = true; };
  }, [functionId]);

  const setInput = useCallback((name: string, value: string) => {
    setInputs((prev) => ({ ...prev, [name]: value }));
  }, []);

  const execute = useCallback(async () => {
    if (!func) return;

    // Validate required inputs
    for (const inp of func.inputs) {
      if (inp.required && !inputs[inp.name]?.trim()) {
        setError(`"${inp.name}" is required`);
        return;
      }
    }

    setRunning(true);
    setError(null);
    setResult(null);

    const controller = new AbortController();
    abortRef.current = controller;

    try {
      // Build data object, only include non-empty values
      const data: Record<string, unknown> = {};
      for (const [key, value] of Object.entries(inputs)) {
        if (value.trim()) {
          // Find the input definition to type-cast
          const inputDef = func.inputs.find((i) => i.name === key);
          if (inputDef?.type === "number") {
            data[key] = Number(value);
          } else if (inputDef?.type === "boolean") {
            data[key] = value === "true";
          } else {
            data[key] = value;
          }
        }
      }

      const res = await executeFunction(func.id, data, { signal: controller.signal });
      setResult(res);

      // Record to recents
      recordRecentRun(func.id, func.name, inputs);
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        setError(e instanceof Error ? e.message : "Execution failed");
      }
    } finally {
      setRunning(false);
      abortRef.current = null;
    }
  }, [func, inputs]);

  const cancel = useCallback(() => {
    abortRef.current?.abort();
    setRunning(false);
  }, []);

  const reset = useCallback(() => {
    setResult(null);
    setError(null);
  }, []);

  return {
    func,
    inputs,
    setInput,
    result,
    running,
    error,
    loading,
    execute,
    cancel,
    reset,
  };
}

function recordRecentRun(funcId: string, funcName: string, inputs: Record<string, string>) {
  try {
    const raw = localStorage.getItem(RECENTS_KEY);
    const recents: RecentRun[] = raw ? JSON.parse(raw) : [];

    // Build a short summary from first non-empty input
    const firstValue = Object.values(inputs).find((v) => v.trim());
    const inputSummary = firstValue
      ? firstValue.length > 50
        ? firstValue.slice(0, 50) + "..."
        : firstValue
      : "No input";

    // Remove existing entry for same function to avoid duplicates
    const filtered = recents.filter((r) => r.funcId !== funcId);
    filtered.unshift({ funcId, funcName, timestamp: Date.now(), inputSummary });

    // Cap at max
    localStorage.setItem(RECENTS_KEY, JSON.stringify(filtered.slice(0, MAX_RECENTS)));
  } catch {
    // localStorage might be full or unavailable
  }
}

export function getRecentRuns(): RecentRun[] {
  try {
    const raw = localStorage.getItem(RECENTS_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}
