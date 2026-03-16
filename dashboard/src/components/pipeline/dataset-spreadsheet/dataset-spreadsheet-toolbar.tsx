"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from "@/components/ui/popover";
import { Download, X, Columns3 } from "lucide-react";
import type { DatasetColumn } from "@/lib/types";
import type { VisibilityState } from "@tanstack/react-table";

export function DatasetSpreadsheetToolbar({
  globalFilter,
  onGlobalFilterChange,
  selectedCount,
  onClearSelection,
  onExportAll,
  onExportSelected,
  totalRows,
  columns,
  columnVisibility,
  onColumnVisibilityChange,
}: {
  globalFilter: string;
  onGlobalFilterChange: (filter: string) => void;
  selectedCount: number;
  onClearSelection: () => void;
  onExportAll?: () => void;
  onExportSelected?: () => void;
  totalRows: number;
  columns: DatasetColumn[];
  columnVisibility: VisibilityState;
  onColumnVisibilityChange: (vis: VisibilityState) => void;
}) {
  const hasSelection = selectedCount > 0;

  // Group columns by source
  const grouped: Record<string, DatasetColumn[]> = {};
  for (const col of columns) {
    if (col.name === "_row_id") continue;
    const group = col.source || "import";
    if (!grouped[group]) grouped[group] = [];
    grouped[group].push(col);
  }

  return (
    <div className="flex items-center gap-2 px-4 py-2 border-b border-clay-500 bg-clay-800/50">
      {hasSelection ? (
        <>
          <span className="text-xs text-kiln-teal font-medium">
            {selectedCount} selected
          </span>
          <Button
            variant="ghost"
            size="sm"
            onClick={onClearSelection}
            className="h-7 px-2 text-clay-200 hover:text-clay-300"
          >
            <X className="h-3 w-3 mr-1" />
            Clear
          </Button>
          <div className="w-px h-4 bg-clay-800" />
          {onExportSelected && (
            <Button
              variant="outline"
              size="sm"
              onClick={onExportSelected}
              className="h-7 bg-kiln-teal/10 text-kiln-teal border-kiln-teal/30 hover:bg-kiln-teal/20"
            >
              <Download className="h-3 w-3 mr-1" />
              Export
            </Button>
          )}
        </>
      ) : (
        <>
          <Input
            placeholder="Search rows..."
            value={globalFilter}
            onChange={(e) => onGlobalFilterChange(e.target.value)}
            className="h-7 w-48 text-xs border-clay-700 bg-clay-800 text-clay-200 placeholder:text-clay-300"
          />

          <Popover>
            <PopoverTrigger asChild>
              <Button
                variant="outline"
                size="sm"
                className="h-7 text-xs border-clay-700 text-clay-200 hover:bg-clay-700"
              >
                <Columns3 className="h-3 w-3 mr-1" />
                Columns
              </Button>
            </PopoverTrigger>
            <PopoverContent
              className="w-56 p-3 bg-clay-800 border-clay-600"
              align="start"
            >
              <p className="text-xs font-medium text-clay-200 mb-2">
                Toggle columns
              </p>
              <div className="flex flex-col gap-2 max-h-64 overflow-y-auto">
                {Object.entries(grouped).map(([source, cols]) => (
                  <div key={source}>
                    <p className="text-[10px] text-clay-400 uppercase tracking-wider mb-1">
                      {source}
                    </p>
                    {cols.map((col) => {
                      const visible = columnVisibility[col.name] !== false;
                      return (
                        <label
                          key={col.name}
                          className="flex items-center gap-2 py-0.5 text-xs text-clay-300 cursor-pointer hover:text-clay-100"
                        >
                          <input
                            type="checkbox"
                            checked={visible}
                            onChange={() => {
                              onColumnVisibilityChange({
                                ...columnVisibility,
                                [col.name]: !visible,
                              });
                            }}
                            className="h-3 w-3 rounded border-clay-600 bg-clay-800 text-kiln-teal"
                          />
                          {col.name}
                        </label>
                      );
                    })}
                  </div>
                ))}
              </div>
            </PopoverContent>
          </Popover>

          <div className="ml-auto flex items-center gap-2">
            {onExportAll && (
              <Button
                variant="outline"
                size="sm"
                onClick={onExportAll}
                className="h-7 text-xs bg-kiln-teal/10 text-kiln-teal border-kiln-teal/30 hover:bg-kiln-teal/20"
              >
                <Download className="h-3 w-3 mr-1" />
                CSV ({totalRows})
              </Button>
            )}
          </div>
        </>
      )}
    </div>
  );
}
