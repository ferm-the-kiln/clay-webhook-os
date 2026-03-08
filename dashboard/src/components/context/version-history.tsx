"use client";

import { useState, useEffect } from "react";
import { History, RotateCcw } from "lucide-react";
import { Button } from "@/components/ui/button";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

interface VersionEntry {
  content: string;
  timestamp: number;
  wordCount: number;
}

const MAX_VERSIONS = 5;
const STORAGE_PREFIX = "file_history:";

export function getFileHistory(fileId: string): VersionEntry[] {
  if (typeof window === "undefined") return [];
  try {
    return JSON.parse(
      localStorage.getItem(`${STORAGE_PREFIX}${fileId}`) || "[]"
    );
  } catch {
    return [];
  }
}

export function saveFileVersion(fileId: string, content: string) {
  const history = getFileHistory(fileId);
  const entry: VersionEntry = {
    content,
    timestamp: Date.now(),
    wordCount: content.split(/\s+/).filter(Boolean).length,
  };
  // Don't save duplicate if content matches latest
  if (history.length > 0 && history[0].content === content) return;
  history.unshift(entry);
  localStorage.setItem(
    `${STORAGE_PREFIX}${fileId}`,
    JSON.stringify(history.slice(0, MAX_VERSIONS))
  );
}

interface VersionHistoryProps {
  fileId: string;
  onRestore: (content: string) => void;
}

export function VersionHistory({ fileId, onRestore }: VersionHistoryProps) {
  const [versions, setVersions] = useState<VersionEntry[]>([]);

  useEffect(() => {
    setVersions(getFileHistory(fileId));
  }, [fileId]);

  if (versions.length === 0) return null;

  const formatTime = (ts: number) => {
    const d = new Date(ts);
    const now = Date.now();
    const diff = now - ts;
    if (diff < 60_000) return "Just now";
    if (diff < 3600_000) return `${Math.floor(diff / 60_000)}m ago`;
    if (diff < 86400_000) return `${Math.floor(diff / 3600_000)}h ago`;
    return d.toLocaleDateString();
  };

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button
          variant="ghost"
          size="sm"
          className="h-7 text-xs text-clay-400 hover:text-clay-200"
        >
          <History className="h-3 w-3 mr-1" />
          History ({versions.length})
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent
        align="end"
        className="w-56 bg-clay-900 border-clay-700"
      >
        {versions.map((v, i) => (
          <DropdownMenuItem
            key={v.timestamp}
            onClick={() => onRestore(v.content)}
            className="text-clay-300 focus:bg-clay-800 focus:text-clay-200"
          >
            <div className="flex w-full items-center justify-between">
              <div className="flex items-center gap-2">
                <RotateCcw className="h-3 w-3 text-clay-500" />
                <span className="text-xs">
                  {i === 0 ? "Latest" : formatTime(v.timestamp)}
                </span>
              </div>
              <span className="text-[10px] text-clay-600">
                {v.wordCount}w
              </span>
            </div>
          </DropdownMenuItem>
        ))}
      </DropdownMenuContent>
    </DropdownMenu>
  );
}
