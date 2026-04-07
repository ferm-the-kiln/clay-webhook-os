"use client";

import { useRef, useState, useCallback, useEffect } from "react";
import { Upload, FileSpreadsheet, ClipboardPaste, Clock, Download } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
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

interface EnrichHistoryEntry {
  id: string;
  name: string;
  rows: number;
  recipes: string[];
  timestamp: number;
}

const SAMPLE_CSV = `first_name,last_name,domain,company_name,title
Jane,Smith,acme.com,Acme Corp,VP of Sales
John,Doe,globex.net,Globex Inc,Director of Marketing
Sarah,Lee,initech.io,Initech,Head of Growth
Mike,Chen,waystar.com,Waystar Royco,CRO
Lisa,Park,hooli.xyz,Hooli,VP Engineering`;

function formatRelativeTime(timestamp: number): string {
  const seconds = Math.floor((Date.now() - timestamp) / 1000);
  if (seconds < 60) return "just now";
  const minutes = Math.floor(seconds / 60);
  if (minutes < 60) return `${minutes}m ago`;
  const hours = Math.floor(minutes / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export function StepUpload({ preview, onParsed, onClear }: StepUploadProps) {
  const fileInputRef = useRef<HTMLInputElement>(null);
  const [parsing, setParsing] = useState(false);
  const [mode, setMode] = useState<"file" | "paste">("file");
  const [pasteText, setPasteText] = useState("");
  const [history, setHistory] = useState<EnrichHistoryEntry[]>([]);

  // Load history from localStorage
  useEffect(() => {
    try {
      const raw = localStorage.getItem("enrich-history");
      if (raw) setHistory(JSON.parse(raw).slice(0, 3));
    } catch {}
  }, []);

  const parseFile = useCallback(
    (file: File) => {
      setParsing(true);
      Papa.parse(file, {
        preview: 6,
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

  const handleParsePaste = useCallback(() => {
    if (!pasteText.trim()) return;
    setParsing(true);
    // Detect delimiter: tabs or commas
    const delimiter = pasteText.includes("\t") ? "\t" : ",";
    Papa.parse(pasteText, {
      delimiter,
      header: false,
      skipEmptyLines: true,
      complete: (result) => {
        const allRows = result.data as string[][];
        if (allRows.length < 2) {
          setParsing(false);
          return;
        }
        const headers = allRows[0];
        const dataRows = allRows.slice(1);
        const file = new File([pasteText], "pasted-data.csv", { type: "text/csv" });
        onParsed({
          file,
          headers,
          rows: dataRows.slice(0, 5),
          totalRows: dataRows.length,
        });
        setParsing(false);
      },
    });
  }, [pasteText, onParsed]);

  const handleDownloadSample = useCallback(() => {
    const blob = new Blob([SAMPLE_CSV], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = "sample-enrichment-data.csv";
    a.click();
    URL.revokeObjectURL(url);
  }, []);

  const pasteRowCount = pasteText.trim()
    ? pasteText.trim().split("\n").length - 1
    : 0;

  return (
    <div className="space-y-6">
      <div className="text-center space-y-1">
        <h2 className="text-lg font-semibold text-clay-100">Upload your CSV</h2>
        <p className="text-sm text-clay-400">
          Drop a file with your contacts or companies to get started.
        </p>
      </div>

      {/* Mode toggle */}
      {!preview && (
        <div className="flex justify-center">
          <div className="inline-flex rounded-lg bg-clay-800 p-0.5 border border-clay-700">
            <button
              onClick={() => setMode("file")}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                mode === "file"
                  ? "bg-clay-700 text-clay-100"
                  : "text-clay-400 hover:text-clay-200",
              )}
            >
              <Upload className="h-3 w-3" />
              Upload File
            </button>
            <button
              onClick={() => setMode("paste")}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                mode === "paste"
                  ? "bg-clay-700 text-clay-100"
                  : "text-clay-400 hover:text-clay-200",
              )}
            >
              <ClipboardPaste className="h-3 w-3" />
              Paste Data
            </button>
          </div>
        </div>
      )}

      {/* File upload mode */}
      {mode === "file" && (
        <>
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

          {/* Sample CSV download */}
          {!preview && (
            <div className="text-center">
              <button
                onClick={handleDownloadSample}
                className="inline-flex items-center gap-1 text-xs text-clay-500 hover:text-clay-300 transition-colors"
              >
                <Download className="h-3 w-3" />
                Need a template? Download sample CSV
              </button>
            </div>
          )}
        </>
      )}

      {/* Paste mode */}
      {mode === "paste" && !preview && (
        <div className="space-y-3">
          <textarea
            value={pasteText}
            onChange={(e) => setPasteText(e.target.value)}
            placeholder="Paste rows from a spreadsheet (tab-separated or comma-separated)..."
            className="w-full h-40 rounded-lg border border-clay-600 bg-clay-800/50 px-4 py-3 text-xs font-mono text-clay-200 placeholder:text-clay-500 focus:border-kiln-teal/50 focus:outline-none focus:ring-1 focus:ring-kiln-teal/20 resize-none"
          />
          {pasteRowCount > 0 && (
            <div className="flex items-center justify-between">
              <span className="text-xs text-clay-500">
                {pasteRowCount} data row{pasteRowCount !== 1 ? "s" : ""} detected
              </span>
              <button
                onClick={handleParsePaste}
                className="px-3 py-1.5 rounded-md bg-kiln-teal text-black text-xs font-medium hover:bg-kiln-teal/90 transition-colors"
              >
                Parse {pasteRowCount} rows
              </button>
            </div>
          )}
        </div>
      )}

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

      {/* Enrichment history */}
      {!preview && history.length > 0 && (
        <div className="space-y-2 pt-2">
          <div className="text-[10px] text-clay-500 uppercase tracking-wider font-medium">
            Recent enrichments
          </div>
          <div className="space-y-1.5">
            {history.map((entry) => (
              <button
                key={entry.id + entry.timestamp}
                onClick={() => window.open(`/tables/${entry.id}`, "_blank")}
                className="w-full flex items-center gap-3 p-2.5 rounded-md border border-clay-700 bg-clay-800/30 hover:bg-clay-800/60 hover:border-clay-600 transition-colors text-left"
              >
                <Clock className="h-3.5 w-3.5 text-clay-500 shrink-0" />
                <div className="flex-1 min-w-0">
                  <div className="text-xs text-clay-200 truncate">{entry.name}</div>
                  <div className="flex items-center gap-1.5 mt-0.5">
                    <Badge variant="secondary" className="text-[9px] py-0 h-3.5 bg-clay-700/50 text-clay-400 border-clay-600">
                      {entry.rows} rows
                    </Badge>
                    {entry.recipes.slice(0, 2).map((r) => (
                      <Badge key={r} variant="secondary" className="text-[9px] py-0 h-3.5 bg-clay-700/50 text-clay-400 border-clay-600">
                        {r}
                      </Badge>
                    ))}
                    {entry.recipes.length > 2 && (
                      <span className="text-[9px] text-clay-500">+{entry.recipes.length - 2}</span>
                    )}
                  </div>
                </div>
                <span className="text-[10px] text-clay-500 shrink-0">
                  {formatRelativeTime(entry.timestamp)}
                </span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
