"use client";

import { useState } from "react";
import {
  FileText,
  MessageSquare,
  Image,
  CheckSquare,
  AlertCircle,
  User,
  Clock,
  Plus,
  Upload,
  Pencil,
  Bell,
  Milestone,
  Package,
  StickyNote,
  ChevronRight,
  Check,
  Rocket,
  Eye,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn, formatRelativeTime } from "@/lib/utils";
import { updatePortal } from "@/lib/api";
import { toast } from "sonner";
import type { PortalDetail, PortalAction, ViewStats } from "@/lib/types";
import type { PortalTab } from "./portal-tabs";
import { NotificationSettings } from "./notification-settings";

// ── Timeline color config (mirrors update-feed.tsx TYPE_CONFIG) ──

const TIMELINE_COLORS: Record<string, { dot: string; icon: React.ElementType }> = {
  update: { dot: "bg-blue-400", icon: Bell },
  milestone: { dot: "bg-emerald-400", icon: Milestone },
  deliverable: { dot: "bg-purple-400", icon: Package },
  note: { dot: "bg-amber-400", icon: StickyNote },
};

// ── Sub-components ──

interface OverviewTabProps {
  portal: PortalDetail;
  slug: string;
  onPortalUpdated?: () => void;
  onTabChange?: (tab: PortalTab) => void;
  onToggleAction?: (actionId: string) => void;
}

function SummaryBar({
  portal,
  onTabChange,
}: {
  portal: PortalDetail;
  onTabChange?: (tab: PortalTab) => void;
}) {
  const openActions = portal.actions.filter((a) => a.status !== "done").length;
  const pinnedUpdates = portal.recent_updates.filter((u) => u.pinned).length;
  const lastUpdate = portal.recent_updates[0];

  const items: {
    icon: React.ElementType;
    label: string;
    count: number;
    sub: string;
    tab: PortalTab;
  }[] = [
    {
      icon: FileText,
      label: "SOPs",
      count: portal.sops.length,
      sub: portal.sops.length === 0 ? "None yet" : `${portal.sops.length} document${portal.sops.length !== 1 ? "s" : ""}`,
      tab: "sops",
    },
    {
      icon: MessageSquare,
      label: "Updates",
      count: portal.recent_updates.length,
      sub: pinnedUpdates > 0 ? `${pinnedUpdates} pinned` : lastUpdate ? formatRelativeTime(lastUpdate.created_at) : "None yet",
      tab: "updates",
    },
    {
      icon: Image,
      label: "Media",
      count: portal.media.length,
      sub: portal.media.length === 0 ? "None yet" : `${portal.media.length} file${portal.media.length !== 1 ? "s" : ""}`,
      tab: "media",
    },
    {
      icon: CheckSquare,
      label: "Actions",
      count: openActions,
      sub: openActions === 0 ? "All clear" : `${openActions} open`,
      tab: "actions",
    },
  ];

  return (
    <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
      {items.map((item) => (
        <button
          key={item.label}
          onClick={() => onTabChange?.(item.tab)}
          className="rounded-lg border border-clay-600 bg-clay-800 p-3 text-left hover:border-clay-500 hover:bg-clay-750 transition-colors group"
        >
          <div className="flex items-center gap-2 text-clay-400 mb-1 group-hover:text-clay-300">
            <item.icon className="h-3.5 w-3.5" />
            <span className="text-[11px] font-medium">{item.label}</span>
          </div>
          <p className="text-xl font-bold text-clay-100">{item.count}</p>
          <p className="text-[10px] text-clay-500 mt-0.5">{item.sub}</p>
        </button>
      ))}
    </div>
  );
}

function PortalInsights({
  portal,
  onTabChange,
}: {
  portal: PortalDetail;
  onTabChange?: (tab: PortalTab) => void;
}) {
  const viewStats = portal.view_stats;
  const sopAcks = portal.sop_acks || {};
  const ackedCount = portal.sops.filter((s) => s.id in sopAcks).length;
  const totalSops = portal.sops.length;

  return (
    <div className="flex flex-wrap gap-3">
      {/* View stats */}
      <div className="flex items-center gap-2 text-xs text-clay-400 bg-clay-800 border border-clay-700 rounded-lg px-3 py-2">
        <Eye className="h-3.5 w-3.5" />
        {viewStats?.last_viewed_at ? (
          <span>
            Last viewed {formatRelativeTime(viewStats.last_viewed_at)} · {viewStats.view_count_7d} views this week
          </span>
        ) : (
          <span>Never viewed</span>
        )}
      </div>

      {/* SOP acknowledgment summary */}
      {totalSops > 0 && (
        <button
          onClick={() => onTabChange?.("sops")}
          className="flex items-center gap-2 text-xs bg-clay-800 border border-clay-700 rounded-lg px-3 py-2 hover:border-clay-500 transition-colors"
        >
          <FileText className="h-3.5 w-3.5 text-clay-400" />
          <span className={ackedCount === totalSops ? "text-emerald-400" : "text-clay-400"}>
            {ackedCount} of {totalSops} SOPs acknowledged
          </span>
          {ackedCount < totalSops && (
            <span className="h-1.5 w-1.5 rounded-full bg-amber-400" />
          )}
        </button>
      )}
    </div>
  );
}

function QuickActions({ onTabChange }: { onTabChange?: (tab: PortalTab) => void }) {
  const actions = [
    { icon: MessageSquare, label: "Post Update", tab: "updates" as PortalTab },
    { icon: FileText, label: "Create SOP", tab: "sops" as PortalTab },
    { icon: Upload, label: "Upload File", tab: "media" as PortalTab },
    { icon: Plus, label: "Add Action", tab: "actions" as PortalTab },
  ];

  return (
    <div className="flex flex-wrap gap-2">
      {actions.map((action) => (
        <Button
          key={action.label}
          variant="outline"
          size="sm"
          onClick={() => onTabChange?.(action.tab)}
          className="border-clay-600 text-clay-300 hover:text-clay-100 hover:bg-clay-700 gap-1.5"
        >
          <action.icon className="h-3.5 w-3.5" />
          {action.label}
        </Button>
      ))}
    </div>
  );
}

function OnboardingChecklist({
  portal,
  onTabChange,
}: {
  portal: PortalDetail;
  onTabChange?: (tab: PortalTab) => void;
}) {
  const checks = [
    { label: "Create a SOP", done: portal.sops.length > 0, tab: "sops" as PortalTab },
    { label: "Post an update", done: portal.recent_updates.length > 0, tab: "updates" as PortalTab },
    { label: "Upload a file", done: portal.media.length > 0, tab: "media" as PortalTab },
    { label: "Add an action", done: portal.actions.length > 0, tab: "actions" as PortalTab },
    { label: "Connect Slack", done: !!portal.meta.slack_webhook_url, tab: "overview" as PortalTab },
  ];

  const completedCount = checks.filter((c) => c.done).length;
  const allDone = completedCount === checks.length;

  if (allDone) return null;

  const pct = (completedCount / checks.length) * 100;

  return (
    <div className="rounded-lg border border-clay-600 bg-clay-800 p-4">
      <div className="flex items-center gap-2 mb-3">
        <Rocket className="h-4 w-4 text-kiln-teal" />
        <h3 className="text-sm font-semibold text-clay-100">Getting Started</h3>
        <span className="text-[10px] text-clay-500 ml-auto">{completedCount}/{checks.length}</span>
      </div>
      <div className="h-1.5 rounded-full bg-clay-700 mb-3">
        <div
          className="h-full rounded-full bg-kiln-teal transition-all"
          style={{ width: `${pct}%` }}
        />
      </div>
      <div className="space-y-1.5">
        {checks.map((check) => (
          <button
            key={check.label}
            onClick={() => !check.done && onTabChange?.(check.tab)}
            disabled={check.done}
            className={cn(
              "flex items-center gap-2 w-full text-left rounded px-2 py-1.5 text-xs transition-colors",
              check.done
                ? "text-clay-500 cursor-default"
                : "text-clay-300 hover:bg-clay-700 hover:text-clay-100"
            )}
          >
            <span
              className={cn(
                "h-4 w-4 rounded-full border flex items-center justify-center shrink-0",
                check.done
                  ? "border-kiln-teal bg-kiln-teal/20"
                  : "border-clay-600"
              )}
            >
              {check.done && <Check className="h-2.5 w-2.5 text-kiln-teal" />}
            </span>
            <span className={check.done ? "line-through" : ""}>{check.label}</span>
            {!check.done && <ChevronRight className="h-3 w-3 text-clay-600 ml-auto" />}
          </button>
        ))}
      </div>
    </div>
  );
}

function ActivityTimeline({
  portal,
  onTabChange,
}: {
  portal: PortalDetail;
  onTabChange?: (tab: PortalTab) => void;
}) {
  const updates = portal.recent_updates.slice(0, 8);

  if (updates.length === 0) {
    return (
      <div className="rounded-lg border border-clay-700 bg-clay-800 p-6 text-center">
        <Clock className="h-5 w-5 text-clay-500 mx-auto mb-2" />
        <p className="text-sm text-clay-400">No activity yet. Post your first update to get started.</p>
      </div>
    );
  }

  return (
    <div>
      <h3 className="text-sm font-semibold text-clay-200 mb-3 flex items-center gap-2">
        <Clock className="h-4 w-4" />
        Recent Activity
      </h3>
      <div className="relative pl-6">
        {/* Vertical timeline line */}
        <div className="absolute left-[7px] top-2 bottom-2 w-px bg-clay-700" />

        <div className="space-y-3">
          {updates.map((update) => {
            const config = TIMELINE_COLORS[update.type] || TIMELINE_COLORS.update;
            return (
              <div key={update.id} className="relative flex items-start gap-3">
                {/* Dot */}
                <span
                  className={cn(
                    "absolute -left-6 top-1.5 h-3 w-3 rounded-full border-2 border-clay-900 shrink-0 z-10",
                    config.dot
                  )}
                />
                <div className="min-w-0 flex-1 rounded-lg border border-clay-700 bg-clay-800 p-3">
                  <div className="flex items-center gap-2 mb-0.5">
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-clay-700 text-clay-300 uppercase font-medium">
                      {update.type}
                    </span>
                    <h4 className="text-sm font-medium text-clay-100 truncate">{update.title}</h4>
                  </div>
                  {update.body && (
                    <p className="text-xs text-clay-400 line-clamp-1 mt-0.5">{update.body}</p>
                  )}
                  <span className="text-[10px] text-clay-500 mt-1 block">
                    {formatRelativeTime(update.created_at)}
                  </span>
                </div>
              </div>
            );
          })}
        </div>
      </div>
      {portal.recent_updates.length > 8 && (
        <button
          onClick={() => onTabChange?.("updates")}
          className="mt-3 text-xs text-clay-400 hover:text-clay-200 flex items-center gap-1"
        >
          View all {portal.recent_updates.length} updates
          <ChevronRight className="h-3 w-3" />
        </button>
      )}
    </div>
  );
}

function WaitingOnClient({
  actions,
  onToggle,
}: {
  actions: PortalAction[];
  onToggle?: (actionId: string) => void;
}) {
  if (actions.length === 0) return null;

  const today = new Date().toISOString().split("T")[0];

  return (
    <div className="rounded-lg border-l-4 border-orange-400 bg-clay-800 border border-clay-700 p-3">
      <h3 className="text-xs font-semibold text-orange-400 mb-2 flex items-center gap-1.5">
        <AlertCircle className="h-3.5 w-3.5" />
        Waiting on Client ({actions.length})
      </h3>
      <div className="space-y-2">
        {actions.map((action) => {
          const isOverdue = action.due_date && action.due_date < today;
          return (
            <div
              key={action.id}
              className="flex items-start gap-2 group"
            >
              <button
                onClick={() => onToggle?.(action.id)}
                className="mt-0.5 h-4 w-4 rounded border border-clay-600 flex items-center justify-center shrink-0 hover:border-clay-400 transition-colors"
                title="Mark done"
              >
                <Check className="h-2.5 w-2.5 text-clay-600 opacity-0 group-hover:opacity-100 transition-opacity" />
              </button>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-1.5">
                  <span
                    className={cn(
                      "h-1.5 w-1.5 rounded-full shrink-0",
                      action.priority === "high" ? "bg-red-400" : action.priority === "low" ? "bg-clay-600" : "bg-clay-400"
                    )}
                  />
                  <span className="text-xs text-clay-200 truncate">{action.title}</span>
                  {isOverdue && (
                    <span className="text-[9px] px-1 py-0.5 rounded bg-red-500/15 text-red-400 font-medium shrink-0">
                      Overdue
                    </span>
                  )}
                </div>
                {action.due_date && (
                  <p className={cn("text-[10px] mt-0.5", isOverdue ? "text-red-400" : "text-clay-500")}>
                    Due: {action.due_date}
                  </p>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}

function SidebarActions({
  actions,
  onToggle,
  onTabChange,
}: {
  actions: PortalAction[];
  onToggle?: (actionId: string) => void;
  onTabChange?: (tab: PortalTab) => void;
}) {
  const openActions = actions.filter((a) => a.status !== "done");
  if (openActions.length === 0) return null;

  const displayed = openActions.slice(0, 5);

  return (
    <div className="rounded-lg border border-clay-700 bg-clay-800 p-3">
      <h3 className="text-xs font-semibold text-clay-200 mb-2 flex items-center gap-1.5">
        <CheckSquare className="h-3.5 w-3.5" />
        Open Actions ({openActions.length})
      </h3>
      <div className="space-y-1.5">
        {displayed.map((action) => (
          <div key={action.id} className="flex items-center gap-2 group">
            <button
              onClick={() => onToggle?.(action.id)}
              className="h-3.5 w-3.5 rounded border border-clay-600 flex items-center justify-center shrink-0 hover:border-clay-400 transition-colors"
              title="Mark done"
            >
              <Check className="h-2 w-2 text-clay-600 opacity-0 group-hover:opacity-100 transition-opacity" />
            </button>
            <span
              className={cn(
                "h-1.5 w-1.5 rounded-full shrink-0",
                action.priority === "high" ? "bg-red-400" : action.priority === "low" ? "bg-clay-600" : "bg-clay-400"
              )}
            />
            <span className="text-xs text-clay-300 truncate flex-1">{action.title}</span>
            <span
              className={cn(
                "text-[9px] px-1 py-0.5 rounded font-medium shrink-0",
                action.owner === "client"
                  ? "text-orange-400 bg-orange-500/10"
                  : "text-clay-400 bg-clay-700"
              )}
            >
              <User className="h-2 w-2 inline mr-0.5" />
              {action.owner}
            </span>
          </div>
        ))}
      </div>
      {openActions.length > 5 && (
        <button
          onClick={() => onTabChange?.("actions")}
          className="mt-2 text-[11px] text-clay-400 hover:text-clay-200 flex items-center gap-1"
        >
          View all {openActions.length} actions
          <ChevronRight className="h-3 w-3" />
        </button>
      )}
    </div>
  );
}

function InlineNotes({
  notes,
  slug,
  onSaved,
}: {
  notes: string;
  slug: string;
  onSaved?: () => void;
}) {
  const [editing, setEditing] = useState(false);
  const [value, setValue] = useState(notes);
  const [saving, setSaving] = useState(false);

  async function handleSave() {
    setSaving(true);
    try {
      await updatePortal(slug, { notes: value });
      toast.success("Notes saved");
      setEditing(false);
      onSaved?.();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to save notes");
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="rounded-lg border border-clay-700 bg-clay-800 p-3">
      <div className="flex items-center justify-between mb-2">
        <h3 className="text-xs font-semibold text-clay-200">Internal Notes</h3>
        {!editing && (
          <button
            onClick={() => setEditing(true)}
            className="text-clay-500 hover:text-clay-300"
            title="Edit notes"
          >
            <Pencil className="h-3 w-3" />
          </button>
        )}
      </div>
      {editing ? (
        <div className="space-y-2">
          <textarea
            value={value}
            onChange={(e) => setValue(e.target.value)}
            rows={4}
            className="w-full rounded-md border border-clay-600 bg-clay-900 px-2.5 py-1.5 text-xs text-clay-100 placeholder:text-clay-500 focus:border-clay-400 focus:outline-none resize-none"
            placeholder="Add internal notes about this client..."
            autoFocus
          />
          <div className="flex items-center gap-2">
            <Button
              size="sm"
              onClick={handleSave}
              disabled={saving}
              className="h-6 text-[11px] px-2"
            >
              {saving ? "Saving..." : "Save"}
            </Button>
            <Button
              variant="ghost"
              size="sm"
              onClick={() => {
                setValue(notes);
                setEditing(false);
              }}
              className="h-6 text-[11px] px-2 text-clay-400"
            >
              Cancel
            </Button>
          </div>
        </div>
      ) : notes ? (
        <p className="text-xs text-clay-400 whitespace-pre-wrap">{notes}</p>
      ) : (
        <button
          onClick={() => setEditing(true)}
          className="text-xs text-clay-500 hover:text-clay-300 italic"
        >
          No notes yet. Click to add.
        </button>
      )}
    </div>
  );
}

// ── Main component ──

export function OverviewTab({ portal, slug, onPortalUpdated, onTabChange, onToggleAction }: OverviewTabProps) {
  const clientActions = portal.actions.filter(
    (a) => a.owner === "client" && a.status !== "done"
  );

  return (
    <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6">
      {/* ── Left column ── */}
      <div className="space-y-6 min-w-0">
        <SummaryBar portal={portal} onTabChange={onTabChange} />
        <PortalInsights portal={portal} onTabChange={onTabChange} />
        <QuickActions onTabChange={onTabChange} />
        <OnboardingChecklist portal={portal} onTabChange={onTabChange} />
        <ActivityTimeline portal={portal} onTabChange={onTabChange} />
      </div>

      {/* ── Right sidebar (stacks below on mobile) ── */}
      <div className="space-y-4 lg:order-none order-last">
        <WaitingOnClient actions={clientActions} onToggle={onToggleAction} />
        <SidebarActions
          actions={portal.actions}
          onToggle={onToggleAction}
          onTabChange={onTabChange}
        />
        <InlineNotes
          notes={portal.meta.notes}
          slug={slug}
          onSaved={onPortalUpdated}
        />
        <NotificationSettings
          slug={slug}
          slackWebhookUrl={portal.meta.slack_webhook_url ?? null}
          notificationEmails={portal.meta.notification_emails ?? []}
          onSaved={() => onPortalUpdated?.()}
          compact
        />
      </div>
    </div>
  );
}
