"use client";

import { createContext, useContext, type ReactNode } from "react";
import { useDatasets, useDataset, useActiveDataset } from "@/hooks/use-dataset";
import type { Dataset, DatasetRow, DatasetSummary } from "@/lib/types";

interface DatasetContextValue {
  datasets: DatasetSummary[];
  datasetsLoading: boolean;
  activeId: string | null;
  setActiveId: (id: string | null) => void;
  dataset: Dataset | null;
  rows: DatasetRow[];
  totalRows: number;
  loading: boolean;
  reload: () => void;
  reloadDatasets: () => void;
}

const DatasetContext = createContext<DatasetContextValue | null>(null);

export function DatasetProvider({ children }: { children: ReactNode }) {
  const { datasets, loading: datasetsLoading, reload: reloadDatasets } = useDatasets();
  const { activeId, setActiveId } = useActiveDataset();
  const { dataset, rows, totalRows, loading, reload } = useDataset(activeId);

  return (
    <DatasetContext.Provider
      value={{
        datasets,
        datasetsLoading,
        activeId,
        setActiveId,
        dataset,
        rows,
        totalRows,
        loading,
        reload,
        reloadDatasets,
      }}
    >
      {children}
    </DatasetContext.Provider>
  );
}

export function useDatasetContext() {
  const ctx = useContext(DatasetContext);
  if (!ctx) {
    throw new Error("useDatasetContext must be used within a DatasetProvider");
  }
  return ctx;
}
