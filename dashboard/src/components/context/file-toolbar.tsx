"use client";

import { LayoutGrid, List, Plus, Search, Eye } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { cn } from "@/lib/utils";
import type { ViewMode } from "@/hooks/use-file-explorer";
import type { DriveId } from "@/lib/types";

interface FileToolbarProps {
  searchQuery: string;
  onSearchChange: (q: string) => void;
  viewMode: ViewMode;
  onViewModeChange: (mode: ViewMode) => void;
  currentDriveId?: DriveId;
  onNewFile: () => void;
  onPreviewPrompt: () => void;
}

const NEW_LABELS: Record<string, string> = {
  "knowledge-base": "New File",
  clients: "New Client",
  skills: "New Skill",
};

export function FileToolbar({
  searchQuery,
  onSearchChange,
  viewMode,
  onViewModeChange,
  currentDriveId,
  onNewFile,
  onPreviewPrompt,
}: FileToolbarProps) {
  return (
    <div className="flex items-center gap-2">
      {/* Search */}
      <div className="relative flex-1 max-w-xs">
        <Search className="absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-clay-500" />
        <Input
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          placeholder="Filter files..."
          className="h-8 pl-8 text-xs bg-clay-900 border-clay-700 text-clay-200 placeholder:text-clay-600"
        />
      </div>

      {/* View toggle */}
      <div className="flex rounded-md border border-clay-700">
        <button
          onClick={() => onViewModeChange("grid")}
          className={cn(
            "p-1.5 transition-colors",
            viewMode === "grid"
              ? "bg-kiln-teal/10 text-kiln-teal"
              : "text-clay-500 hover:text-clay-300"
          )}
        >
          <LayoutGrid className="h-3.5 w-3.5" />
        </button>
        <button
          onClick={() => onViewModeChange("list")}
          className={cn(
            "p-1.5 transition-colors border-l border-clay-700",
            viewMode === "list"
              ? "bg-kiln-teal/10 text-kiln-teal"
              : "text-clay-500 hover:text-clay-300"
          )}
        >
          <List className="h-3.5 w-3.5" />
        </button>
      </div>

      {/* Preview Prompt */}
      <Button
        variant="outline"
        size="sm"
        onClick={onPreviewPrompt}
        className="h-8 text-xs border-clay-700 text-clay-300 hover:bg-clay-800"
      >
        <Eye className="h-3.5 w-3.5 mr-1.5" />
        Preview
      </Button>

      {/* New file */}
      {currentDriveId && (
        <Button
          size="sm"
          onClick={onNewFile}
          className="h-8 text-xs bg-kiln-teal text-clay-950 hover:bg-kiln-teal/80"
        >
          <Plus className="h-3.5 w-3.5 mr-1" />
          {NEW_LABELS[currentDriveId] || "New"}
        </Button>
      )}
    </div>
  );
}
