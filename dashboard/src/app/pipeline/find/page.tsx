"use client";

import { useState } from "react";
import { Header } from "@/components/layout/header";
import { DatasetSelector } from "@/components/pipeline/dataset-selector";
import { DatasetSpreadsheetView } from "@/components/pipeline/dataset-spreadsheet/dataset-spreadsheet-view";
import { DatasetImportDialog } from "@/components/pipeline/dataset-import-dialog";
import { useDatasetContext } from "@/contexts/dataset-context";
import { Upload, UserSearch, ArrowRight } from "lucide-react";
import { toast } from "sonner";

export default function FindContactsPage() {
  const { datasets, activeId, setActiveId, dataset, rows, reloadDatasets } = useDatasetContext();
  const [importOpen, setImportOpen] = useState(false);
  const [droppedFile, setDroppedFile] = useState<File | null>(null);

  const columns = dataset?.columns.filter((c) => c.name !== "_row_id") ?? [];

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Find Contacts"
        breadcrumbs={[
          { label: "Pipeline", href: "/pipeline" },
          { label: "Find Contacts" },
        ]}
      />

      <div className="flex flex-col gap-6 p-6 max-w-[1400px]">
        <DatasetSelector
          datasets={datasets}
          activeId={activeId}
          onSelect={setActiveId}
          onCreated={reloadDatasets}
        />

        {dataset && rows.length > 0 ? (
          <DatasetSpreadsheetView columns={columns} rows={rows} />
        ) : (
          <div
            className="flex flex-col items-center justify-center py-20 text-clay-300 border-2 border-dashed border-clay-600 rounded-lg cursor-pointer hover:border-kiln-teal/50 transition-colors"
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
            <p className="text-lg font-medium mb-3">Get started</p>
            <div className="flex items-center gap-3 text-sm">
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-clay-700/50 border border-clay-600">
                <span className="text-kiln-teal font-medium">1.</span> Drop CSV
              </div>
              <ArrowRight className="h-4 w-4 text-clay-500" />
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-clay-700/50 border border-clay-600">
                <span className="text-kiln-teal font-medium">2.</span> Name dataset
              </div>
              <ArrowRight className="h-4 w-4 text-clay-500" />
              <div className="flex items-center gap-2 px-3 py-1.5 rounded-md bg-clay-700/50 border border-clay-600">
                <span className="text-kiln-teal font-medium">3.</span> Start enriching
              </div>
            </div>
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
