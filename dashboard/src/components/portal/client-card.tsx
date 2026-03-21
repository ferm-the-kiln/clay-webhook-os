"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import { FileText, MessageSquare, Image, Cloud, Clock, CheckSquare } from "lucide-react";
import type { PortalOverview } from "@/lib/types";
import { HealthBadge } from "./health-badge";

const STATUS_COLORS: Record<string, string> = {
  active: "bg-emerald-500/15 text-emerald-400 border-emerald-500/30",
  onboarding: "bg-blue-500/15 text-blue-400 border-blue-500/30",
  paused: "bg-amber-500/15 text-amber-400 border-amber-500/30",
  churned: "bg-red-500/15 text-red-400 border-red-500/30",
};

function timeAgo(ts: number | null): string {
  if (!ts) return "No activity";
  const diff = Date.now() / 1000 - ts;
  if (diff < 60) return "Just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  return new Date(ts * 1000).toLocaleDateString();
}

export function ClientCard({ portal }: { portal: PortalOverview }) {
  return (
    <Link
      href={`/clients/${portal.slug}`}
      className="group block rounded-xl border border-clay-600 bg-clay-800 p-5 transition-all hover:border-clay-500 hover:bg-clay-750"
    >
      <div className="flex items-start justify-between mb-3">
        <h3 className="text-base font-semibold text-clay-100 group-hover:text-kiln-teal transition-colors">
          {portal.name}
        </h3>
        <div className="flex items-center gap-2">
          <HealthBadge portal={portal} />
          {portal.open_client_actions > 0 && (
            <span className="text-[10px] px-1.5 py-0.5 rounded-full font-medium bg-orange-500/15 text-orange-400 border border-orange-500/30">
              {portal.open_client_actions} waiting
            </span>
          )}
          <span
            className={cn(
              "text-[11px] px-2 py-0.5 rounded-full border font-medium",
              STATUS_COLORS[portal.status] || STATUS_COLORS.active
            )}
          >
            {portal.status}
          </span>
        </div>
      </div>

      <div className="flex items-center gap-4 text-xs text-clay-300">
        <span className="flex items-center gap-1">
          <FileText className="h-3.5 w-3.5" />
          {portal.sop_count} SOPs
        </span>
        <span className="flex items-center gap-1">
          <MessageSquare className="h-3.5 w-3.5" />
          {portal.update_count} updates
        </span>
        <span className="flex items-center gap-1">
          <Image className="h-3.5 w-3.5" />
          {portal.media_count}
        </span>
        <span className="flex items-center gap-1">
          <CheckSquare className="h-3.5 w-3.5" />
          {portal.action_count}
        </span>
      </div>

      <div className="mt-3 pt-3 border-t border-clay-700 flex items-center justify-between text-[11px] text-clay-400">
        <span className="flex items-center gap-1">
          <Clock className="h-3 w-3" />
          {timeAgo(portal.last_activity)}
        </span>
        <div className="flex items-center gap-2">
          {portal.last_viewed_at && (
            <span className="text-clay-500">Viewed {timeAgo(portal.last_viewed_at)}</span>
          )}
          {portal.has_gws_sync && (
            <span className="flex items-center gap-1 text-blue-400">
              <Cloud className="h-3 w-3" />
              Synced
            </span>
          )}
        </div>
      </div>
    </Link>
  );
}
