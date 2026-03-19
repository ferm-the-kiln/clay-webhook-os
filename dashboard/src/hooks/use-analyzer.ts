"use client";

import { useState, useCallback, useRef, useEffect } from "react";
import type { AnalysisType, AnalysisResult, DatasetSummary } from "@/lib/types";
import {
  analyzeDataset,
  fetchAnalysis,
  fetchAnalyses,
  fetchDatasets,
  createDataset,
  importDatasetCsv,
  fetchDatasetRows,
} from "@/lib/api";

export type AnalyzerPhase = "upload" | "configure" | "results";

export interface AnalyzerState {
  phase: AnalyzerPhase;
  datasetId: string | null;
  datasetName: string;
  columns: string[];
  rowCount: number;
  analysisType: AnalysisType | null;
  outcomeColumn: string | null;
  segmentColumns: string[];
  businessContext: string;
  currentAnalysis: AnalysisResult | null;
  analyses: AnalysisResult[];
  isRunning: boolean;
  error: string | null;
  datasets: DatasetSummary[];
}

export function useAnalyzer() {
  const [state, setState] = useState<AnalyzerState>({
    phase: "upload",
    datasetId: null,
    datasetName: "",
    columns: [],
    rowCount: 0,
    analysisType: null,
    outcomeColumn: null,
    segmentColumns: [],
    businessContext: "",
    currentAnalysis: null,
    analyses: [],
    isRunning: false,
    error: null,
    datasets: [],
  });
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null);

  // Load existing datasets on mount
  useEffect(() => {
    fetchDatasets()
      .then((res) => setState((s) => ({ ...s, datasets: res.datasets })))
      .catch(() => {});
  }, []);

  const setPhase = useCallback((phase: AnalyzerPhase) => {
    setState((s) => ({ ...s, phase, error: null }));
  }, []);

  const uploadCsv = useCallback(async (file: File, name: string) => {
    try {
      setState((s) => ({ ...s, error: null }));
      const ds = await createDataset({ name });
      const formData = new FormData();
      formData.append("file", file);
      await importDatasetCsv(ds.id, formData);

      const rowsRes = await fetchDatasetRows(ds.id, { limit: 1 });
      const columns = rowsRes.rows.length > 0
        ? Object.keys(rowsRes.rows[0]).filter((k) => k !== "_row_id")
        : [];

      setState((s) => ({
        ...s,
        datasetId: ds.id,
        datasetName: name,
        columns,
        rowCount: rowsRes.total,
        phase: "configure",
        datasets: [...s.datasets, { id: ds.id, name, row_count: rowsRes.total, column_count: columns.length, stages_completed: [], created_at: ds.created_at, updated_at: ds.updated_at }],
      }));
    } catch (e) {
      setState((s) => ({ ...s, error: e instanceof Error ? e.message : "Upload failed" }));
    }
  }, []);

  const selectExistingDataset = useCallback(async (datasetId: string) => {
    try {
      setState((s) => ({ ...s, error: null }));
      const rowsRes = await fetchDatasetRows(datasetId, { limit: 1 });
      const ds = state.datasets.find((d) => d.id === datasetId);
      const columns = rowsRes.rows.length > 0
        ? Object.keys(rowsRes.rows[0]).filter((k) => k !== "_row_id")
        : [];

      // Load existing analyses
      const analysesRes = await fetchAnalyses(datasetId);

      setState((s) => ({
        ...s,
        datasetId,
        datasetName: ds?.name ?? "Dataset",
        columns,
        rowCount: rowsRes.total,
        analyses: analysesRes.analyses,
        phase: "configure",
      }));
    } catch (e) {
      setState((s) => ({ ...s, error: e instanceof Error ? e.message : "Failed to load dataset" }));
    }
  }, [state.datasets]);

  const setAnalysisConfig = useCallback((config: {
    analysisType?: AnalysisType;
    outcomeColumn?: string | null;
    segmentColumns?: string[];
    businessContext?: string;
  }) => {
    setState((s) => ({ ...s, ...config }));
  }, []);

  const runAnalysis = useCallback(async () => {
    if (!state.datasetId || !state.analysisType) return;

    setState((s) => ({ ...s, isRunning: true, error: null }));

    try {
      const res = await analyzeDataset(state.datasetId, {
        analysis_type: state.analysisType,
        business_context: state.businessContext || undefined,
        outcome_column: state.outcomeColumn,
        segment_columns: state.segmentColumns.length > 0 ? state.segmentColumns : undefined,
      });

      // Start polling
      const datasetId = state.datasetId;
      const analysisId = res.analysis_id;

      const poll = async () => {
        try {
          const analysis = await fetchAnalysis(datasetId, analysisId);
          setState((s) => ({ ...s, currentAnalysis: analysis }));

          if (analysis.status === "completed" || analysis.status === "failed") {
            if (pollRef.current) {
              clearInterval(pollRef.current);
              pollRef.current = null;
            }
            setState((s) => ({
              ...s,
              isRunning: false,
              phase: "results",
              analyses: [analysis, ...s.analyses.filter((a) => a.analysis_id !== analysisId)],
              error: analysis.status === "failed" ? analysis.error_message : null,
            }));
          }
        } catch {
          // Ignore poll errors
        }
      };

      poll();
      pollRef.current = setInterval(poll, 2000);
    } catch (e) {
      setState((s) => ({
        ...s,
        isRunning: false,
        error: e instanceof Error ? e.message : "Analysis failed to start",
      }));
    }
  }, [state.datasetId, state.analysisType, state.businessContext, state.outcomeColumn, state.segmentColumns]);

  const viewAnalysis = useCallback((analysis: AnalysisResult) => {
    setState((s) => ({ ...s, currentAnalysis: analysis, phase: "results" }));
  }, []);

  const reset = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current);
      pollRef.current = null;
    }
    setState((s) => ({
      ...s,
      phase: "upload",
      datasetId: null,
      datasetName: "",
      columns: [],
      rowCount: 0,
      analysisType: null,
      outcomeColumn: null,
      segmentColumns: [],
      businessContext: "",
      currentAnalysis: null,
      isRunning: false,
      error: null,
    }));
  }, []);

  // Cleanup on unmount
  useEffect(() => {
    return () => {
      if (pollRef.current) clearInterval(pollRef.current);
    };
  }, []);

  return {
    ...state,
    setPhase,
    uploadCsv,
    selectExistingDataset,
    setAnalysisConfig,
    runAnalysis,
    viewAnalysis,
    reset,
  };
}
