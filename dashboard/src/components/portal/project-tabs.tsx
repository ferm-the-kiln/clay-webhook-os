"use client";

import { cn } from "@/lib/utils";
import { MessageSquare, Paperclip, CheckSquare } from "lucide-react";

export type ProjectTab = "feed" | "files" | "actions";

const TABS: { id: ProjectTab; label: string; icon: typeof MessageSquare }[] = [
  { id: "feed", label: "Feed", icon: MessageSquare },
  { id: "files", label: "Files", icon: Paperclip },
  { id: "actions", label: "Actions", icon: CheckSquare },
];

interface ProjectTabsProps {
  active: ProjectTab;
  onChange: (tab: ProjectTab) => void;
  counts?: { feed: number; files: number; actions: number };
}

export function ProjectTabs({ active, onChange, counts }: ProjectTabsProps) {
  return (
    <div className="flex gap-2">
      {TABS.map((tab) => {
        const Icon = tab.icon;
        const count = counts?.[tab.id];
        return (
          <button
            key={tab.id}
            onClick={() => onChange(tab.id)}
            className={cn(
              "flex items-center gap-1.5 text-sm px-3.5 py-1.5 rounded-full transition-colors",
              active === tab.id
                ? "bg-kiln-teal/15 text-kiln-teal border border-kiln-teal/30"
                : "bg-clay-700 text-clay-300 border border-clay-600/60 hover:border-clay-500",
            )}
          >
            <Icon className="h-3.5 w-3.5" />
            {tab.label}
            {count !== undefined && count > 0 && (
              <span className="text-[10px] ml-0.5 opacity-70">{count}</span>
            )}
          </button>
        );
      })}
    </div>
  );
}
