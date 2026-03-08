"use client";

import { X, Plus } from "lucide-react";
import { cn } from "@/lib/utils";
import type { FileTab } from "@/hooks/use-file-explorer";

interface FileTabsProps {
  tabs: FileTab[];
  activeTabId: string;
  onSelectTab: (tabId: string) => void;
  onCloseTab: (tabId: string) => void;
  onNewTab: () => void;
}

export function FileTabs({
  tabs,
  activeTabId,
  onSelectTab,
  onCloseTab,
  onNewTab,
}: FileTabsProps) {
  return (
    <div className="flex items-center gap-0.5 overflow-x-auto border-b border-clay-800 px-1">
      {tabs.map((tab) => {
        const isActive = tab.id === activeTabId;
        return (
          <div
            key={tab.id}
            className={cn(
              "group flex items-center gap-1 rounded-t-md px-3 py-1.5 text-xs cursor-pointer transition-colors",
              isActive
                ? "bg-clay-900 text-clay-200 border-b-2 border-kiln-teal"
                : "text-clay-500 hover:text-clay-300 hover:bg-clay-900/50"
            )}
            onClick={() => onSelectTab(tab.id)}
            onMouseDown={(e) => {
              // Middle-click to close
              if (e.button === 1) {
                e.preventDefault();
                onCloseTab(tab.id);
              }
            }}
          >
            <span className="truncate max-w-[120px]">{tab.label}</span>
            <button
              onClick={(e) => {
                e.stopPropagation();
                onCloseTab(tab.id);
              }}
              className={cn(
                "rounded p-0.5 transition-colors",
                isActive
                  ? "hover:bg-clay-800 text-clay-500"
                  : "opacity-0 group-hover:opacity-100 hover:bg-clay-800 text-clay-600"
              )}
            >
              <X className="h-3 w-3" />
            </button>
          </div>
        );
      })}
      <button
        onClick={onNewTab}
        className="flex items-center justify-center rounded-md p-1.5 text-clay-600 hover:text-clay-400 hover:bg-clay-800/50 transition-colors"
      >
        <Plus className="h-3 w-3" />
      </button>
    </div>
  );
}
