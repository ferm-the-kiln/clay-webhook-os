"use client";

import { useState } from "react";
import {
  Clock,
  Bell,
  Milestone,
  Package,
  StickyNote,
  Rocket,
  Check,
} from "lucide-react";
import { cn, formatRelativeTime } from "@/lib/utils";
import type { PortalDetail, PortalAction } from "@/lib/types";
import { InlineNotes } from "./inline-notes";
import { NotificationSettings } from "./notification-settings";

const TIMELINE_COLORS: Record<string, { dot: string; icon: React.ElementType }> = {
  update: { dot: "bg-blue-400", icon: Bell },
  milestone: { dot: "bg-emerald-400", icon: Milestone },
  deliverable: { dot: "bg-purple-400", icon: Package },
  note: { dot: "bg-amber-400", icon: StickyNote },
};

// ── Onboarding checklist (reused from original page) ──

function OnboardingChecklist({ portal }: { portal: PortalDetail }) {
  const checks = [
    { label: "Create a SOP", done: portal.sops.length > 0 },
    { label: "Post an update", done: portal.recent_updates.length > 0 },
    { label: "Upload a file", done: portal.media.length > 0 },
    { label: "Add an action", done: portal.actions.length > 0 },
    { label: "Connect Slack", done: !!portal.meta.slack_webhook_url },
  ];

  const completedCount = checks.filter((c) => c.done).length;
  if (completedCount === checks.length) return null;

  const pct = (completedCount / checks.length) * 100;

  return (
    <div className="rounded-xl border border-clay-700 bg-clay-800 p-4">
      <div className="flex items-center gap-2 mb-3">
        <Rocket className="h-4 w-4 text-kiln-teal" />
        <h3 className="text-sm font-semibold text-clay-100">Getting Started</h3>
        <span className="text-[10px] text-clay-500 ml-auto">{completedCount}/{checks.length}</span>
      </div>
      <div className="h-1.5 rounded-full bg-clay-700 mb-3">
        <div className="h-full rounded-full bg-kiln-teal transition-all" style={{ width: `${pct}%` }} />
      </div>
      <div className="space-y-1.5">
        {checks.map((check) => (
          <div
            key={check.label}
            className={cn(
              "flex items-center gap-2 rounded px-2 py-1.5 text-xs",
              check.done ? "text-clay-500" : "text-clay-300"
            )}
          >
            <span className={cn(
              "h-4 w-4 rounded-full border flex items-center justify-center shrink-0",
              check.done ? "border-kiln-teal bg-kiln-teal/20" : "border-clay-600"
            )}>
              {check.done && <Check className="h-2.5 w-2.5 text-kiln-teal" />}
            </span>
            <span className={check.done ? "line-through" : ""}>{check.label}</span>
          </div>
        ))}
      </div>
    </div>
  );
}

// ── Main sidebar ──

interface TimelineSidebarProps {
  portal: PortalDetail;
  onSelectUpdate: (updateId: string) => void;
  activeUpdateId: string | null;
  slug: string;
  onToggleAction: (actionId: string) => void;
  onPortalUpdated: () => void;
}

export function TimelineSidebar({
  portal,
  onSelectUpdate,
  activeUpdateId,
  slug,
  onPortalUpdated,
}: TimelineSidebarProps) {
  const updates = [...portal.recent_updates].sort((a, b) => b.created_at - a.created_at);

  return (
    <div className="sticky top-4 space-y-4 max-h-[calc(100vh-6rem)] overflow-y-auto">
      {/* Timeline */}
      <div className="rounded-xl border border-clay-700 bg-clay-800 p-4">
        <h3 className="text-xs font-semibold text-clay-200 mb-3 flex items-center gap-2">
          <Clock className="h-3.5 w-3.5 text-clay-400" />
          Timeline
          <span className="text-[10px] bg-clay-700 text-clay-400 px-1.5 py-0.5 rounded-full ml-auto">
            {updates.length}
          </span>
        </h3>

        {updates.length === 0 ? (
          <p className="text-xs text-clay-500 text-center py-4">No activity yet.</p>
        ) : (
          <div className="relative pl-5">
            {/* Vertical line */}
            <div className="absolute left-[7px] top-1 bottom-1 w-px bg-clay-700" />

            <div className="space-y-2.5">
              {updates.map((update) => {
                const config = TIMELINE_COLORS[update.type] || TIMELINE_COLORS.update;
                const isActive = update.id === activeUpdateId;

                return (
                  <button
                    key={update.id}
                    onClick={() => onSelectUpdate(update.id)}
                    className={cn(
                      "relative flex items-start gap-2 w-full text-left rounded-md px-2 py-1.5 -ml-2 transition-colors",
                      isActive ? "bg-clay-750" : "hover:bg-clay-750/50"
                    )}
                  >
                    {/* Dot */}
                    <span
                      className={cn(
                        "absolute -left-[13px] top-2.5 h-2.5 w-2.5 rounded-full border-2 border-clay-800 shrink-0 z-10",
                        config.dot
                      )}
                    />
                    <div className="min-w-0 flex-1">
                      <p className="text-xs text-clay-200 truncate">{update.title}</p>
                      <span className="text-[10px] text-clay-500">
                        {formatRelativeTime(update.created_at)}
                      </span>
                    </div>
                  </button>
                );
              })}
            </div>
          </div>
        )}
      </div>

      {/* Internal Notes */}
      <InlineNotes notes={portal.meta.notes} slug={slug} onSaved={onPortalUpdated} />

      {/* Notification Settings */}
      <NotificationSettings
        slug={slug}
        slackWebhookUrl={portal.meta.slack_webhook_url ?? null}
        notificationEmails={portal.meta.notification_emails ?? []}
        onSaved={onPortalUpdated}
        compact
      />

      {/* Onboarding Checklist */}
      <OnboardingChecklist portal={portal} />
    </div>
  );
}
