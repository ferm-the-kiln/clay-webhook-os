"use client";

import type { FileNode } from "@/lib/types";
import type { ViewMode } from "@/hooks/use-file-explorer";
import { FileGridItem } from "./file-grid-item";
import { FileListRow } from "./file-list-row";
import { EmptyState } from "@/components/ui/empty-state";
import { FolderOpen } from "lucide-react";
import { cn } from "@/lib/utils";

interface FileGridProps {
  items: FileNode[];
  viewMode: ViewMode;
  selectedFileId: string | null;
  renamingId: string | null;
  selectedIds: Set<string>;
  usageMap: Record<string, string[]>;
  onSelect: (id: string) => void;
  onDoubleClick: (id: string) => void;
  onNavigate: (id: string) => void;
  onRename: (id: string, newName: string) => void;
  onToggleSelect: (id: string, multi: boolean) => void;
  onContextMenu: (e: React.MouseEvent, node: FileNode) => void;
}

export function FileGrid({
  items,
  viewMode,
  selectedFileId,
  renamingId,
  selectedIds,
  usageMap,
  onSelect,
  onDoubleClick,
  onNavigate,
  onRename,
  onToggleSelect,
  onContextMenu,
}: FileGridProps) {
  if (items.length === 0) {
    return (
      <EmptyState
        title="This folder is empty"
        description="Create a new file or drag one here."
        icon={FolderOpen}
      />
    );
  }

  if (viewMode === "list") {
    return (
      <div className="rounded-lg border border-clay-800 overflow-hidden">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-clay-800 text-left text-xs text-clay-500">
              <th className="px-3 py-2 font-medium">Name</th>
              <th className="px-3 py-2 font-medium hidden sm:table-cell">Type</th>
              <th className="px-3 py-2 font-medium hidden md:table-cell">Category</th>
              <th className="px-3 py-2 font-medium w-10" />
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <FileListRow
                key={item.id}
                node={item}
                isSelected={item.id === selectedFileId}
                isMultiSelected={selectedIds.has(item.id)}
                isRenaming={item.id === renamingId}
                onSelect={onSelect}
                onDoubleClick={onDoubleClick}
                onNavigate={onNavigate}
                onRename={onRename}
                onToggleSelect={onToggleSelect}
                onContextMenu={onContextMenu}
              />
            ))}
          </tbody>
        </table>
      </div>
    );
  }

  return (
    <div
      className={cn(
        "grid gap-3",
        "grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6"
      )}
    >
      {items.map((item) => (
        <FileGridItem
          key={item.id}
          node={item}
          isSelected={item.id === selectedFileId}
          isMultiSelected={selectedIds.has(item.id)}
          isRenaming={item.id === renamingId}
          usageMap={usageMap}
          onSelect={onSelect}
          onDoubleClick={onDoubleClick}
          onNavigate={onNavigate}
          onRename={onRename}
          onToggleSelect={onToggleSelect}
          onContextMenu={onContextMenu}
        />
      ))}
    </div>
  );
}
