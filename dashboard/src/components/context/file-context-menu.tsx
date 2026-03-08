"use client";

import {
  ContextMenu,
  ContextMenuContent,
  ContextMenuItem,
  ContextMenuSeparator,
  ContextMenuTrigger,
  ContextMenuShortcut,
} from "@/components/ui/context-menu";
import type { FileNode } from "@/lib/types";
import { FolderOpen, Pencil, Copy, Star, Trash2, Plus, FileText } from "lucide-react";

interface FileContextMenuProps {
  children: React.ReactNode;
  node: FileNode;
  isFavorite: boolean;
  onOpen: (id: string) => void;
  onEdit: (id: string) => void;
  onRename: (id: string) => void;
  onCopyPath: (node: FileNode) => void;
  onToggleFavorite: (id: string) => void;
  onDelete: (id: string) => void;
  onNewFile: () => void;
}

export function FileContextMenu({
  children,
  node,
  isFavorite,
  onOpen,
  onEdit,
  onRename,
  onCopyPath,
  onToggleFavorite,
  onDelete,
  onNewFile,
}: FileContextMenuProps) {
  const isFolder = node.type === "folder" || node.type === "drive";

  return (
    <ContextMenu>
      <ContextMenuTrigger asChild>{children}</ContextMenuTrigger>
      <ContextMenuContent className="w-52 bg-clay-900 border-clay-700">
        {isFolder ? (
          <>
            <ContextMenuItem
              onClick={() => onOpen(node.id)}
              className="text-clay-300 focus:bg-clay-800 focus:text-clay-200"
            >
              <FolderOpen className="mr-2 h-4 w-4" />
              Open
              <ContextMenuShortcut>Enter</ContextMenuShortcut>
            </ContextMenuItem>
            <ContextMenuItem
              onClick={onNewFile}
              className="text-clay-300 focus:bg-clay-800 focus:text-clay-200"
            >
              <Plus className="mr-2 h-4 w-4" />
              New File
            </ContextMenuItem>
            <ContextMenuSeparator className="bg-clay-800" />
            <ContextMenuItem
              onClick={() => onCopyPath(node)}
              className="text-clay-300 focus:bg-clay-800 focus:text-clay-200"
            >
              <Copy className="mr-2 h-4 w-4" />
              Copy Path
            </ContextMenuItem>
          </>
        ) : (
          <>
            <ContextMenuItem
              onClick={() => onOpen(node.id)}
              className="text-clay-300 focus:bg-clay-800 focus:text-clay-200"
            >
              <FileText className="mr-2 h-4 w-4" />
              Open
              <ContextMenuShortcut>Enter</ContextMenuShortcut>
            </ContextMenuItem>
            <ContextMenuItem
              onClick={() => onEdit(node.id)}
              className="text-clay-300 focus:bg-clay-800 focus:text-clay-200"
            >
              <Pencil className="mr-2 h-4 w-4" />
              Edit
            </ContextMenuItem>
            <ContextMenuItem
              onClick={() => onRename(node.id)}
              className="text-clay-300 focus:bg-clay-800 focus:text-clay-200"
            >
              <Pencil className="mr-2 h-4 w-4" />
              Rename
              <ContextMenuShortcut>F2</ContextMenuShortcut>
            </ContextMenuItem>
            <ContextMenuItem
              onClick={() => onCopyPath(node)}
              className="text-clay-300 focus:bg-clay-800 focus:text-clay-200"
            >
              <Copy className="mr-2 h-4 w-4" />
              Copy Path
            </ContextMenuItem>
            <ContextMenuItem
              onClick={() => onToggleFavorite(node.id)}
              className="text-clay-300 focus:bg-clay-800 focus:text-clay-200"
            >
              <Star className="mr-2 h-4 w-4" />
              {isFavorite ? "Unpin" : "Pin to Favorites"}
              <ContextMenuShortcut>{"\u2318"}D</ContextMenuShortcut>
            </ContextMenuItem>
            <ContextMenuSeparator className="bg-clay-800" />
            <ContextMenuItem
              onClick={() => onDelete(node.id)}
              className="text-kiln-coral focus:bg-kiln-coral/10 focus:text-kiln-coral"
            >
              <Trash2 className="mr-2 h-4 w-4" />
              Delete
              <ContextMenuShortcut>Del</ContextMenuShortcut>
            </ContextMenuItem>
          </>
        )}
      </ContextMenuContent>
    </ContextMenu>
  );
}
