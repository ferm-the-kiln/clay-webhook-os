"use client";

import type { FileNode } from "@/lib/types";

interface StatusBarProps {
  itemCount: number;
  currentPath: string;
  selectedCount: number;
  selectedFile: FileNode | null;
}

export function StatusBar({
  itemCount,
  currentPath,
  selectedCount,
  selectedFile,
}: StatusBarProps) {
  const wordCount =
    selectedFile?.content
      ? selectedFile.content.split(/\s+/).filter(Boolean).length
      : 0;

  return (
    <div className="flex items-center justify-between border-t border-clay-800 bg-clay-950 px-4 py-1.5 text-[10px] text-clay-500">
      <div className="flex items-center gap-3">
        <span>
          {itemCount} {itemCount === 1 ? "item" : "items"}
        </span>
        {selectedCount > 0 && (
          <span className="text-kiln-teal">{selectedCount} selected</span>
        )}
        {selectedFile && wordCount > 0 && (
          <span>{wordCount} words</span>
        )}
      </div>
      <span className="text-clay-600 truncate max-w-[300px]">{currentPath}</span>
    </div>
  );
}
