"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import {
  fetchFunctions,
  createChannel,
  fetchChannel,
  fetchChannels,
  streamChannelMessage,
  createClientChannel,
  fetchClientChannels,
  fetchClientChannel,
  streamClientChannelMessage,
} from "@/lib/api";
import type {
  FunctionDefinition,
  ChannelMessage,
  ChannelSession,
  ChannelSessionSummary,
} from "@/lib/types";
import { toast } from "sonner";

export type RowStatusValue = "pending" | "running" | "done" | "error";

export interface RowStatus {
  index: number;
  status: RowStatusValue;
  result: Record<string, unknown> | null;
  error: string | null;
}

export interface ExecutionState {
  functionId: string;
  functionName: string;
  totalRows: number;
  startedAt: number;
}

export interface UseChatReturn {
  // Session state
  sessions: ChannelSessionSummary[];
  activeSession: ChannelSession | null;

  // Message state
  messages: ChannelMessage[];
  streaming: boolean;
  streamProgress: { current: number; total: number } | null;

  // Function selection
  functions: FunctionDefinition[];
  functionsByFolder: Record<string, FunctionDefinition[]>;
  selectedFunction: FunctionDefinition | null;

  // Actions
  createSession: (functionId: string) => Promise<void>;
  loadSession: (sessionId: string) => Promise<void>;
  sendMessage: () => void;
  selectFunction: (func: FunctionDefinition) => void;
  refreshSessions: () => Promise<void>;

  // Input state
  inputValue: string;
  setInputValue: (v: string) => void;

  // Execution tracking
  rowStatuses: RowStatus[];
  executionState: ExecutionState | null;
  completedResults: Record<string, unknown>[];

  // Loading
  loading: boolean;
}

interface UseChatOptions {
  clientSlug?: string;
  shareToken?: string;
  clientFunctionId?: string;
}

export function useChat(options?: UseChatOptions): UseChatReturn {
  const clientSlug = options?.clientSlug;
  const shareToken = options?.shareToken;
  const clientFunctionId = options?.clientFunctionId;
  const isClientMode = !!(clientSlug && shareToken);

  // Function state
  const [functions, setFunctions] = useState<FunctionDefinition[]>([]);
  const [selectedFunction, setSelectedFunction] =
    useState<FunctionDefinition | null>(null);

  // Session state
  const [sessions, setSessions] = useState<ChannelSessionSummary[]>([]);
  const [activeSession, setActiveSession] = useState<ChannelSession | null>(
    null
  );

  // Message state
  const [messages, setMessages] = useState<ChannelMessage[]>([]);
  const [streaming, setStreaming] = useState(false);
  const [streamProgress, setStreamProgress] = useState<{
    current: number;
    total: number;
  } | null>(null);

  // Execution tracking state
  const [rowStatuses, setRowStatuses] = useState<RowStatus[]>([]);
  const [executionState, setExecutionState] = useState<ExecutionState | null>(null);
  const [completedResults, setCompletedResults] = useState<Record<string, unknown>[]>([]);

  // Input state
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(true);

  // Stream abort ref
  const abortRef = useRef<AbortController | null>(null);

  // Group functions by folder
  const functionsByFolder = useMemo(() => {
    const grouped: Record<string, FunctionDefinition[]> = {};
    functions.forEach((f) => {
      const folder = f.folder || "Uncategorized";
      if (!grouped[folder]) grouped[folder] = [];
      grouped[folder].push(f);
    });
    return grouped;
  }, [functions]);

  // Load functions on mount -- skip in client mode (clients don't have API key)
  useEffect(() => {
    if (isClientMode) {
      setLoading(false);
      return;
    }
    fetchFunctions()
      .then(({ functions: funcs }) => {
        setFunctions(funcs);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [isClientMode]);

  // Load sessions on mount
  useEffect(() => {
    const loadSessions = isClientMode
      ? () => fetchClientChannels(clientSlug!, shareToken!)
      : () => fetchChannels();
    loadSessions()
      .then(({ sessions: sess }) => setSessions(sess))
      .catch(() => {});
  }, [isClientMode, clientSlug, shareToken]);

  // Cleanup abort controller on unmount
  useEffect(() => {
    return () => {
      abortRef.current?.abort();
    };
  }, []);

  const refreshSessions = useCallback(async () => {
    try {
      const { sessions: sess } = isClientMode
        ? await fetchClientChannels(clientSlug!, shareToken!)
        : await fetchChannels();
      setSessions(sess);
    } catch {
      // silent
    }
  }, [isClientMode, clientSlug, shareToken]);

  const selectFunction = useCallback((func: FunctionDefinition) => {
    setSelectedFunction(func);
  }, []);

  const createSessionAction = useCallback(
    async (functionId: string) => {
      try {
        const session = isClientMode
          ? await createClientChannel(clientSlug!, shareToken!, { function_id: functionId })
          : await createChannel({ function_id: functionId });
        setActiveSession(session);
        setMessages(session.messages || []);
        await refreshSessions();
      } catch (e) {
        toast.error(
          e instanceof Error ? e.message : "Failed to create session"
        );
      }
    },
    [isClientMode, clientSlug, shareToken, refreshSessions]
  );

  const loadSession = useCallback(async (sessionId: string) => {
    // Abort any active stream before switching
    abortRef.current?.abort();
    abortRef.current = null;
    setStreaming(false);
    setStreamProgress(null);
    setRowStatuses([]);
    setExecutionState(null);
    setCompletedResults([]);

    try {
      const session = isClientMode
        ? await fetchClientChannel(clientSlug!, shareToken!, sessionId)
        : await fetchChannel(sessionId);
      setActiveSession(session);
      setMessages(session.messages || []);
      setSelectedFunction(null); // Will be determined by session
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to load session");
    }
  }, [isClientMode, clientSlug, shareToken]);

  const sendMessage = useCallback(() => {
    if (!activeSession || !inputValue.trim() || streaming) return;

    // Parse input: each non-empty line becomes a data row
    const lines = inputValue.split("\n").filter((l) => l.trim());
    const data = lines.map((l) => ({ value: l.trim() }));

    // Build user message
    const userMessage: ChannelMessage = {
      role: "user",
      content: inputValue,
      timestamp: Date.now() / 1000,
      data,
      results: null,
      execution_id: null,
    };

    // Build assistant placeholder
    const assistantPlaceholder: ChannelMessage = {
      role: "assistant",
      content: "Processing...",
      timestamp: Date.now() / 1000,
      data: null,
      results: null,
      execution_id: null,
    };

    // Optimistic update
    setMessages((prev) => [...prev, userMessage, assistantPlaceholder]);
    setInputValue("");
    setStreaming(true);

    // SSE event handler
    const onEvent = (
      eventType: string,
      payload: Record<string, unknown>
    ) => {
      switch (eventType) {
        case "function_started":
          {
            const totalRows = (payload.total_rows as number) || 0;
            setStreamProgress({ current: 0, total: totalRows });
            setExecutionState({
              functionId: payload.function_id as string,
              functionName: payload.function_name as string,
              totalRows,
              startedAt: Date.now(),
            });
            setRowStatuses(
              Array.from({ length: totalRows }, (_, i) => ({
                index: i,
                status: "pending" as const,
                result: null,
                error: null,
              }))
            );
            setCompletedResults([]);
          }
          break;

        case "row_processing":
          {
            const rowIndex = (payload.row_index as number) + 1;
            const totalRows = payload.total_rows as number;
            const rawIdx = payload.row_index as number;
            setStreamProgress({ current: rowIndex, total: totalRows });
            setRowStatuses((prev) =>
              prev.map((r, i) =>
                i === rawIdx ? { ...r, status: "running" } : r
              )
            );
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last && last.role === "assistant") {
                updated[updated.length - 1] = {
                  ...last,
                  content: `Processing ${rowIndex}/${totalRows}...`,
                };
              }
              return updated;
            });
          }
          break;

        case "row_complete":
          {
            const rowIdx = (payload.row_index as number) + 1;
            const total = payload.total_rows as number;
            const rawRowIdx = payload.row_index as number;
            setStreamProgress({ current: rowIdx, total });
            setRowStatuses((prev) =>
              prev.map((r, i) =>
                i === rawRowIdx
                  ? { ...r, status: "done", result: payload.result as Record<string, unknown> }
                  : r
              )
            );
            setCompletedResults((prev) => [
              ...prev,
              payload.result as Record<string, unknown>,
            ]);
          }
          break;

        case "row_error":
          {
            const errIdx = (payload.row_index as number) + 1;
            const errTotal = payload.total_rows as number;
            const rawErrIdx = payload.row_index as number;
            setStreamProgress({ current: errIdx, total: errTotal });
            setRowStatuses((prev) =>
              prev.map((r, i) =>
                i === rawErrIdx
                  ? { ...r, status: "error", error: payload.error as string }
                  : r
              )
            );
          }
          break;

        case "function_complete":
          setStreaming(false);
          setStreamProgress(null);
          setExecutionState(null);
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.role === "assistant") {
              updated[updated.length - 1] = {
                ...last,
                content: "",
                results: (payload.results as Record<string, unknown>[]) || [],
              };
            }
            return updated;
          });
          // Refresh sessions to update message counts
          refreshSessions();
          break;

        case "error":
          setStreaming(false);
          setStreamProgress(null);
          setMessages((prev) => {
            const updated = [...prev];
            const last = updated[updated.length - 1];
            if (last && last.role === "assistant") {
              updated[updated.length - 1] = {
                ...last,
                content:
                  "Processing failed -- check your data and try again.",
              };
            }
            return updated;
          });
          toast.error(
            (payload.error as string) || "Processing failed"
          );
          break;
      }
    };

    // SSE error handler
    const onError = (error: string) => {
      setStreaming(false);
      setStreamProgress(null);
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last && last.role === "assistant") {
          updated[updated.length - 1] = {
            ...last,
            content: "Processing failed -- check your data and try again.",
          };
        }
        return updated;
      });
      toast.error(error);
    };

    // Start streaming
    const controller = isClientMode
      ? streamClientChannelMessage(
          clientSlug!,
          shareToken!,
          activeSession.id,
          inputValue,
          data,
          onEvent,
          onError
        )
      : streamChannelMessage(
          activeSession.id,
          inputValue,
          data,
          onEvent,
          onError
        );
    abortRef.current = controller;
  }, [activeSession, inputValue, streaming, refreshSessions, isClientMode, clientSlug, shareToken]);

  return {
    sessions,
    activeSession,
    messages,
    streaming,
    streamProgress,
    functions,
    functionsByFolder,
    selectedFunction,
    createSession: createSessionAction,
    loadSession,
    sendMessage,
    selectFunction,
    refreshSessions,
    rowStatuses,
    executionState,
    completedResults,
    inputValue,
    setInputValue,
    loading,
  };
}
