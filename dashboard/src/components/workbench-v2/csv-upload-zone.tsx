"use client";

import type { FunctionDefinition } from "@/lib/types";
import type { CsvData } from "@/hooks/use-function-workbench";
import { cn } from "@/lib/utils";
import { Upload, FileSpreadsheet, Info } from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface CsvUploadZoneProps {
  csvData: CsvData | null;
  fileInputRef: React.RefObject<HTMLInputElement | null>;
  onFileUpload: (file: File) => void;
  onDrop: (e: React.DragEvent) => void;
  onClear: () => void;
  selectedFunction?: FunctionDefinition | null;
}

export function CsvUploadZone({
  csvData,
  fileInputRef,
  onFileUpload,
  onDrop,
  onClear,
  selectedFunction,
}: CsvUploadZoneProps) {
  const requiredFields = selectedFunction?.inputs.filter((i) => i.required) ?? [];
  const optionalFields = selectedFunction?.inputs.filter((i) => !i.required) ?? [];

  return (
    <div className="space-y-3">
      {/* Expected columns info card */}
      {selectedFunction && !csvData && requiredFields.length > 0 && (
        <div className="flex gap-3 rounded-lg bg-clay-800/60 border border-clay-700/50 px-4 py-3">
          <Info className="h-4 w-4 text-kiln-teal shrink-0 mt-0.5" />
          <div className="space-y-2 min-w-0">
            <div className="text-xs font-medium text-clay-200">
              Your CSV should include these columns
            </div>
            <div className="flex flex-wrap gap-1.5">
              {requiredFields.map((f) => (
                <Badge
                  key={f.name}
                  className="text-[11px] bg-kiln-teal/10 text-kiln-teal border-kiln-teal/25 font-mono"
                >
                  {f.name}
                </Badge>
              ))}
              {optionalFields.map((f) => (
                <Badge
                  key={f.name}
                  variant="secondary"
                  className="text-[11px] font-mono text-clay-300"
                >
                  {f.name}
                  <span className="ml-1 text-clay-300 font-sans">optional</span>
                </Badge>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Drop zone */}
      <div
        onDrop={onDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          "border-2 border-dashed rounded-xl p-12 text-center cursor-pointer transition-colors",
          csvData
            ? "border-kiln-teal/30 bg-kiln-teal/5"
            : "border-clay-600 hover:border-clay-500 hover:bg-clay-800/50"
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) onFileUpload(file);
          }}
        />
        {csvData ? (
          <div className="space-y-2">
            <FileSpreadsheet className="h-10 w-10 text-kiln-teal mx-auto" />
            <div className="text-sm font-medium text-clay-100">
              {csvData.fileName}
            </div>
            <div className="text-xs text-clay-300">
              {csvData.totalRows} rows, {csvData.headers.length} columns
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onClear();
              }}
              className="text-xs text-clay-300 hover:text-clay-200 underline"
            >
              Upload different file
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <Upload className="h-10 w-10 text-clay-300 mx-auto" />
            <div className="text-sm text-clay-200">
              Drag and drop a CSV file here
            </div>
            <div className="text-xs text-clay-300">or click to browse</div>
          </div>
        )}
      </div>
    </div>
  );
}
