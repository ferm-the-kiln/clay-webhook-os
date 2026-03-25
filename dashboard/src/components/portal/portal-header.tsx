"use client";

import { useState, useRef, useEffect } from "react";
import { cn, formatRelativeTime } from "@/lib/utils";
import { Share2, ChevronDown, Eye, CheckSquare, Image, FileText } from "lucide-react";
import { Button } from "@/components/ui/button";

const STATUS_OPTIONS = ["active", "onboarding", "paused", "churned"] as const;

const STATUS_COLORS: Record<string, string> = {
  active: "bg-emerald-500/15 text-emerald-400",
  onboarding: "bg-blue-500/15 text-blue-400",
  paused: "bg-amber-500/15 text-amber-400",
  churned: "bg-red-500/15 text-red-400",
};

const AVATAR_COLORS = [
  "bg-kiln-teal/20 text-kiln-teal",
  "bg-blue-500/20 text-blue-400",
  "bg-purple-500/20 text-purple-400",
  "bg-amber-500/20 text-amber-400",
  "bg-emerald-500/20 text-emerald-400",
];

function getAvatarColor(name: string): string {
  let hash = 0;
  for (let i = 0; i < name.length; i++) {
    hash = name.charCodeAt(i) + ((hash << 5) - hash);
  }
  return AVATAR_COLORS[Math.abs(hash) % AVATAR_COLORS.length];
}

interface PortalHeaderProps {
  name: string;
  status: string;
  syncAvailable: boolean;
  syncing: boolean;
  lastSyncedAt: number | null;
  shareToken: string | null;
  onSync: () => void;
  onShareClick: () => void;
  openActionCount?: number;
  mediaCount?: number;
  sopCount?: number;
  lastViewedAt?: number | null;
  onStatusChange?: (status: string) => void;
}

export function PortalHeader({
  name,
  status,
  syncAvailable,
  syncing,
  lastSyncedAt,
  shareToken,
  onSync,
  onShareClick,
  openActionCount = 0,
  mediaCount = 0,
  sopCount = 0,
  lastViewedAt,
  onStatusChange,
}: PortalHeaderProps) {
  const [statusDropdownOpen, setStatusDropdownOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);

  // Close dropdown on outside click
  useEffect(() => {
    if (!statusDropdownOpen) return;
    const handler = (e: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setStatusDropdownOpen(false);
      }
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [statusDropdownOpen]);

  const initial = name.charAt(0).toUpperCase();

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          {/* Client avatar */}
          <div
            className={cn(
              "h-10 w-10 rounded-xl flex items-center justify-center text-lg font-bold shrink-0",
              getAvatarColor(name)
            )}
          >
            {initial}
          </div>

          <div>
            <h1 className="text-xl font-bold text-clay-100">{name}</h1>
            {/* Clickable status dropdown */}
            <div className="relative inline-block" ref={dropdownRef}>
              <button
                onClick={() => onStatusChange && setStatusDropdownOpen(!statusDropdownOpen)}
                className={cn(
                  "text-[11px] px-2 py-0.5 rounded-full font-medium inline-flex items-center gap-1 mt-1 transition-colors",
                  STATUS_COLORS[status] || STATUS_COLORS.active,
                  onStatusChange && "hover:opacity-80 cursor-pointer"
                )}
              >
                {status}
                {onStatusChange && <ChevronDown className="h-2.5 w-2.5" />}
              </button>

              {statusDropdownOpen && onStatusChange && (
                <div className="absolute top-full left-0 mt-1 w-36 bg-clay-800 border border-clay-600 rounded-lg shadow-xl z-20 py-1">
                  {STATUS_OPTIONS.map((s) => (
                    <button
                      key={s}
                      onClick={() => {
                        onStatusChange(s);
                        setStatusDropdownOpen(false);
                      }}
                      className={cn(
                        "w-full text-left px-3 py-1.5 text-xs transition-colors hover:bg-clay-700",
                        s === status ? "text-clay-100 font-medium" : "text-clay-300"
                      )}
                    >
                      <span className={cn(
                        "inline-block h-1.5 w-1.5 rounded-full mr-2",
                        STATUS_COLORS[s]?.split(" ")[0] || "bg-clay-400"
                      )} />
                      {s}
                    </button>
                  ))}
                </div>
              )}
            </div>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <Button
            variant="outline"
            size="sm"
            onClick={onShareClick}
            className="border-clay-600 text-clay-200 hover:bg-clay-700 gap-2"
          >
            <Share2 className="h-3.5 w-3.5" />
            Share
            {shareToken && (
              <span className="h-1.5 w-1.5 rounded-full bg-emerald-400" />
            )}
          </Button>
        </div>
      </div>

      {/* Context strip */}
      <div className="flex items-center gap-4 text-[11px] text-clay-400 pl-[52px]">
        {openActionCount > 0 && (
          <span className="flex items-center gap-1">
            <CheckSquare className="h-3 w-3" />
            {openActionCount} open action{openActionCount !== 1 ? "s" : ""}
          </span>
        )}
        <span className="flex items-center gap-1">
          <Image className="h-3 w-3" />
          {mediaCount} file{mediaCount !== 1 ? "s" : ""}
        </span>
        <span className="flex items-center gap-1">
          <FileText className="h-3 w-3" />
          {sopCount} SOP{sopCount !== 1 ? "s" : ""}
        </span>
        <span className="flex items-center gap-1">
          <Eye className="h-3 w-3" />
          {lastViewedAt
            ? `Client viewed ${formatRelativeTime(lastViewedAt)}`
            : "Client hasn\u2019t viewed yet"}
        </span>
      </div>
    </div>
  );
}
