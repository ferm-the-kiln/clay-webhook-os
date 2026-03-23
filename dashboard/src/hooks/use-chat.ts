"use client";

import { useState, useEffect, useCallback, useRef, useMemo } from "react";
import {
  fetchFunctions,
  createChannel,
  fetchChannel,
  fetchChannels,
  streamChannelMessage,
  checkChannelHealth,
  createClientChannel,
  fetchClientChannels,
  fetchClientChannel,
  streamClientChannelMessage,
  updateChannelTitle,
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

  // Free chat
  freeChatAvailable: boolean;

  // Actions
  createSession: (functionId?: string) => Promise<void>;
  loadSession: (sessionId: string) => Promise<void>;
  sendMessage: (csvData?: Record<string, unknown>[]) => void;
  selectFunction: (func: FunctionDefinition) => void;
  deselectFunction: () => void;
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
  sessionsLoading: boolean;
}

interface UseChatOptions {
  clientSlug?: string;
  shareToken?: string;
  clientFunctionId?: string;
}

function getStorageKey(clientSlug?: string): string {
  return clientSlug ? `clay-chat-session-${clientSlug}` : "clay-chat-session";
}

export function useChat(options?: UseChatOptions): UseChatReturn {
  const clientSlug = options?.clientSlug;
  const shareToken = options?.shareToken;
  const clientFunctionId = options?.clientFunctionId;
  const isClientMode = !!(clientSlug && shareToken);
  const storageKey = getStorageKey(clientSlug);

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

  // Free chat availability
  const [freeChatAvailable, setFreeChatAvailable] = useState(false);

  // Input state
  const [inputValue, setInputValue] = useState("");
  const [loading, setLoading] = useState(true);
  const [sessionsLoading, setSessionsLoading] = useState(true);

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

  // Check channel health on mount (determines if free chat is available)
  useEffect(() => {
    checkChannelHealth()
      .then((data) => setFreeChatAvailable(data.status === "ok"))
      .catch(() => setFreeChatAvailable(false));
  }, []);

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
      .catch(() => {})
      .finally(() => setSessionsLoading(false));
  }, [isClientMode, clientSlug, shareToken]);

  // Restore active session from localStorage after sessions load
  useEffect(() => {
    if (sessionsLoading || activeSession) return;
    try {
      const savedId = localStorage.getItem(storageKey);
      if (savedId) {
        // Only restore if the session exists in the loaded list
        const exists = sessions.some((s) => s.id === savedId);
        if (exists) {
          loadSession(savedId);
        } else {
          localStorage.removeItem(storageKey);
        }
      }
    } catch {
      // localStorage unavailable (e.g., incognito)
    }
  }, [sessionsLoading, sessions, storageKey]); // eslint-disable-line react-hooks/exhaustive-deps

  // Persist active session ID to localStorage
  useEffect(() => {
    try {
      if (activeSession) {
        localStorage.setItem(storageKey, activeSession.id);
      }
    } catch {
      // localStorage unavailable
    }
  }, [activeSession?.id, storageKey]);

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

  const deselectFunction = useCallback(() => {
    setSelectedFunction(null);
  }, []);

  const createSessionAction = useCallback(
    async (functionId?: string) => {
      try {
        const session = isClientMode
          ? await createClientChannel(clientSlug!, shareToken!, { function_id: functionId || undefined })
          : await createChannel({ function_id: functionId || undefined });
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

  const sendMessage = useCallback((csvData?: Record<string, unknown>[]) => {
    if (!activeSession || !inputValue.trim() || streaming) return;

    // Determine mode based on whether a function is selected
    const isFreeChatMessage = !selectedFunction;
    const mode: "function" | "free_chat" = isFreeChatMessage ? "free_chat" : "function";

    // Build data rows
    let data: Record<string, unknown>[];
    if (csvData && csvData.length > 0) {
      // CSV upload data
      data = csvData;
    } else if (isFreeChatMessage) {
      // Free chat: no data rows
      data = [];
    } else {
      // Function mode: each line becomes a data row
      const lines = inputValue.split("\n").filter((l) => l.trim());
      data = lines.map((l) => ({ value: l.trim() }));
    }

    // Build user message
    const userMessage: ChannelMessage = {
      role: "user",
      content: inputValue,
      timestamp: Date.now() / 1000,
      data: data.length > 0 ? data : null,
      results: null,
      execution_id: null,
      mode,
    };

    // Build assistant placeholder
    const assistantPlaceholder: ChannelMessage = {
      role: "assistant",
      content: isFreeChatMessage ? "" : "Processing...",
      timestamp: Date.now() / 1000,
      data: null,
      results: null,
      execution_id: null,
      mode,
    };

    // Optimistic update
    setMessages((prev) => [...prev, userMessage, assistantPlaceholder]);
    const sentInput = inputValue;
    setInputValue("");
    setStreaming(true);

    // SSE event handler
    const onEvent = (
      eventType: string,
      payload: Record<string, unknown>
    ) => {
      // ── Free chat events ──
      if (mode === "free_chat") {
        switch (eventType) {
          case "chunk":
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last && last.role === "assistant") {
                updated[updated.length - 1] = {
                  ...last,
                  content: last.content + ((payload.text as string) || ""),
                };
              }
              return updated;
            });
            break;
          case "done":
            setStreaming(false);
            // Auto-name the session from the first user message (only when it's a new session)
            setMessages((currentMsgs) => {
              const isFirstExchange = currentMsgs.filter((m) => m.role === "user").length === 1;
              if (isFirstExchange && activeSession) {
                const firstUserMsg = currentMsgs.find((m) => m.role === "user");
                if (firstUserMsg) {
                  const autoTitle = firstUserMsg.content.slice(0, 40).trim() + (firstUserMsg.content.length > 40 ? "…" : "");
                  if (!isClientMode) {
                    updateChannelTitle(activeSession.id, autoTitle).catch(() => {/* silent */});
                  }
                }
              }
              return currentMsgs;
            });
            refreshSessions();
            break;
          case "connected":
            // Initial connection event — ignore
            break;
          case "error":
            setStreaming(false);
            setMessages((prev) => {
              const updated = [...prev];
              const last = updated[updated.length - 1];
              if (last && last.role === "assistant") {
                updated[updated.length - 1] = {
                  ...last,
                  content: "Something went wrong. Try again.",
                };
              }
              return updated;
            });
            toast.error((payload.error_message as string) || "Free chat error");
            break;
        }
        return;
      }

      // ── Function execution events (existing) ──
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
              const results =
                (payload.results as Record<string, unknown>[]) || [];
              updated[updated.length - 1] = {
                ...last,
                content:
                  results.length === 0
                    ? "No results returned. The function completed but produced no output."
                    : "",
                results: results.length > 0 ? results : null,
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
      const isNetworkError =
        error.includes("Failed to fetch") ||
        error.includes("NetworkError") ||
        error.includes("network") ||
        error.includes("ERR_") ||
        error.includes("Backend unreachable");
      const errorContent = isNetworkError
        ? "Connection lost -- your session is saved. Refresh to reconnect."
        : mode === "free_chat"
          ? "Free chat unavailable. Try again later."
          : "Processing failed -- check your data and try again.";
      setMessages((prev) => {
        const updated = [...prev];
        const last = updated[updated.length - 1];
        if (last && last.role === "assistant") {
          updated[updated.length - 1] = { ...last, content: errorContent };
        }
        return updated;
      });
      toast.error(isNetworkError ? "Connection lost" : error);
    };

    // Start streaming
    const funcId = selectedFunction?.id;
    const controller = isClientMode
      ? streamClientChannelMessage(
          clientSlug!,
          shareToken!,
          activeSession.id,
          sentInput,
          data,
          onEvent,
          onError,
          mode,
          funcId
        )
      : streamChannelMessage(
          activeSession.id,
          sentInput,
          data,
          onEvent,
          onError,
          mode,
          funcId
        );
    abortRef.current = controller;
  }, [activeSession, inputValue, streaming, selectedFunction, refreshSessions, isClientMode, clientSlug, shareToken]);

  return {
    sessions,
    activeSession,
    messages,
    streaming,
    streamProgress,
    functions,
    functionsByFolder,
    selectedFunction,
    freeChatAvailable,
    createSession: createSessionAction,
    loadSession,
    sendMessage,
    selectFunction,
    deselectFunction,
    refreshSessions,
    rowStatuses,
    executionState,
    completedResults,
    inputValue,
    setInputValue,
    loading,
    sessionsLoading,
  };
}
