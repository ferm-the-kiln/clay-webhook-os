"use client";

import { useState, useEffect, useCallback, useRef } from "react";
import type { Dataset, DatasetRow, DatasetSummary, StageStatus } from "@/lib/types";
import {
  fetchDatasets,
  fetchDataset,
  fetchDatasetRows,
  fetchStageStatus,
} from "@/lib/api";

const ACTIVE_DATASET_KEY = "clay-os-active-dataset-id";

export function useDatasets() {
  const [datasets, setDatasets] = useState<DatasetSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await fetchDatasets();
      setDatasets(res.datasets);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load datasets");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  return { datasets, loading, error, reload: load };
}

export function useDataset(id: string | null) {
  const [dataset, setDataset] = useState<Dataset | null>(null);
  const [rows, setRows] = useState<DatasetRow[]>([]);
  const [totalRows, setTotalRows] = useState(0);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadDataset = useCallback(async () => {
    if (!id) return;
    setLoading(true);
    try {
      const [ds, rowRes] = await Promise.all([
        fetchDataset(id),
        fetchDatasetRows(id, { offset: 0, limit: 100 }),
      ]);
      setDataset(ds);
      setRows(rowRes.rows as DatasetRow[]);
      setTotalRows(rowRes.total);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load dataset");
    } finally {
      setLoading(false);
    }
  }, [id]);

  const loadMoreRows = useCallback(
    async (offset: number, limit = 100) => {
      if (!id) return;
      const res = await fetchDatasetRows(id, { offset, limit });
      setRows((prev) => [...prev, ...(res.rows as DatasetRow[])]);
      setTotalRows(res.total);
    },
    [id]
  );

  useEffect(() => {
    loadDataset();
  }, [loadDataset]);

  return { dataset, rows, totalRows, loading, error, reload: loadDataset, loadMoreRows };
}

export function useActiveDataset() {
  const [activeId, setActiveIdState] = useState<string | null>(null);

  useEffect(() => {
    const stored = localStorage.getItem(ACTIVE_DATASET_KEY);
    if (stored) setActiveIdState(stored);
  }, []);

  const setActiveId = useCallback((id: string | null) => {
    setActiveIdState(id);
    if (id) {
      localStorage.setItem(ACTIVE_DATASET_KEY, id);
    } else {
      localStorage.removeItem(ACTIVE_DATASET_KEY);
    }
  }, []);

  return { activeId, setActiveId };
}

export function useStagePolling(
  datasetId: string | null,
  batchId: string | null,
  onComplete?: () => void
) {
  const [status, setStatus] = useState<StageStatus | null>(null);
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null);

  useEffect(() => {
    if (!datasetId || !batchId) {
      setStatus(null);
      return;
    }

    const poll = async () => {
      try {
        const s = await fetchStageStatus(datasetId, batchId);
        setStatus(s);
        if (s.status === "completed" || s.status === "failed") {
          if (intervalRef.current) clearInterval(intervalRef.current);
          onComplete?.();
        }
      } catch {
        // Ignore poll errors
      }
    };

    poll();
    intervalRef.current = setInterval(poll, 1500);

    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current);
    };
  }, [datasetId, batchId, onComplete]);

  return status;
}
