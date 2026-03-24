"use client";

import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import {
  CheckCheck,
  ChevronDown,
  Download,
  Copy,
  Send,
  Loader2,
  Trash2,
  LayoutGrid,
  Table2,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type { Destination } from "@/lib/types";

type FilterKey = "all" | "pending" | "approved" | "rejected";

interface ReviewToolbarProps {
  counts: { all: number; pending: number; approved: number; rejected: number };
  filter: string;
  onFilterChange: (filter: FilterKey) => void;
  destinations: Destination[];
  pushing: boolean;
  onApproveAll: () => void;
  onPushApproved: (destinationId: string) => void;
  onDownloadCsv: () => void;
  onCopyToClipboard: () => void;
  onClear: () => void;
  viewMode: "cards" | "table";
  onViewModeChange: (mode: "cards" | "table") => void;
}

const FILTER_TABS: { key: FilterKey; label: string }[] = [
  { key: "all", label: "All" },
  { key: "pending", label: "Pending" },
  { key: "approved", label: "Approved" },
  { key: "rejected", label: "Rejected" },
];

export function ReviewToolbar({
  counts,
  filter,
  onFilterChange,
  destinations,
  pushing,
  onApproveAll,
  onPushApproved,
  onDownloadCsv,
  onCopyToClipboard,
  onClear,
  viewMode,
  onViewModeChange,
}: ReviewToolbarProps) {
  const hasApproved = counts.approved > 0;

  return (
    <div className="space-y-3">
      {/* Top row: view toggle + filter tabs */}
      <div className="flex items-center gap-3">
        {/* View mode toggle */}
        <div className="flex items-center rounded-lg border border-clay-600 overflow-hidden">
          <button
            onClick={() => onViewModeChange("cards")}
            className={cn(
              "flex items-center gap-1 px-2.5 py-1.5 text-xs transition-colors",
              viewMode === "cards"
                ? "bg-clay-700 text-clay-100"
                : "text-clay-400 hover:text-clay-200 hover:bg-clay-700/50"
            )}
            title="Card view"
          >
            <LayoutGrid className="h-3.5 w-3.5" />
          </button>
          <div className="w-px h-5 bg-clay-600" />
          <button
            onClick={() => onViewModeChange("table")}
            className={cn(
              "flex items-center gap-1 px-2.5 py-1.5 text-xs transition-colors",
              viewMode === "table"
                ? "bg-clay-700 text-clay-100"
                : "text-clay-400 hover:text-clay-200 hover:bg-clay-700/50"
            )}
            title="Table view"
          >
            <Table2 className="h-3.5 w-3.5" />
          </button>
        </div>

        {/* Filter tabs */}
        <div className="flex items-center gap-1 flex-wrap">
          {FILTER_TABS.map((tab) => (
            <button
              key={tab.key}
              onClick={() => onFilterChange(tab.key)}
              className={cn(
                "flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs transition-colors",
                filter === tab.key
                  ? "bg-clay-700 text-clay-100"
                  : "text-clay-300 hover:bg-clay-700/50"
              )}
            >
              {tab.label}
              <Badge
                variant="outline"
                className="text-[9px] border-clay-500 text-clay-300 py-0 px-1"
              >
                {counts[tab.key]}
              </Badge>
            </button>
          ))}
        </div>
      </div>

      {/* Bottom row: actions */}
      <div className="flex items-center gap-2 flex-wrap">
        <Button
          variant="outline"
          size="sm"
          onClick={onApproveAll}
          disabled={counts.pending === 0}
          className="border-clay-600 text-clay-200 hover:bg-clay-700 text-xs"
        >
          <CheckCheck className="h-3.5 w-3.5 mr-1.5" />
          Approve All ({counts.pending})
        </Button>

        <div className="flex items-center gap-1.5 ml-auto">
          {/* Unified export menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                size="sm"
                disabled={!hasApproved || pushing}
                className="h-8 bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light text-xs font-semibold"
              >
                {pushing ? (
                  <Loader2 className="h-3.5 w-3.5 mr-1.5 animate-spin" />
                ) : (
                  <Download className="h-3.5 w-3.5 mr-1.5" />
                )}
                Export Approved ({counts.approved})
                <ChevronDown className="h-3 w-3 ml-1.5" />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuItem onClick={onDownloadCsv} className="text-xs">
                <Download className="h-3.5 w-3.5 mr-2" />
                Download CSV
              </DropdownMenuItem>
              <DropdownMenuItem onClick={onCopyToClipboard} className="text-xs">
                <Copy className="h-3.5 w-3.5 mr-2" />
                Copy to Clipboard
              </DropdownMenuItem>

              {destinations.length > 0 && (
                <>
                  <DropdownMenuSeparator />
                  <div className="px-2 py-1 text-[10px] font-medium text-clay-400 uppercase tracking-wider">
                    Push to Destination
                  </div>
                  {destinations.map((d) => (
                    <DropdownMenuItem
                      key={d.id}
                      onClick={() => onPushApproved(d.id)}
                      className="text-xs"
                    >
                      <Send className="h-3.5 w-3.5 mr-2" />
                      {d.name}
                    </DropdownMenuItem>
                  ))}
                </>
              )}

              {destinations.length === 0 && (
                <>
                  <DropdownMenuSeparator />
                  <div className="px-2 py-1.5 text-xs text-clay-400">
                    No destinations configured.
                    <br />
                    Add one in Settings.
                  </div>
                </>
              )}
            </DropdownMenuContent>
          </DropdownMenu>
        </div>

        <Button
          variant="ghost"
          size="sm"
          onClick={onClear}
          className="text-clay-300 hover:text-red-400 text-xs"
          title="Clear queue"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
