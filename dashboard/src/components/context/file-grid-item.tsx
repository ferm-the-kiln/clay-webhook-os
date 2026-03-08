"use client";

import { useState, useRef, useEffect } from "react";
import { Folder, FolderOpen, FileText, BookOpen, Users, TestTubes } from "lucide-react";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import type { FileNode } from "@/lib/types";

interface FileGridItemProps {
  node: FileNode;
  isSelected: boolean;
  isMultiSelected: boolean;
  isRenaming: boolean;
  usageMap: Record<string, string[]>;
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

export function FileGridItem({
  node,
  isSelected,
  isMultiSelected,
  isRenaming,
  usageMap,
  onSelect,
  onDoubleClick,
  onNavigate,
  onRename,
  onToggleSelect,
  onContextMenu,
}: FileGridItemProps) {
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

  const usagePath = node.meta?.path as string | undefined;
  const skills = usagePath ? usageMap[usagePath] ?? [] : [];

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
      onRename(node.id, node.name); // Cancel
    }
  };

  return (
    <div
      onClick={handleClick}
      onDoubleClick={handleDoubleClick}
      onContextMenu={(e) => onContextMenu(e, node)}
      className={cn(
        "group flex flex-col items-center gap-2 rounded-lg border p-3 cursor-pointer transition-all",
        isSelected
          ? "border-kiln-teal/50 bg-kiln-teal/5"
          : "border-clay-800 hover:border-clay-700 bg-clay-900/50 hover:bg-clay-900",
        isMultiSelected && "ring-2 ring-blue-500/50"
      )}
    >
      <Icon
        className={cn(
          "h-8 w-8",
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
          className="w-full bg-clay-800 border border-clay-600 rounded px-1 py-0.5 text-center text-xs text-clay-200 outline-none focus:border-kiln-teal"
        />
      ) : (
        <span className="w-full text-center text-xs text-clay-300 truncate">
          {node.name}
        </span>
      )}

      {node.category && (
        <Badge
          variant="outline"
          className="text-[10px] px-1.5 py-0 border-clay-700 text-clay-500"
        >
          {node.category}
        </Badge>
      )}

      {skills.length > 0 && (
        <div className="flex flex-wrap gap-1 justify-center">
          {skills.slice(0, 2).map((s) => (
            <Badge
              key={s}
              variant="outline"
              className="text-[10px] px-1 py-0 border-kiln-teal/30 text-kiln-teal/70"
            >
              {s}
            </Badge>
          ))}
          {skills.length > 2 && (
            <Badge
              variant="outline"
              className="text-[10px] px-1 py-0 border-clay-700 text-clay-500"
            >
              +{skills.length - 2}
            </Badge>
          )}
        </div>
      )}
    </div>
  );
}
