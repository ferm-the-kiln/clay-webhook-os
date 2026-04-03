"use client";

import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
} from "@/components/ui/context-menu";
import {
  Play,
  RotateCcw,
  Copy,
  Trash2,
  Pencil,
  Settings2,
  EyeOff,
  ArrowLeft,
  ArrowRight,
} from "lucide-react";
import type { TableColumn } from "@/lib/types";

interface ColumnContextMenuProps {
  children: React.ReactNode;
  column: TableColumn;
  onEditConfig: () => void;
  onRename: () => void;
  onDuplicate: () => void;
  onInsertLeft: () => void;
  onInsertRight: () => void;
  onHide: () => void;
  onRunColumn: () => void;
  onRerunFailed: () => void;
  onDelete: () => void;
}

export function ColumnContextMenu({
  children,
  column,
  onEditConfig,
  onRename,
  onDuplicate,
  onInsertLeft,
  onInsertRight,
  onHide,
  onRunColumn,
  onRerunFailed,
  onDelete,
}: ColumnContextMenuProps) {
  const isEnrichment =
    column.column_type === "enrichment" || column.column_type === "ai";

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>{children}</ContextMenuTrigger>
      <ContextMenuContent className="w-52 bg-zinc-900 border-zinc-700">
        {/* Config & rename */}
        {column.column_type !== "input" && (
          <ContextMenuItem
            className="text-zinc-300 text-xs"
            onClick={onEditConfig}
          >
            <Settings2 className="w-3.5 h-3.5 mr-2 text-blue-400" />
            Edit configuration
          </ContextMenuItem>
        )}
        <ContextMenuItem
          className="text-zinc-300 text-xs"
          onClick={onRename}
        >
          <Pencil className="w-3.5 h-3.5 mr-2" />
          Rename column
        </ContextMenuItem>

        <ContextMenuSeparator className="bg-zinc-800" />

        {/* Run actions — only for enrichment/AI columns */}
        {isEnrichment && (
          <>
            <ContextMenuItem
              className="text-zinc-300 text-xs"
              onClick={onRunColumn}
            >
              <Play className="w-3.5 h-3.5 mr-2 text-emerald-400" />
              Run this column
            </ContextMenuItem>
            <ContextMenuItem
              className="text-zinc-300 text-xs"
              onClick={onRerunFailed}
            >
              <RotateCcw className="w-3.5 h-3.5 mr-2 text-amber-400" />
              Re-run failed rows
            </ContextMenuItem>
            <ContextMenuSeparator className="bg-zinc-800" />
          </>
        )}

        {/* Structure actions */}
        <ContextMenuItem
          className="text-zinc-300 text-xs"
          onClick={onDuplicate}
        >
          <Copy className="w-3.5 h-3.5 mr-2" />
          Duplicate column
        </ContextMenuItem>
        <ContextMenuItem
          className="text-zinc-300 text-xs"
          onClick={onInsertLeft}
        >
          <ArrowLeft className="w-3.5 h-3.5 mr-2" />
          Insert column left
        </ContextMenuItem>
        <ContextMenuItem
          className="text-zinc-300 text-xs"
          onClick={onInsertRight}
        >
          <ArrowRight className="w-3.5 h-3.5 mr-2" />
          Insert column right
        </ContextMenuItem>
        <ContextMenuItem
          className="text-zinc-300 text-xs"
          onClick={onHide}
        >
          <EyeOff className="w-3.5 h-3.5 mr-2" />
          Hide column
        </ContextMenuItem>

        <ContextMenuSeparator className="bg-zinc-800" />

        <ContextMenuItem
          className="text-red-400 text-xs"
          onClick={onDelete}
        >
          <Trash2 className="w-3.5 h-3.5 mr-2" />
          Delete column
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
}
