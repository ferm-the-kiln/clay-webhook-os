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
  Download,
} from "lucide-react";

interface RowContextMenuProps {
  children: React.ReactNode;
  selectedCount: number;
  onRunSelected: () => void;
  onRerunFailed: () => void;
  onDuplicate: () => void;
  onDelete: () => void;
  onExport: () => void;
}

export function RowContextMenu({
  children,
  selectedCount,
  onRunSelected,
  onRerunFailed,
  onDuplicate,
  onDelete,
  onExport,
}: RowContextMenuProps) {
  const label = selectedCount > 1 ? `${selectedCount} rows` : "row";

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>{children}</ContextMenuTrigger>
      <ContextMenuContent className="w-52 bg-clay-900 border-clay-500">
        <ContextMenuItem
          className="text-clay-100 text-xs"
          onClick={onRunSelected}
        >
          <Play className="w-3.5 h-3.5 mr-2 text-emerald-400" />
          Run {label}
        </ContextMenuItem>
        <ContextMenuItem
          className="text-clay-100 text-xs"
          onClick={onRerunFailed}
        >
          <RotateCcw className="w-3.5 h-3.5 mr-2 text-amber-400" />
          Re-run failed
        </ContextMenuItem>

        <ContextMenuSeparator className="bg-clay-700" />

        <ContextMenuItem
          className="text-clay-100 text-xs"
          onClick={onDuplicate}
        >
          <Copy className="w-3.5 h-3.5 mr-2" />
          Duplicate {label}
        </ContextMenuItem>
        <ContextMenuItem
          className="text-clay-100 text-xs"
          onClick={onExport}
        >
          <Download className="w-3.5 h-3.5 mr-2" />
          Export selection
        </ContextMenuItem>

        <ContextMenuSeparator className="bg-clay-700" />

        <ContextMenuItem
          className="text-red-400 text-xs"
          onClick={onDelete}
        >
          <Trash2 className="w-3.5 h-3.5 mr-2" />
          Delete {label}
        </ContextMenuItem>
      </ContextMenuContent>
    </ContextMenu>
  );
}
