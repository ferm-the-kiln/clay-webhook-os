"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { BatchStatus, Job } from "@/lib/types";
import {
  runBatch,
  fetchBatchStatus,
  fetchQueueStatus,
  pauseQueue,
  resumeQueue,
  retryBatch,
} from "@/lib/api";

export type BatchPhase = "upload" | "preview" | "running" | "done";

export interface UseBatchReturn {
  // Phase state
  phase: BatchPhase;
  setPhase: (p: BatchPhase) => void;

  // Upload phase
  csvHeaders: string[];
  csvRows: Record<string, string>[];
  setCsvData: (headers: string[], rows: Record<string, string>[]) => void;
  validationWarnings: string[];

  // Config
  selectedSkill: string;
  setSelectedSkill: (skill: string) => void;
  columnMapping: Record<string, string>;
  setColumnMapping: (mapping: Record<string, string>) => void;
  model: string | null;
  setModel: (m: string | null) => void;
  instructions: string;
  setInstructions: (i: string) => void;

  // Run
  startBatch: () => Promise<void>;
  batchId: string | null;
  batchStatus: BatchStatus | null;

  // Polling
  isPolling: boolean;
  lastUpdated: Date | null;
  refreshNow: () => void;

  // Queue controls
  queuePaused: boolean;
  togglePause: () => Promise<void>;

  // Retry
  retryFailed: (modifiedRows?: Record<string, Record<string, unknown>>) => Promise<void>;

  // Detail panel
  selectedJob: Job | null;
  setSelectedJob: (job: Job | null) => void;

  // Reset
  reset: () => void;
}

const MAX_CSV_SIZE_BYTES = 5 * 1024 * 1024;

export function useBatch(): UseBatchReturn {
  const [phase, setPhase] = useState<BatchPhase>("upload");
  const [csvHeaders, setCsvHeaders] = useState<string[]>([]);
  const [csvRows, setCsvRows] = useState<Record<string, string>[]>([]);
  const [validationWarnings, setValidationWarnings] = useState<string[]>([]);

  const [selectedSkill, setSelectedSkill] = useState("");
  const [columnMapping, setColumnMapping] = useState<Record<string, string>>({});
  const [model, setModel] = useState<string | null>(null);
  const [instructions, setInstructions] = useState("");

  const [batchId, setBatchId] = useState<string | null>(null);
  const [batchStatus, setBatchStatus] = useState<BatchStatus | null>(null);
  const [isPolling, setIsPolling] = useState(false);
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null);
  const [queuePaused, setQueuePaused] = useState(false);

  const [selectedJob, setSelectedJob] = useState<Job | null>(null);

  // Persist selection across polls
  const selectionRef = useRef<Set<string>>(new Set());

  // CSV data setter with validation
  const setCsvData = useCallback((headers: string[], rows: Record<string, string>[]) => {
    setCsvHeaders(headers);
    setCsvRows(rows);

    const warnings: string[] = [];

    // Estimate file size (rough)
    const estimatedSize = JSON.stringify(rows).length;
    if (estimatedSize > MAX_CSV_SIZE_BYTES) {
      warnings.push(`Large file (~${Math.round(estimatedSize / 1024 / 1024)}MB). Processing may be slow.`);
    }

    // Duplicate detection
    const seen = new Set<string>();
    let dupes = 0;
    for (const row of rows) {
      const key = JSON.stringify(row);
      if (seen.has(key)) dupes++;
      else seen.add(key);
    }
    if (dupes > 0) {
      warnings.push(`${dupes} duplicate row${dupes > 1 ? "s" : ""} detected.`);
    }

    setValidationWarnings(warnings);
    setPhase("preview");
  }, []);

  // Start batch
  const startBatch = useCallback(async () => {
    if (!selectedSkill || csvRows.length === 0) return;

    // Map CSV rows through column mapping
    const mappedRows = csvRows.map((row) => {
      const mapped: Record<string, unknown> = {};
      for (const [skillField, csvCol] of Object.entries(columnMapping)) {
        if (csvCol && row[csvCol] !== undefined) {
          mapped[skillField] = row[csvCol];
        }
      }
      // Include unmapped CSV fields as-is
      for (const [key, val] of Object.entries(row)) {
        if (!Object.values(columnMapping).includes(key)) {
          mapped[key] = val;
        }
      }
      return mapped;
    });

    const resp = await runBatch({
      skill: selectedSkill,
      rows: mappedRows,
      model: model || undefined,
      instructions: instructions || undefined,
    });

    setBatchId(resp.batch_id);
    setPhase("running");
  }, [selectedSkill, csvRows, columnMapping, model, instructions]);

  // Polling
  useEffect(() => {
    if (phase !== "running" || !batchId) return;

    setIsPolling(true);
    let cancelled = false;

    const poll = async () => {
      try {
        const status = await fetchBatchStatus(batchId);
        if (cancelled) return;
        setBatchStatus(status);
        setLastUpdated(new Date());

        if (status.done) {
          setPhase("done");
          setIsPolling(false);
        }
      } catch {
        // Ignore poll errors silently
      }
    };

    // Immediate first poll
    poll();
    const interval = setInterval(poll, 3000);

    return () => {
      cancelled = true;
      clearInterval(interval);
      setIsPolling(false);
    };
  }, [phase, batchId]);

  // Keep polling queue status for pause state
  useEffect(() => {
    if (phase !== "running") return;

    const checkQueue = async () => {
      try {
        const qs = await fetchQueueStatus();
        setQueuePaused(qs.paused);
      } catch {
        // ignore
      }
    };

    checkQueue();
    const interval = setInterval(checkQueue, 5000);
    return () => clearInterval(interval);
  }, [phase]);

  const refreshNow = useCallback(async () => {
    if (!batchId) return;
    try {
      const status = await fetchBatchStatus(batchId);
      setBatchStatus(status);
      setLastUpdated(new Date());
      if (status.done) {
        setPhase("done");
        setIsPolling(false);
      }
    } catch {
      // ignore
    }
  }, [batchId]);

  const togglePause = useCallback(async () => {
    if (queuePaused) {
      await resumeQueue();
      setQueuePaused(false);
    } else {
      await pauseQueue();
      setQueuePaused(true);
    }
  }, [queuePaused]);

  const retryFailed = useCallback(async (modifiedRows?: Record<string, Record<string, unknown>>) => {
    if (!batchId) return;
    await retryBatch(batchId, modifiedRows);
    // Go back to running to re-poll
    setPhase("running");
  }, [batchId]);

  const reset = useCallback(() => {
    setPhase("upload");
    setCsvHeaders([]);
    setCsvRows([]);
    setValidationWarnings([]);
    setSelectedSkill("");
    setColumnMapping({});
    setModel(null);
    setInstructions("");
    setBatchId(null);
    setBatchStatus(null);
    setIsPolling(false);
    setLastUpdated(null);
    setSelectedJob(null);
    selectionRef.current.clear();
  }, []);

  return {
    phase,
    setPhase,
    csvHeaders,
    csvRows,
    setCsvData,
    validationWarnings,
    selectedSkill,
    setSelectedSkill,
    columnMapping,
    setColumnMapping,
    model,
    setModel,
    instructions,
    setInstructions,
    startBatch,
    batchId,
    batchStatus,
    isPolling,
    lastUpdated,
    refreshNow,
    queuePaused,
    togglePause,
    retryFailed,
    selectedJob,
    setSelectedJob,
    reset,
  };
}
