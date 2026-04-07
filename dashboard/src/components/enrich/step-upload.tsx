"use client";

import { useRef, useState, useCallback } from "react";
import { Upload, FileSpreadsheet } from "lucide-react";
import { cn } from "@/lib/utils";
import Papa from "papaparse";

export interface CsvPreview {
  file: File;
  headers: string[];
  rows: string[][];
  totalRows: number;
}

interface StepUploadProps {
  preview: CsvPreview | null;
  onParsed: (preview: CsvPreview) => void;
  onClear: () => void;
}

export function StepUpload({ preview, onParsed, onClear }: StepUploadProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [parsing, setParsing] = useState(false);

  const parseFile = useCallback(
    (file: File) => {
      setParsing(true);
      Papa.parse(file, {
        preview: 6, // header + 5 data rows
        header: false,
        skipEmptyLines: true,
        complete: (result) => {
          const allRows = result.data as string[][];
          if (allRows.length === 0) {
            setParsing(false);
            return;
          }
          const headers = allRows[0];
          const dataRows = allRows.slice(1);
          // Get total count
          Papa.parse(file, {
            header: false,
            skipEmptyLines: true,
            complete: (full) => {
              onParsed({
                file,
                headers,
                rows: dataRows,
                totalRows: (full.data as string[][]).length - 1,
              });
              setParsing(false);
            },
          });
        },
      });
    },
    [onParsed],
  );

  const handleDrop = useCallback(
    (e: React.DragEvent) => {
      e.preventDefault();
      const file = e.dataTransfer.files[0];
      if (file?.name.endsWith(".csv")) parseFile(file);
    },
    [parseFile],
  );

  return (
    <div className="space-y-6">
      <div className="text-center space-y-1">
        <h2 className="text-lg font-semibold text-clay-100">Upload your CSV</h2>
        <p className="text-sm text-clay-400">
          Drop a file with your contacts or companies to get started.
        </p>
      </div>

      {/* Drop zone */}
      <div
        onDrop={handleDrop}
        onDragOver={(e) => e.preventDefault()}
        onClick={() => fileInputRef.current?.click()}
        className={cn(
          "border-2 border-dashed rounded-xl p-16 text-center cursor-pointer transition-all duration-200",
          preview
            ? "border-kiln-teal/30 bg-kiln-teal/5"
            : "border-clay-600 hover:border-clay-500 hover:bg-clay-800/50",
        )}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) parseFile(file);
          }}
        />
        {parsing ? (
          <div className="space-y-2">
            <div className="h-10 w-10 mx-auto rounded-full border-2 border-kiln-teal border-t-transparent animate-spin" />
            <div className="text-sm text-clay-300">Reading file...</div>
          </div>
        ) : preview ? (
          <div className="space-y-2">
            <FileSpreadsheet className="h-10 w-10 text-kiln-teal mx-auto" />
            <div className="text-sm font-medium text-clay-100">
              {preview.file.name}
            </div>
            <div className="text-xs text-clay-400">
              {preview.totalRows.toLocaleString()} rows, {preview.headers.length} columns
            </div>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onClear();
              }}
              className="text-xs text-clay-400 hover:text-clay-200 underline mt-1"
            >
              Upload different file
            </button>
          </div>
        ) : (
          <div className="space-y-2">
            <Upload className="h-10 w-10 text-clay-400 mx-auto" />
            <div className="text-sm text-clay-200">
              Drag and drop a CSV file here
            </div>
            <div className="text-xs text-clay-400">or click to browse</div>
          </div>
        )}
      </div>

      {/* Preview table */}
      {preview && (
        <div>
          <h3 className="text-xs font-medium text-clay-400 mb-2">
            Preview (first {preview.rows.length} rows)
          </h3>
          <div className="rounded-md border border-clay-700 overflow-x-auto">
            <table className="w-full text-xs">
              <thead>
                <tr>
                  {preview.headers.map((h, i) => (
                    <th
                      key={i}
                      className="px-3 py-1.5 text-left text-clay-400 font-medium border-b border-clay-700 bg-clay-800/50 whitespace-nowrap"
                    >
                      {h}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {preview.rows.map((row, ri) => (
                  <tr key={ri} className="border-b border-clay-800/50 last:border-0">
                    {row.map((cell, ci) => (
                      <td
                        key={ci}
                        className="px-3 py-1.5 text-clay-300 whitespace-nowrap max-w-[200px] truncate"
                      >
                        {cell || <span className="text-clay-600">&mdash;</span>}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
  );
}
