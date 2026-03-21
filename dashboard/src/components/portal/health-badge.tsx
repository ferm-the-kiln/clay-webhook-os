"use client";

import { cn } from "@/lib/utils";
import type { PortalOverview } from "@/lib/types";

type HealthLevel = "healthy" | "warning" | "critical" | "inactive";

function getHealthLevel(portal: PortalOverview): HealthLevel {
  if (portal.overdue_action_count > 0) return "critical";
  if (portal.days_since_last_update !== null && portal.days_since_last_update >= 7) return "warning";
  if (portal.last_viewed_at === null) return "inactive";
  return "healthy";
}

const HEALTH_CONFIG: Record<HealthLevel, { dot: string; label: string; ring: string }> = {
  critical: { dot: "bg-red-400", label: "Needs attention", ring: "ring-red-400/20" },
  warning: { dot: "bg-amber-400", label: "Stale", ring: "ring-amber-400/20" },
  inactive: { dot: "bg-clay-500", label: "Never viewed", ring: "ring-clay-500/20" },
  healthy: { dot: "bg-emerald-400", label: "Healthy", ring: "ring-emerald-400/20" },
};

export function HealthBadge({ portal }: { portal: PortalOverview }) {
  const level = getHealthLevel(portal);
  const config = HEALTH_CONFIG[level];

  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 text-[10px] font-medium px-1.5 py-0.5 rounded-full ring-1",
        config.ring,
        level === "critical" ? "text-red-400" :
        level === "warning" ? "text-amber-400" :
        level === "inactive" ? "text-clay-500" :
        "text-emerald-400"
      )}
      title={config.label}
    >
      <span className={cn("h-1.5 w-1.5 rounded-full", config.dot)} />
      {level === "critical" && portal.overdue_action_count > 0 && `${portal.overdue_action_count} overdue`}
      {level === "warning" && `${portal.days_since_last_update}d quiet`}
      {level === "inactive" && "No views"}
      {level === "healthy" && ""}
    </span>
  );
}

export function getHealthLevel_fn(portal: PortalOverview): HealthLevel {
  return getHealthLevel(portal);
}
