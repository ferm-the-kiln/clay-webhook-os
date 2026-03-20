"use client";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { RotateCcw, Send, Download, X, AlertCircle } from "lucide-react";

export function SpreadsheetToolbar({
  statusFilter,
  onStatusFilterChange,
  globalFilter,
  onGlobalFilterChange,
  selectedCount,
  failedCount,
  onRetrySelected,
  onPushSelected,
  onExportSelected,
  onSelectAllFailed,
  onClearSelection,
  onDownloadAll,
  totalRows,
  completedCount,
}: {
  statusFilter: string;
  onStatusFilterChange: (status: string) => void;
  globalFilter: string;
  onGlobalFilterChange: (filter: string) => void;
  selectedCount: number;
  failedCount: number;
  onRetrySelected?: () => void;
  onPushSelected?: () => void;
  onExportSelected?: () => void;
  onSelectAllFailed?: () => void;
  onClearSelection: () => void;
  onDownloadAll: () => void;
  totalRows: number;
  completedCount?: number;
}) {
  const hasSelection = selectedCount > 0;

  return (
    <div className="flex items-center gap-2 px-4 py-2 border-b border-clay-500 bg-clay-800/50">
      {hasSelection ? (
        // Bulk action mode
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
          {onRetrySelected && (
            <Button
              variant="outline"
              size="sm"
              onClick={onRetrySelected}
              className="h-7 bg-kiln-coral/10 text-kiln-coral border-kiln-coral/30 hover:bg-kiln-coral/20"
            >
              <RotateCcw className="h-3 w-3 mr-1" />
              Retry
            </Button>
          )}
          {onPushSelected && (
            <Button
              variant="outline"
              size="sm"
              onClick={onPushSelected}
              className="h-7 bg-kiln-mustard/10 text-kiln-mustard border-kiln-mustard/30 hover:bg-kiln-mustard/20"
            >
              <Send className="h-3 w-3 mr-1" />
              Push
            </Button>
          )}
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
        // Filter mode
        <>
          <Select value={statusFilter} onValueChange={onStatusFilterChange}>
            <SelectTrigger className="w-32 h-7 text-xs border-clay-700 bg-clay-800 text-clay-300">
              <SelectValue placeholder="All statuses" />
            </SelectTrigger>
            <SelectContent className="border-clay-700 bg-clay-800">
              <SelectItem value="all">All statuses</SelectItem>
              <SelectItem value="completed">Completed</SelectItem>
              <SelectItem value="failed">Failed</SelectItem>
              <SelectItem value="processing">Processing</SelectItem>
              <SelectItem value="queued">Queued</SelectItem>
            </SelectContent>
          </Select>

          <Input
            placeholder="Search rows..."
            value={globalFilter}
            onChange={(e) => onGlobalFilterChange(e.target.value)}
            className="h-7 w-48 text-xs border-clay-700 bg-clay-800 text-clay-200 placeholder:text-clay-300"
          />

          <div className="ml-auto flex items-center gap-2">
            {failedCount > 0 && onSelectAllFailed && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onSelectAllFailed}
                className="h-7 text-xs text-kiln-coral hover:text-kiln-coral/80"
              >
                <AlertCircle className="h-3 w-3 mr-1" />
                Select failed ({failedCount})
              </Button>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={onDownloadAll}
              className="h-7 text-xs bg-kiln-teal/10 text-kiln-teal border-kiln-teal/30 hover:bg-kiln-teal/20"
            >
              <Download className="h-3 w-3 mr-1" />
              {completedCount !== undefined && completedCount < totalRows
                ? `Export ${completedCount} completed`
                : `CSV (${totalRows})`}
            </Button>
          </div>
        </>
      )}
    </div>
  );
}
