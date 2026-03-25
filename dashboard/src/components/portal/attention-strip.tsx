"use client";

import { useState, useEffect } from "react";
import { AlertCircle, Clock, Check, ChevronDown, ChevronUp, BellOff } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PortalAction } from "@/lib/types";

interface AttentionStripProps {
  clientActions: PortalAction[];
  overdueActions: PortalAction[];
  onToggleAction: (id: string) => void;
  slug?: string;
}

function getDueDateContext(dueDate: string): { label: string; urgency: "overdue" | "today" | "soon" | "normal" } {
  const today = new Date();
  today.setHours(0, 0, 0, 0);
  const due = new Date(dueDate + "T00:00:00");
  const diffMs = due.getTime() - today.getTime();
  const diffDays = Math.round(diffMs / (1000 * 60 * 60 * 24));

  if (diffDays < 0) {
    const absDays = Math.abs(diffDays);
    return { label: absDays === 1 ? "1 day overdue" : `${absDays} days overdue`, urgency: "overdue" };
  }
  if (diffDays === 0) return { label: "Due today", urgency: "today" };
  if (diffDays === 1) return { label: "Due tomorrow", urgency: "soon" };
  if (diffDays <= 3) return { label: `Due in ${diffDays} days`, urgency: "soon" };
  return { label: `Due ${dueDate}`, urgency: "normal" };
}

function getSnoozedIds(slug: string): Set<string> {
  if (typeof window === "undefined") return new Set();
  try {
    const raw = localStorage.getItem(`snoozed-actions:${slug}`);
    if (!raw) return new Set();
    const parsed: Record<string, number> = JSON.parse(raw);
    const now = Date.now();
    const active: string[] = [];
    const cleaned: Record<string, number> = {};
    for (const [id, expiresAt] of Object.entries(parsed)) {
      if (expiresAt > now) {
        active.push(id);
        cleaned[id] = expiresAt;
      }
    }
    // Clean up expired entries
    if (Object.keys(cleaned).length !== Object.keys(parsed).length) {
      localStorage.setItem(`snoozed-actions:${slug}`, JSON.stringify(cleaned));
    }
    return new Set(active);
  } catch {
    return new Set();
  }
}

function snoozeAction(slug: string, actionId: string) {
  if (typeof window === "undefined") return;
  try {
    const raw = localStorage.getItem(`snoozed-actions:${slug}`);
    const parsed: Record<string, number> = raw ? JSON.parse(raw) : {};
    parsed[actionId] = Date.now() + 24 * 60 * 60 * 1000; // 24h from now
    localStorage.setItem(`snoozed-actions:${slug}`, JSON.stringify(parsed));
  } catch { /* ignore */ }
}

export function AttentionStrip({ clientActions, overdueActions, onToggleAction, slug = "" }: AttentionStripProps) {
  const [expanded, setExpanded] = useState(false);
  const [snoozedIds, setSnoozedIds] = useState<Set<string>>(new Set());

  useEffect(() => {
    setSnoozedIds(getSnoozedIds(slug));
  }, [slug]);

  const handleSnooze = (actionId: string) => {
    snoozeAction(slug, actionId);
    setSnoozedIds(getSnoozedIds(slug));
  };

  // Merge and dedupe, then filter snoozed
  const allActions = [
    ...overdueActions,
    ...clientActions.filter((a) => !overdueActions.some((o) => o.id === a.id)),
  ].filter((a) => !snoozedIds.has(a.id));

  const visibleOverdue = overdueActions.filter((a) => !snoozedIds.has(a.id));
  const visibleClient = clientActions.filter((a) => !snoozedIds.has(a.id));

  if (visibleClient.length === 0 && visibleOverdue.length === 0) return null;

  return (
    <div className="rounded-lg border border-red-500/20 bg-clay-800 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-clay-750/50 transition-colors"
      >
        <div className="flex items-center gap-3 flex-wrap flex-1">
          {visibleOverdue.length > 0 && (
            <span className="flex items-center gap-1.5 text-xs font-medium text-clay-200">
              <span className="h-1.5 w-1.5 rounded-full bg-red-400" />
              {visibleOverdue.length} overdue
            </span>
          )}
          {visibleClient.length > 0 && (
            <span className="flex items-center gap-1.5 text-xs font-medium text-clay-200">
              <span className="h-1.5 w-1.5 rounded-full bg-orange-400" />
              {visibleClient.length} waiting on client
            </span>
          )}
        </div>
        {expanded ? (
          <ChevronUp className="h-4 w-4 text-clay-400 shrink-0" />
        ) : (
          <ChevronDown className="h-4 w-4 text-clay-400 shrink-0" />
        )}
      </button>

      {expanded && (
        <div className="border-t border-clay-700/50 px-4 py-3 space-y-2">
          {allActions.map((action) => {
            const today = new Date().toISOString().split("T")[0];
            const isOverdue = action.due_date && action.due_date < today;
            const isClient = action.owner === "client";
            const dateCtx = action.due_date ? getDueDateContext(action.due_date) : null;

            return (
              <div key={action.id} className="flex items-start gap-2 group">
                <button
                  onClick={() => onToggleAction(action.id)}
                  className="mt-0.5 h-4 w-4 rounded border border-clay-600 flex items-center justify-center shrink-0 hover:border-emerald-400 hover:bg-emerald-400/10 transition-colors"
                  title="Mark done"
                >
                  <Check className="h-2.5 w-2.5 text-clay-600 opacity-0 group-hover:opacity-100 transition-opacity" />
                </button>
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-1.5 flex-wrap">
                    <span className={cn(
                      "h-1.5 w-1.5 rounded-full shrink-0",
                      action.priority === "high" ? "bg-red-400" : action.priority === "low" ? "bg-clay-600" : "bg-clay-400"
                    )} />
                    <span className="text-xs text-clay-200">{action.title}</span>
                    {isOverdue && (
                      <span className="text-[9px] px-1 py-0.5 rounded bg-red-500/15 text-red-400 font-medium">Overdue</span>
                    )}
                    {isClient && (
                      <span className="text-[9px] px-1 py-0.5 rounded bg-orange-500/15 text-orange-400 font-medium">Client</span>
                    )}
                  </div>
                  {dateCtx && (
                    <p className={cn(
                      "text-[10px] mt-0.5",
                      dateCtx.urgency === "overdue" ? "text-red-400" :
                      dateCtx.urgency === "today" ? "text-amber-400" :
                      dateCtx.urgency === "soon" ? "text-amber-400/70" :
                      "text-clay-500"
                    )}>
                      {dateCtx.label}
                    </p>
                  )}
                </div>
                <button
                  onClick={(e) => { e.stopPropagation(); handleSnooze(action.id); }}
                  className="opacity-0 group-hover:opacity-100 mt-0.5 text-clay-500 hover:text-clay-300 transition-all shrink-0"
                  title="Snooze for 24 hours"
                >
                  <BellOff className="h-3 w-3" />
                </button>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
