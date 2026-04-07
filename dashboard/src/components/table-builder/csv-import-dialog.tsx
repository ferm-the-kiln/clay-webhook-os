"use client";

import { useState, useEffect, useCallback } from "react";
import { Dialog as DialogPrimitive } from "radix-ui";
import {
  Upload,
  ArrowRight,
  X,
  FileSpreadsheet,
  Check,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import Papa from "papaparse";
import type { TableDefinition, FunctionDefinition } from "@/lib/types";
import { fetchFunction } from "@/lib/api";
import { autoMapHeaders, type MappingTarget, type MatchConfidence } from "@/lib/csv-utils";

interface CsvImportDialogProps {
  open: boolean;
  onClose: () => void;
  onImport: (file: File, mapping?: Record<string, string>) => Promise<void>;
  table: TableDefinition;
  file: File | null;
}

interface CsvPreview {
  headers: string[];
  rows: string[][];
  totalRows: number;
}

export function CsvImportDialog({
  open,
  onClose,
  onImport,
  table,
  file,
}: CsvImportDialogProps) {
  const [preview, setPreview] = useState<CsvPreview | null>(null);
  const [funcDef, setFuncDef] = useState<FunctionDefinition | null>(null);
  // mappings: { targetId: csvHeader }
  const [mappings, setMappings] = useState<Record<string, string>>({});
  const [confidence, setConfidence] = useState<Record<string, MatchConfidence>>({});
  const [importing, setImporting] = useState(false);

  // Build mapping targets from function inputs OR existing table input columns
  const existingInputCols = table.columns.filter(
    (c) => c.column_type === "input",
  );

  const mappingTargets: MappingTarget[] = funcDef
    ? funcDef.inputs.map((i) => ({
        id: i.name,
        name: i.name,
        type: i.type,
        required: i.required,
        description: i.description,
      }))
    : existingInputCols.map((c) => ({
        id: c.id,
        name: c.name,
        type: "string",
        required: true,
        description: "",
      }));

  const hasMappingTargets = mappingTargets.length > 0;

  // Parse CSV preview when file changes
  useEffect(() => {
    if (!file || !open) {
      setPreview(null);
      return;
    }
    Papa.parse(file, {
      preview: 5,
      header: false,
      skipEmptyLines: true,
      complete: (result) => {
        const allRows = result.data as string[][];
        if (allRows.length === 0) return;
        const headers = allRows[0];
        const dataRows = allRows.slice(1);
        // Get total count by re-parsing just for count
        Papa.parse(file, {
          header: false,
          skipEmptyLines: true,
          complete: (full) => {
            setPreview({
              headers,
              rows: dataRows,
              totalRows: (full.data as string[][]).length - 1, // minus header
            });
          },
        });
      },
    });
  }, [file, open]);

  // Fetch function definition if table is linked to a function
  useEffect(() => {
    if (!open || !table.source_function_id) {
      setFuncDef(null);
      return;
    }
    fetchFunction(table.source_function_id)
      .then(setFuncDef)
      .catch(() => setFuncDef(null));
  }, [open, table.source_function_id]);

  // Auto-map when preview is ready and we have targets
  useEffect(() => {
    if (!preview || mappingTargets.length === 0) {
      setMappings({});
      setConfidence({});
      return;
    }
    const result = autoMapHeaders(mappingTargets, preview.headers);
    setMappings(result.mappings);
    setConfidence(result.confidence);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [preview, funcDef, existingInputCols.length]);

  const handleMapColumn = useCallback(
    (targetId: string, csvHeader: string) => {
      setMappings((prev) => ({ ...prev, [targetId]: csvHeader }));
      setConfidence((prev) => ({ ...prev, [targetId]: "exact" as MatchConfidence }));
    },
    [],
  );

  const handleClearMapping = useCallback((targetId: string) => {
    setMappings((prev) => {
      const next = { ...prev };
      delete next[targetId];
      return next;
    });
    setConfidence((prev) => {
      const next = { ...prev };
      delete next[targetId];
      return next;
    });
  }, []);

  const handleImport = async () => {
    if (!file) return;
    setImporting(true);
    try {
      // Build column mapping: { csvHeader: targetColumnId }
      let columnMapping: Record<string, string> | undefined;
      if (hasMappingTargets && Object.keys(mappings).length > 0) {
        columnMapping = {};
        for (const [targetId, csvHeader] of Object.entries(mappings)) {
          // targetId is already the column ID (from table columns or slugified function input)
          const colId = funcDef
            ? targetId.toLowerCase().replace(/[-\s]+/g, "_")
            : targetId; // existing table columns already have proper IDs
          columnMapping[csvHeader] = colId;
        }
      }
      await onImport(file, columnMapping);
      onClose();
    } finally {
      setImporting(false);
    }
  };

  // Check required targets are mapped
  const requiredTargets = mappingTargets.filter((t) => t.required);
  const unmappedRequired = requiredTargets.filter((t) => !mappings[t.id]);
  const allRequiredMapped = unmappedRequired.length === 0;

  // CSV headers that are mapped
  const mappedHeaders = new Set(Object.values(mappings));
  const unmappedHeaders = preview?.headers.filter((h) => !mappedHeaders.has(h)) || [];

  return (
    <DialogPrimitive.Root open={open} onOpenChange={(o) => !o && onClose()}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 bg-black/60 z-50" />
        <DialogPrimitive.Content className="fixed top-[10%] left-1/2 -translate-x-1/2 w-full max-w-2xl z-50 bg-zinc-900 border border-zinc-700 rounded-lg shadow-2xl overflow-hidden max-h-[80vh] flex flex-col">
          <DialogPrimitive.Title className="sr-only">Import CSV</DialogPrimitive.Title>
          <DialogPrimitive.Description className="sr-only">
            Preview and map CSV columns before importing
          </DialogPrimitive.Description>

          {/* Header */}
          <div className="flex items-center justify-between px-5 py-3 border-b border-zinc-800">
            <div className="flex items-center gap-2">
              <FileSpreadsheet className="w-4 h-4 text-kiln-teal" />
              <span className="text-sm font-medium text-white">Import CSV</span>
              {preview && (
                <span className="text-xs text-zinc-500 bg-zinc-800 px-2 py-0.5 rounded-full">
                  {preview.totalRows} rows
                </span>
              )}
            </div>
            <button onClick={onClose} className="text-zinc-500 hover:text-zinc-300">
              <X className="w-4 h-4" />
            </button>
          </div>

          <div className="overflow-y-auto flex-1 p-5 space-y-5">
            {/* Section A: CSV Preview */}
            {preview && (
              <div>
                <h3 className="text-xs font-medium text-zinc-400 mb-2">Preview</h3>
                <div className="rounded-md border border-zinc-800 overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead>
                      <tr>
                        {preview.headers.map((h, i) => (
                          <th
                            key={i}
                            className="px-3 py-1.5 text-left text-zinc-400 font-medium border-b border-zinc-800 bg-zinc-800/50 whitespace-nowrap"
                          >
                            {h}
                          </th>
                        ))}
                      </tr>
                    </thead>
                    <tbody>
                      {preview.rows.map((row, ri) => (
                        <tr key={ri} className="border-b border-zinc-800/50 last:border-0">
                          {row.map((cell, ci) => (
                            <td
                              key={ci}
                              className="px-3 py-1.5 text-zinc-300 whitespace-nowrap max-w-[200px] truncate"
                            >
                              {cell || <span className="text-zinc-600">—</span>}
                            </td>
                          ))}
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Section B: Column Mapping */}
            {hasMappingTargets && preview && (
              <div>
                <h3 className="text-xs font-medium text-zinc-400 mb-2">
                  Map CSV columns to table inputs
                </h3>

                {/* Required targets */}
                {requiredTargets.length > 0 && (
                  <div className="space-y-1.5 mb-3">
                    <div className="text-[10px] text-zinc-500 uppercase tracking-wider font-medium">
                      Required
                    </div>
                    {requiredTargets.map((target) => (
                      <MappingRow
                        key={target.id}
                        inputName={target.name}
                        inputType={target.type}
                        inputDescription={target.description}
                        required
                        csvHeaders={preview.headers}
                        mappedTo={mappings[target.id]}
                        matchConfidence={confidence[target.id]}
                        onMap={(csvHeader) => handleMapColumn(target.id, csvHeader)}
                        onClear={() => handleClearMapping(target.id)}
                      />
                    ))}
                  </div>
                )}

                {/* Optional targets */}
                {mappingTargets.filter((t) => !t.required).length > 0 && (
                  <div className="space-y-1.5">
                    <div className="text-[10px] text-zinc-500 uppercase tracking-wider font-medium">
                      Optional
                    </div>
                    {mappingTargets
                      .filter((t) => !t.required)
                      .map((target) => (
                        <MappingRow
                          key={target.id}
                          inputName={target.name}
                          inputType={target.type}
                          inputDescription={target.description}
                          required={false}
                          csvHeaders={preview.headers}
                          mappedTo={mappings[target.id]}
                          matchConfidence={confidence[target.id]}
                          onMap={(csvHeader) => handleMapColumn(target.id, csvHeader)}
                          onClear={() => handleClearMapping(target.id)}
                        />
                      ))}
                  </div>
                )}

                {/* Unmapped CSV columns */}
                {unmappedHeaders.length > 0 && (
                  <div className="mt-4 pt-3 border-t border-zinc-800">
                    <div className="text-[10px] text-zinc-500 uppercase tracking-wider font-medium mb-1.5">
                      Additional columns (imported as-is)
                    </div>
                    <div className="flex flex-wrap gap-1.5">
                      {unmappedHeaders.map((h) => (
                        <span
                          key={h}
                          className="text-[11px] px-2 py-0.5 rounded bg-zinc-800 text-zinc-400 border border-zinc-700"
                        >
                          {h}
                        </span>
                      ))}
                    </div>
                  </div>
                )}
              </div>
            )}

            {/* Simple mode: no targets to map to */}
            {!hasMappingTargets && preview && (
              <p className="text-xs text-zinc-500">
                {preview.headers.length} columns detected. All columns will be imported as input fields.
              </p>
            )}
          </div>

          {/* Footer */}
          <div className="flex items-center justify-between px-5 py-3 border-t border-zinc-800 bg-zinc-950/50">
            <div className="text-xs text-zinc-500">
              {hasMappingTargets && !allRequiredMapped && (
                <span className="text-amber-400">
                  {unmappedRequired.length} required input{unmappedRequired.length > 1 ? "s" : ""} unmapped
                </span>
              )}
            </div>
            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                className="border-zinc-700 text-zinc-300 h-8"
                onClick={onClose}
              >
                Cancel
              </Button>
              <Button
                size="sm"
                className="bg-kiln-teal text-black hover:bg-kiln-teal/90 h-8"
                onClick={handleImport}
                disabled={importing || !preview}
              >
                {importing ? (
                  "Importing..."
                ) : preview ? (
                  <>
                    <Upload className="w-3 h-3 mr-1" />
                    Import {preview.totalRows} rows
                  </>
                ) : (
                  "Loading..."
                )}
              </Button>
            </div>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

/**
 * A single mapping row: function input → CSV column dropdown.
 */
function MappingRow({
  inputName,
  inputType,
  inputDescription,
  required,
  csvHeaders,
  mappedTo,
  matchConfidence,
  onMap,
  onClear,
}: {
  inputName: string;
  inputType: string;
  inputDescription: string;
  required: boolean;
  csvHeaders: string[];
  mappedTo: string | undefined;
  matchConfidence: MatchConfidence | undefined;
  onMap: (csvHeader: string) => void;
  onClear: () => void;
}) {
  const isMapped = !!mappedTo;

  return (
    <div
      className={`flex items-center gap-2 p-2 rounded-md border transition-colors ${
        !isMapped && required
          ? "border-red-500/30 bg-red-500/5"
          : isMapped
            ? "border-kiln-teal/20 bg-kiln-teal/5"
            : "border-zinc-700 bg-zinc-800/30"
      }`}
    >
      {/* Confidence dot */}
      <div className="w-3 flex justify-center shrink-0">
        {matchConfidence === "exact" && (
          <div className="h-2 w-2 rounded-full bg-green-400" title="Exact match" />
        )}
        {matchConfidence === "fuzzy" && (
          <div className="h-2 w-2 rounded-full bg-yellow-400" title="Fuzzy match" />
        )}
        {!matchConfidence && !isMapped && required && (
          <div className="h-2 w-2 rounded-full bg-red-400 animate-pulse" title="Unmapped" />
        )}
      </div>

      {/* Input info */}
      <div className="flex items-center gap-1.5 min-w-0 flex-1">
        <span className="text-xs font-mono font-medium text-zinc-200 truncate">
          {inputName}
        </span>
        <span className="text-[9px] px-1 py-0 rounded bg-zinc-700 text-zinc-400 shrink-0">
          {inputType}
        </span>
        {inputDescription && (
          <span className="text-[10px] text-zinc-500 truncate hidden sm:inline">
            {inputDescription}
          </span>
        )}
      </div>

      <ArrowRight className="h-3 w-3 text-zinc-500 shrink-0" />

      {/* CSV column selector */}
      <div className="flex items-center gap-1 shrink-0">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              className={`text-xs px-2 py-1 rounded border transition-colors min-w-[140px] text-left truncate ${
                isMapped
                  ? "border-kiln-teal/30 text-kiln-teal bg-kiln-teal/5"
                  : "border-zinc-600 text-zinc-400 hover:text-zinc-300 hover:border-zinc-500"
              }`}
            >
              {mappedTo || "Select column..."}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="bg-zinc-800 border-zinc-600 max-h-48 overflow-auto">
            {csvHeaders.map((h) => (
              <DropdownMenuItem
                key={h}
                onClick={() => onMap(h)}
                className="text-xs"
              >
                {h === mappedTo && <Check className="w-3 h-3 mr-1 text-kiln-teal" />}
                {h}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        {isMapped && (
          <button
            onClick={onClear}
            className="p-0.5 text-zinc-500 hover:text-zinc-300 transition-colors"
            title="Clear mapping"
          >
            <X className="h-3 w-3" />
          </button>
        )}
      </div>
    </div>
  );
}
