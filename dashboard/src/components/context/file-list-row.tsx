"use client";

import { useState, useRef, useEffect } from "react";
import { Folder, FileText, BookOpen, Users, TestTubes } from "lucide-react";
import { cn } from "@/lib/utils";
import type { FileNode } from "@/lib/types";

interface FileListRowProps {
  node: FileNode;
  isSelected: boolean;
  isMultiSelected: boolean;
  isRenaming: boolean;
  onSelect: (id: string) => void;
  onDoubleClick: (id: string) => void;
  onNavigate: (id: string) => void;
  onRename: (id: string, newName: string) => void;
  onToggleSelect: (id: string, multi: boolean) => void;
  onContextMenu: (e: React.MouseEvent, node: FileNode) => void;
}

const DRIVE_ICONS: Record<string, typeof BookOpen> = {
  "knowledge-base": BookOpen,
  clients: Users,
  skills: TestTubes,
};

export function FileListRow({
  node,
  isSelected,
  isMultiSelected,
  isRenaming,
  onSelect,
  onDoubleClick,
  onNavigate,
  onRename,
  onToggleSelect,
  onContextMenu,
}: FileListRowProps) {
  const [renameValue, setRenameValue] = useState(node.name);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    if (isRenaming && inputRef.current) {
      inputRef.current.focus();
      inputRef.current.select();
    }
  }, [isRenaming]);

  const isFolder = node.type === "folder" || node.type === "drive";
  const DriveIcon = node.type === "drive" ? DRIVE_ICONS[node.driveId] : undefined;
  const Icon = DriveIcon || (isFolder ? Folder : FileText);

  const typeLabel = node.type === "drive" ? "Drive" : node.type === "folder" ? "Folder" : "File";

  const handleClick = (e: React.MouseEvent) => {
    if (e.shiftKey || e.metaKey || e.ctrlKey) {
      onToggleSelect(node.id, true);
      return;
    }
    if (isFolder) {
      onNavigate(node.id);
    } else {
      onSelect(node.id);
    }
  };

  const handleDoubleClick = () => {
    if (isFolder) {
      onNavigate(node.id);
    } else {
      onDoubleClick(node.id);
    }
  };

  const handleRenameKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === "Enter") {
      onRename(node.id, renameValue);
    } else if (e.key === "Escape") {
      setRenameValue(node.name);
      onRename(node.id, node.name);
    }
  };

  return (
    <tr
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
      onContextMenu={(e) => onContextMenu(e, node)}
      className={cn(
        "cursor-pointer border-b border-clay-800/50 transition-colors",
        isSelected ? "bg-kiln-teal/5" : "hover:bg-clay-900/50",
        isMultiSelected && "ring-1 ring-inset ring-blue-500/50"
      )}
    >
      <td className="px-3 py-2">
        <div className="flex items-center gap-2">
          <Icon
            className={cn(
              "h-4 w-4 shrink-0",
              isFolder ? "text-amber-500" : "text-clay-400",
              node.type === "drive" && "text-kiln-teal"
            )}
          />
          {isRenaming ? (
            <input
              ref={inputRef}
              value={renameValue}
              onChange={(e) => setRenameValue(e.target.value)}
              onKeyDown={handleRenameKeyDown}
              onBlur={() => onRename(node.id, renameValue)}
              className="bg-clay-800 border border-clay-600 rounded px-1.5 py-0.5 text-xs text-clay-200 outline-none focus:border-kiln-teal"
            />
          ) : (
            <span className="text-xs text-clay-300 truncate">{node.name}</span>
          )}
        </div>
      </td>
      <td className="px-3 py-2 text-xs text-clay-500 hidden sm:table-cell">
        {typeLabel}
      </td>
      <td className="px-3 py-2 text-xs text-clay-500 hidden md:table-cell">
        {node.category || "—"}
      </td>
      <td className="px-3 py-2" />
    </tr>
  );
}
