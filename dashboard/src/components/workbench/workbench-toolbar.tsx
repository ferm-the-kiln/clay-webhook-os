"use client";

import { DatasetSelector } from "@/components/pipeline/dataset-selector";
import { Button } from "@/components/ui/button";
import { Download, Trash2 } from "lucide-react";
import { useDatasetContext } from "@/contexts/dataset-context";
import { exportDataset, deleteDataset } from "@/lib/api";
import { toast } from "sonner";

export function WorkbenchToolbar() {
  const { datasets, activeId, setActiveId, dataset, reloadDatasets } = useDatasetContext();

  const handleExport = async () => {
    if (!activeId) return;
    try {
      const blob = await exportDataset(activeId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${dataset?.name || "dataset"}-${Date.now()}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("Export downloaded");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Export failed");
    }
  };

  const handleDelete = async () => {
    if (!activeId) return;
    if (!confirm(`Delete dataset "${dataset?.name}"? This cannot be undone.`)) return;
    try {
      await deleteDataset(activeId);
      setActiveId(null);
      reloadDatasets();
      toast.success("Dataset deleted");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    }
  };

  return (
    <div className="flex items-center justify-between px-4 py-3 border-b border-clay-600 bg-clay-800">
      <DatasetSelector
        datasets={datasets}
        activeId={activeId}
        onSelect={setActiveId}
        onCreated={reloadDatasets}
      />

      {activeId && (
        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={handleExport}
            className="border-clay-600 text-clay-200 hover:bg-clay-700 h-8"
          >
            <Download className="h-3.5 w-3.5 mr-1.5" />
            Export
          </Button>
          <Button
            variant="outline"
            size="sm"
            onClick={handleDelete}
            className="border-clay-600 text-clay-200 hover:bg-kiln-coral/10 hover:text-kiln-coral hover:border-kiln-coral/30 h-8"
          >
            <Trash2 className="h-3.5 w-3.5" />
          </Button>
        </div>
      )}
    </div>
  );
}
