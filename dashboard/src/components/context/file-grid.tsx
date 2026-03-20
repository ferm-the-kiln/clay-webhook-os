"use client";

import type { FileNode } from "@/lib/types";
import type { ViewMode } from "@/hooks/use-file-explorer";
import { FileGridItem } from "./file-grid-item";
import { FileListRow } from "./file-list-row";
import { EmptyState } from "@/components/ui/empty-state";
import { FolderOpen } from "lucide-react";
import {
  Table,
  TableHeader,
  TableBody,
  TableHead,
  TableRow,
} from "@/components/ui/table";
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
      <Table className="text-sm">
        <TableHeader>
          <TableRow>
            <TableHead className="text-xs">Name</TableHead>
            <TableHead className="text-xs hidden sm:table-cell">Type</TableHead>
            <TableHead className="text-xs hidden md:table-cell">Category</TableHead>
            <TableHead className="w-10" />
          </TableRow>
        </TableHeader>
        <TableBody>
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
        </TableBody>
      </Table>
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
