"use client";

import { useState, useCallback } from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Upload, FileSpreadsheet, Database } from "lucide-react";
import type { DatasetSummary } from "@/lib/types";

interface UploadPhaseProps {
  datasets: DatasetSummary[];
  onUpload: (file: File, name: string) => void;
  onSelectDataset: (id: string) => void;
  error: string | null;
}

export function UploadPhase({ datasets, onUpload, onSelectDataset, error }: UploadPhaseProps) {
  const [file, setFile] = useState<File | null>(null);
  const [name, setName] = useState("");
  const [dragOver, setDragOver] = useState(false);

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault();
    setDragOver(false);
    const dropped = e.dataTransfer.files[0];
    if (dropped && dropped.name.endsWith(".csv")) {
      setFile(dropped);
      if (!name) setName(dropped.name.replace(/\.csv$/i, ""));
    }
  }, [name]);

  const handleFileChange = useCallback((e: React.ChangeEvent<HTMLInputElement>) => {
    const selected = e.target.files?.[0];
    if (selected) {
      setFile(selected);
      if (!name) setName(selected.name.replace(/\.csv$/i, ""));
    }
  }, [name]);

  return (
    <div className="space-y-6">
      {/* Upload new CSV */}
      <div>
        <h3 className="text-sm font-medium text-clay-200 mb-3">Upload CSV</h3>
        <div
          onDragOver={(e) => { e.preventDefault(); setDragOver(true); }}
          onDragLeave={() => setDragOver(false)}
          onDrop={handleDrop}
          className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
            dragOver ? "border-kiln-amber bg-kiln-amber/5" : "border-clay-600 hover:border-clay-500"
          }`}
        >
          <Upload className="h-8 w-8 mx-auto mb-3 text-clay-300" />
          <p className="text-sm text-clay-300 mb-2">
            {file ? file.name : "Drop a CSV file here, or click to browse"}
          </p>
          <input
            type="file"
            accept=".csv"
            onChange={handleFileChange}
            className="hidden"
            id="csv-upload"
          />
          <label htmlFor="csv-upload">
            <Button variant="outline" size="sm" className="cursor-pointer" asChild>
              <span>Browse Files</span>
            </Button>
          </label>
        </div>

        {file && (
          <div className="mt-3 flex items-center gap-3">
            <Input
              placeholder="Dataset name"
              value={name}
              onChange={(e) => setName(e.target.value)}
              className="flex-1"
            />
            <Button
              onClick={() => onUpload(file, name || file.name.replace(/\.csv$/i, ""))}
              className="bg-kiln-amber text-clay-900 hover:bg-kiln-amber/90 font-semibold"
              disabled={!name.trim()}
            >
              <FileSpreadsheet className="h-4 w-4 mr-2" />
              Upload & Analyze
            </Button>
          </div>
        )}

        {error && (
          <p className="mt-2 text-sm text-red-400">{error}</p>
        )}
      </div>

      {/* Or pick existing dataset */}
      {datasets.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-clay-200 mb-3">Or use existing dataset</h3>
          <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
            {datasets.map((ds) => (
              <Card
                key={ds.id}
                className="rounded-xl cursor-pointer hover:border-kiln-amber/50 transition-colors"
                onClick={() => onSelectDataset(ds.id)}
              >
                <CardContent className="pt-4 pb-4">
                  <div className="flex items-center gap-2 mb-1">
                    <Database className="h-4 w-4 text-kiln-amber" />
                    <span className="text-sm font-medium text-clay-100 truncate">{ds.name}</span>
                  </div>
                  <span className="text-xs text-clay-300">
                    {ds.row_count} rows &middot; {ds.column_count} columns
                  </span>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
