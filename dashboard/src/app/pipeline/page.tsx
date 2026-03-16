"use client";

import { useState, useCallback } from "react";
import { Header } from "@/components/layout/header";
import { DatasetSelector } from "@/components/pipeline/dataset-selector";
import { StageProgressBar } from "@/components/pipeline/stage-progress-bar";
import { DatasetSpreadsheetView } from "@/components/pipeline/dataset-spreadsheet/dataset-spreadsheet-view";
import { DatasetImportDialog } from "@/components/pipeline/dataset-import-dialog";
import { useDatasetContext } from "@/contexts/dataset-context";
import { Button } from "@/components/ui/button";
import { Download, Trash2, ArrowRight, Upload } from "lucide-react";
import { exportDataset, deleteDataset } from "@/lib/api";
import { toast } from "sonner";
import { useRouter } from "next/navigation";

export default function PipelineHomePage() {
  const router = useRouter();
  const {
    datasets,
    datasetsLoading,
    activeId,
    setActiveId,
    dataset,
    rows,
    totalRows,
    reload,
    reloadDatasets,
  } = useDatasetContext();
  const [deleting, setDeleting] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [droppedFile, setDroppedFile] = useState<File | null>(null);

  const handleExport = useCallback(async () => {
    if (!activeId || !dataset) return;
    try {
      const blob = await exportDataset(activeId);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${dataset.name.replace(/\s+/g, "_").toLowerCase()}.csv`;
      a.click();
      URL.revokeObjectURL(url);
      toast.success("CSV exported");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Export failed");
    }
  }, [activeId, dataset]);

  const handleDelete = useCallback(async () => {
    if (!activeId) return;
    if (!confirm("Delete this dataset and all its data?")) return;
    setDeleting(true);
    try {
      await deleteDataset(activeId);
      setActiveId(null);
      reloadDatasets();
      toast.success("Dataset deleted");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Delete failed");
    } finally {
      setDeleting(false);
    }
  }, [activeId, setActiveId, reloadDatasets]);

  const nextStage = dataset
    ? !dataset.stages_completed.includes("find-email")
      ? { label: "Find Email", href: "/pipeline/enrich" }
      : !dataset.stages_completed.includes("classify")
        ? { label: "Score Leads", href: "/pipeline/score" }
        : !dataset.stages_completed.includes("email-gen")
          ? { label: "Generate Emails", href: "/pipeline/email-lab" }
          : null
    : null;

  const columns = dataset?.columns.filter((c) => c.name !== "_row_id") ?? [];

  return (
    <div className="flex flex-col h-full">
      <Header title="Pipeline" />

      <div className="flex flex-col gap-6 p-6 max-w-[1400px]">
        {/* Dataset selector */}
        <DatasetSelector
          datasets={datasets}
          activeId={activeId}
          onSelect={setActiveId}
          onCreated={() => {
            reloadDatasets();
          }}
        />

        {/* Active dataset view */}
        {dataset && (
          <>
            {/* Stage progress */}
            <div className="flex items-center justify-between">
              <StageProgressBar completedStages={dataset.stages_completed} />
              <div className="flex items-center gap-2">
                {nextStage && (
                  <Button
                    size="sm"
                    className="bg-kiln-teal text-clay-900 hover:bg-kiln-teal/90"
                    onClick={() => router.push(nextStage.href)}
                  >
                    {nextStage.label}
                    <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
                  </Button>
                )}
                <Button
                  variant="outline"
                  size="sm"
                  className="border-clay-600 text-clay-200 hover:bg-clay-700"
                  onClick={handleExport}
                >
                  <Download className="h-3.5 w-3.5 mr-1.5" />
                  Export
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-red-400 hover:text-red-300 hover:bg-red-400/10"
                  onClick={handleDelete}
                  disabled={deleting}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>

            {/* Dataset info */}
            <div className="flex items-center gap-4 text-sm text-clay-300">
              <span>{dataset.row_count} rows</span>
              <span>·</span>
              <span>{columns.length} columns</span>
              {dataset.description && (
                <>
                  <span>·</span>
                  <span>{dataset.description}</span>
                </>
              )}
            </div>

            {/* Spreadsheet view */}
            {columns.length === 0 && rows.length === 0 ? (
              <div className="flex flex-col items-center justify-center py-16 text-clay-300 border border-dashed border-clay-600 rounded-lg">
                <p className="text-lg font-medium mb-2">Empty dataset</p>
                <p className="text-sm">Import a CSV or add rows to get started.</p>
              </div>
            ) : (
              <DatasetSpreadsheetView
                columns={columns}
                rows={rows}
                onExport={handleExport}
              />
            )}
            {totalRows > rows.length && (
              <div className="text-center text-xs text-clay-400">
                Showing {rows.length} of {totalRows} rows
              </div>
            )}
          </>
        )}

        {/* Empty state with drop zone */}
        {!dataset && !datasetsLoading && (
          <div
            className="flex flex-col items-center justify-center py-24 text-clay-300 border-2 border-dashed border-clay-600 rounded-lg cursor-pointer hover:border-kiln-teal/50 transition-colors"
            onDragOver={(e) => {
              e.preventDefault();
              e.currentTarget.classList.add("border-kiln-teal");
            }}
            onDragLeave={(e) => {
              e.currentTarget.classList.remove("border-kiln-teal");
            }}
            onDrop={(e) => {
              e.preventDefault();
              e.currentTarget.classList.remove("border-kiln-teal");
              const file = e.dataTransfer.files[0];
              if (file && file.name.endsWith(".csv")) {
                setDroppedFile(file);
                setImportOpen(true);
              } else {
                toast.error("Please drop a .csv file");
              }
            }}
            onClick={() => setImportOpen(true)}
          >
            <Upload className="h-12 w-12 mb-4 text-clay-500" />
            <p className="text-lg font-medium mb-2">No dataset selected</p>
            <p className="text-sm mb-1">Drop a CSV here or click to create a new dataset</p>
            <p className="text-xs text-clay-400">Or select an existing dataset above</p>
          </div>
        )}

        <DatasetImportDialog
          open={importOpen}
          onOpenChange={(open) => {
            setImportOpen(open);
            if (!open) setDroppedFile(null);
          }}
          onCreated={(id) => {
            setActiveId(id);
            reloadDatasets();
            setImportOpen(false);
            setDroppedFile(null);
          }}
          initialFile={droppedFile ?? undefined}
        />
      </div>
    </div>
  );
}
