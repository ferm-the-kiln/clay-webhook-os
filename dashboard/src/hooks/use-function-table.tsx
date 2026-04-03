"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import { useRouter } from "next/navigation";
import { toast } from "sonner";
import type { FunctionDefinition, TableDefinition, TableColumn } from "@/lib/types";
import {
  fetchFunction,
  updateFunction,
  deleteFunction as deleteFunctionApi,
  duplicateFunction as duplicateFunctionApi,
  getOrCreateFunctionTable,
} from "@/lib/api";
import { useTableBuilder, type UseTableBuilderReturn } from "./use-table-builder";

export interface UseFunctionTableReturn extends UseTableBuilderReturn {
  /** The underlying function definition */
  func: FunctionDefinition | null;
  funcLoading: boolean;

  /** Sync table columns back to function steps */
  syncColumnsToFunction: () => Promise<void>;

  /** Function metadata operations */
  updateFunctionMeta: (fields: {
    name?: string;
    description?: string;
    folder?: string;
  }) => Promise<void>;
  deleteFn: () => Promise<void>;
  duplicateFn: () => Promise<void>;

  /** Settings panel */
  settingsOpen: boolean;
  setSettingsOpen: (open: boolean) => void;
}

/**
 * Bridge hook that wraps useTableBuilder with function-aware logic.
 * Each function gets a "shadow table" for row storage and execution.
 */
export function useFunctionTable(funcId: string): UseFunctionTableReturn {
  const router = useRouter();
  const [func, setFunc] = useState<FunctionDefinition | null>(null);
  const [funcLoading, setFuncLoading] = useState(true);
  const [tableId, setTableId] = useState<string | null>(null);
  const [settingsOpen, setSettingsOpen] = useState(false);
  const syncTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Load function + create/get shadow table
  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        setFuncLoading(true);
        const funcData = await fetchFunction(funcId);
        if (cancelled) return;
        setFunc(funcData);

        const table = await getOrCreateFunctionTable(funcId);
        if (cancelled) return;
        setTableId(table.id);
      } catch (e) {
        if (!cancelled) {
          toast.error("Failed to load function");
        }
      } finally {
        if (!cancelled) setFuncLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [funcId]);

  // Wrap useTableBuilder — only call once tableId is ready
  const tb = useTableBuilder(tableId || "__placeholder__");

  // Sync table columns → function definition (debounced)
  const syncColumnsToFunction = useCallback(async () => {
    if (!tb.table || !func) return;

    const inputs: Array<{ name: string; type: string; required: boolean; description: string }> = [];
    const steps: Array<{ tool: string; params: Record<string, string> }> = [];

    for (const col of tb.table.columns) {
      if (col.column_type === "input") {
        inputs.push({
          name: col.id,
          type: "string",
          required: true,
          description: col.name,
        });
      } else if (col.column_type === "enrichment" && col.tool) {
        steps.push({ tool: col.tool, params: col.params });
      } else if (col.column_type === "ai") {
        steps.push({
          tool: "call_ai",
          params: {
            prompt: col.ai_prompt || "",
            model: col.ai_model || "sonnet",
            name: col.name,
          },
        });
      } else if (col.column_type === "gate") {
        steps.push({
          tool: "gate",
          params: {
            condition: col.condition || "",
            label: col.condition_label || col.name,
          },
        });
      }
    }

    try {
      const updated = await updateFunction(funcId, { inputs, steps });
      setFunc(updated);
    } catch {
      toast.error("Failed to sync function");
    }
  }, [tb.table, func, funcId]);

  // Auto-sync when columns change (debounced)
  const prevColumnsRef = useRef<string>("");
  useEffect(() => {
    if (!tb.table) return;
    const colKey = tb.table.columns.map((c) => `${c.id}:${c.column_type}:${c.tool}`).join("|");
    if (prevColumnsRef.current && colKey !== prevColumnsRef.current) {
      // Columns changed — debounce sync
      if (syncTimerRef.current) clearTimeout(syncTimerRef.current);
      syncTimerRef.current = setTimeout(() => {
        syncColumnsToFunction();
      }, 1000);
    }
    prevColumnsRef.current = colKey;
  }, [tb.table, syncColumnsToFunction]);

  // Function metadata operations
  const updateFunctionMeta = useCallback(
    async (fields: { name?: string; description?: string; folder?: string }) => {
      try {
        const updated = await updateFunction(funcId, fields);
        setFunc(updated);
        toast.success("Function updated");
      } catch {
        toast.error("Failed to update function");
      }
    },
    [funcId],
  );

  const deleteFn = useCallback(async () => {
    try {
      await deleteFunctionApi(funcId);
      toast.success("Function deleted");
      router.push("/");
    } catch {
      toast.error("Failed to delete function");
    }
  }, [funcId, router]);

  const duplicateFn = useCallback(async () => {
    try {
      const dup = await duplicateFunctionApi(funcId);
      toast.success("Function duplicated");
      router.push(`/functions/${dup.id}`);
    } catch {
      toast.error("Failed to duplicate function");
    }
  }, [funcId, router]);

  // Override rename to also update function name
  const renameOverride = useCallback(
    async (name: string) => {
      await tb.rename(name);
      await updateFunction(funcId, { name });
      setFunc((prev) => (prev ? { ...prev, name } : prev));
    },
    [tb, funcId],
  );

  // Override addColumn to also sync to function
  const addColumnOverride = useCallback(
    async (body: Record<string, unknown>) => {
      const newColId = await tb.addColumn(body);
      // Sync will happen via the debounced effect
      return newColId;
    },
    [tb],
  );

  const deleteColumnOverride = useCallback(
    async (columnId: string) => {
      await tb.deleteColumn(columnId);
      // Sync will happen via the debounced effect
    },
    [tb],
  );

  return {
    ...tb,
    // Override table operations with function-aware versions
    rename: renameOverride,
    addColumn: addColumnOverride,
    deleteColumn: deleteColumnOverride,
    // Hide loading until both function + table are ready
    loading: funcLoading || (tableId !== null && tb.loading),
    error: tb.error,
    // Function-specific
    func,
    funcLoading,
    syncColumnsToFunction,
    updateFunctionMeta,
    deleteFn,
    duplicateFn,
    settingsOpen,
    setSettingsOpen,
  };
}
