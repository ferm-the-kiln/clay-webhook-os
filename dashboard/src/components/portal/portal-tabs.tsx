"use client";

import { cn } from "@/lib/utils";
import { LayoutDashboard, FileText, MessageSquare, Image, CheckSquare } from "lucide-react";

export type PortalTab = "overview" | "sops" | "updates" | "media" | "actions";

const TABS: { id: PortalTab; label: string; shortLabel: string; icon: React.ElementType }[] = [
  { id: "overview", label: "Overview", shortLabel: "Home", icon: LayoutDashboard },
  { id: "sops", label: "SOPs", shortLabel: "SOPs", icon: FileText },
  { id: "updates", label: "Updates", shortLabel: "Feed", icon: MessageSquare },
  { id: "media", label: "Media", shortLabel: "Files", icon: Image },
  { id: "actions", label: "Actions", shortLabel: "Tasks", icon: CheckSquare },
];

interface PortalTabsProps {
  active: PortalTab;
  onChange: (tab: PortalTab) => void;
  counts?: { sops: number; updates: number; media: number; actions: number };
}

export function PortalTabs({ active, onChange, counts }: PortalTabsProps) {
  const countMap: Record<string, number | undefined> = {
    sops: counts?.sops,
    updates: counts?.updates,
    media: counts?.media,
    actions: counts?.actions,
  };

  return (
    <div className="flex gap-1 border-b border-clay-700 pb-px overflow-x-auto scrollbar-none -mx-4 px-4 sm:mx-0 sm:px-0">
      {TABS.map((tab) => (
        <button
          key={tab.id}
          onClick={() => onChange(tab.id)}
          className={cn(
            "flex items-center gap-1.5 sm:gap-2 px-3 sm:px-4 py-2.5 text-xs sm:text-sm font-medium rounded-t-lg transition-colors border-b-2 whitespace-nowrap shrink-0",
            active === tab.id
              ? "text-kiln-teal border-kiln-teal bg-kiln-teal/5"
              : "text-clay-300 border-transparent hover:text-clay-100 hover:bg-clay-750"
          )}
        >
          <tab.icon className="h-4 w-4" />
          <span className="hidden sm:inline">{tab.label}</span>
          <span className="sm:hidden">{tab.shortLabel}</span>
          {countMap[tab.id] !== undefined && (
            <span className="text-[10px] bg-clay-700 text-clay-300 px-1.5 py-0.5 rounded-full">
              {countMap[tab.id]}
            </span>
          )}
        </button>
      ))}
    </div>
  );
}
