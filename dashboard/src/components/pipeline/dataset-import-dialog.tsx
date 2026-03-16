"use client";

import { useState, useRef, useEffect, useCallback } from "react";
import Papa from "papaparse";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from "@/components/ui/dialog";
import { Upload, FileSpreadsheet, AlertTriangle } from "lucide-react";
import { createDataset, importDatasetCsv } from "@/lib/api";
import { toast } from "sonner";

interface DatasetImportDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onCreated: (datasetId: string) => void;
  initialFile?: File;
}

const EXPECTED_COLUMNS = ["first_name", "last_name", "email", "company_domain"];

export function DatasetImportDialog({
  open,
  onOpenChange,
  onCreated,
  initialFile,
}: DatasetImportDialogProps) {
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState<{ headers: string[]; rows: Record<string, string>[] } | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  // Handle initialFile prop
  useEffect(() => {
    if (initialFile && open) {
      setFile(initialFile);
      parsePreview(initialFile);
    }
  }, [initialFile, open]);

  const parsePreview = useCallback((f: File) => {
    Papa.parse<Record<string, string>>(f, {
      header: true,
      skipEmptyLines: true,
      preview: 5,
      complete: (result) => {
        setPreview({
          headers: result.meta.fields || [],
          rows: result.data,
        });
      },
    });
  }, []);

  const handleFileChange = useCallback((f: File | null) => {
    setFile(f);
    if (f) {
      parsePreview(f);
    } else {
      setPreview(null);
    }
  }, [parsePreview]);

  const missingColumns = preview
    ? EXPECTED_COLUMNS.filter((col) => !preview.headers.includes(col))
    : [];

  const handleCreate = async () => {
    if (!name.trim()) {
      toast.error("Dataset name is required");
      return;
    }

    setLoading(true);
    try {
      const ds = await createDataset({ name: name.trim(), description });

      if (file) {
        const formData = new FormData();
        formData.append("file", file);
        const result = await importDatasetCsv(ds.id, formData);
        toast.success(`Created "${name}" with ${result.rows_added} rows`);
      } else {
        toast.success(`Created empty dataset "${name}"`);
      }

      onCreated(ds.id);
      setName("");
      setDescription("");
      setFile(null);
      setPreview(null);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to create dataset");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="bg-clay-800 border-clay-600 text-clay-100 sm:max-w-lg">
        <DialogHeader>
          <DialogTitle className="text-clay-100">New Dataset</DialogTitle>
        </DialogHeader>

        <div className="flex flex-col gap-4 mt-2">
          <div>
            <label className="text-sm font-medium text-clay-200">Name</label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Q2 Outbound List"
              className="mt-1 bg-clay-700 border-clay-600 text-clay-100"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-clay-200">Description (optional)</label>
            <Input
              value={description}
              onChange={(e) => setDescription(e.target.value)}
              placeholder="What this dataset is for..."
              className="mt-1 bg-clay-700 border-clay-600 text-clay-100"
            />
          </div>

          <div>
            <label className="text-sm font-medium text-clay-200">Import CSV (optional)</label>
            <input
              ref={fileRef}
              type="file"
              accept=".csv"
              className="hidden"
              onChange={(e) => handleFileChange(e.target.files?.[0] ?? null)}
            />
            <Button
              variant="outline"
              className="mt-1 w-full border-dashed border-clay-500 text-clay-200 hover:bg-clay-700 min-h-[48px]"
              onClick={() => fileRef.current?.click()}
              onDragOver={(e) => {
                e.preventDefault();
                e.currentTarget.classList.add("border-kiln-teal", "bg-kiln-teal/5");
              }}
              onDragLeave={(e) => {
                e.currentTarget.classList.remove("border-kiln-teal", "bg-kiln-teal/5");
              }}
              onDrop={(e) => {
                e.preventDefault();
                e.currentTarget.classList.remove("border-kiln-teal", "bg-kiln-teal/5");
                const f = e.dataTransfer.files[0];
                if (f && f.name.endsWith(".csv")) {
                  handleFileChange(f);
                } else {
                  toast.error("Please drop a .csv file");
                }
              }}
            >
              {file ? (
                <span className="flex items-center gap-2">
                  <FileSpreadsheet className="h-4 w-4 text-kiln-teal" />
                  {file.name}
                </span>
              ) : (
                <span className="flex items-center gap-2">
                  <Upload className="h-4 w-4" />
                  Drop CSV here or click to browse...
                </span>
              )}
            </Button>
          </div>

          {/* CSV Preview */}
          {preview && (
            <div className="border border-clay-600 rounded-lg overflow-hidden">
              <div className="px-3 py-1.5 bg-clay-750 border-b border-clay-600 flex items-center justify-between">
                <span className="text-xs text-clay-300">
                  Preview: {preview.headers.length} columns, first {preview.rows.length} rows
                </span>
                {missingColumns.length > 0 && (
                  <div className="flex items-center gap-1">
                    <AlertTriangle className="h-3 w-3 text-kiln-mustard" />
                    <span className="text-[10px] text-kiln-mustard">Missing columns</span>
                  </div>
                )}
              </div>

              {/* Missing column warnings */}
              {missingColumns.length > 0 && (
                <div className="px-3 py-2 bg-kiln-mustard/5 border-b border-clay-600 flex flex-wrap gap-1">
                  {missingColumns.map((col) => (
                    <Badge
                      key={col}
                      variant="outline"
                      className="text-[10px] border-kiln-mustard/30 text-kiln-mustard"
                    >
                      {col}
                    </Badge>
                  ))}
                </div>
              )}

              {/* Mini table */}
              <div className="overflow-x-auto max-h-[160px]">
                <table className="w-full text-xs">
                  <thead>
                    <tr className="border-b border-clay-600">
                      {preview.headers.slice(0, 6).map((h) => (
                        <th key={h} className="px-2 py-1 text-left text-clay-300 font-medium whitespace-nowrap">
                          {h}
                        </th>
                      ))}
                      {preview.headers.length > 6 && (
                        <th className="px-2 py-1 text-left text-clay-400">
                          +{preview.headers.length - 6}
                        </th>
                      )}
                    </tr>
                  </thead>
                  <tbody>
                    {preview.rows.map((row, i) => (
                      <tr key={i} className="border-b border-clay-700">
                        {preview.headers.slice(0, 6).map((h) => (
                          <td key={h} className="px-2 py-1 text-clay-200 max-w-[120px] truncate">
                            {row[h] || "\u2014"}
                          </td>
                        ))}
                        {preview.headers.length > 6 && (
                          <td className="px-2 py-1 text-clay-400">...</td>
                        )}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

          <Button
            onClick={handleCreate}
            disabled={loading || !name.trim()}
            className="bg-kiln-teal text-clay-900 hover:bg-kiln-teal/90"
          >
            {loading ? "Creating..." : file ? "Create & Import" : "Create Empty"}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
}
