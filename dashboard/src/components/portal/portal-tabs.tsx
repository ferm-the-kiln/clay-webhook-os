"use client";

import { cn } from "@/lib/utils";
import { MessageSquare, FileText } from "lucide-react";

export type PortalTab = "communication" | "documents";

const TABS: { id: PortalTab; label: string; icon: typeof MessageSquare }[] = [
  { id: "communication", label: "Communication", icon: MessageSquare },
  { id: "documents", label: "Documents & Files", icon: FileText },
];

interface PortalTabsProps {
  active: PortalTab;
  onChange: (tab: PortalTab) => void;
  counts?: { communication: number; documents: number };
}

export function PortalTabs({ active, onChange, counts }: PortalTabsProps) {
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
              "flex items-center gap-2 text-sm px-4 py-2 rounded-lg transition-colors font-medium",
              active === tab.id
                ? "bg-kiln-teal/15 text-kiln-teal border border-kiln-teal/30"
                : "bg-clay-800 text-clay-300 border border-clay-700 hover:border-clay-500 hover:text-clay-200"
            )}
          >
            <Icon className="h-4 w-4" />
            {tab.label}
            {count !== undefined && count > 0 && (
              <span className={cn(
                "text-[10px] px-1.5 py-0.5 rounded-full",
                active === tab.id ? "bg-kiln-teal/20 text-kiln-teal" : "bg-clay-700 text-clay-400"
              )}>
                {count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
