"use client";

import { useState } from "react";
import { Plus, Pencil, Trash2, CheckSquare, Square, Calendar, User, Repeat, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { PortalAction } from "@/lib/types";
import { ActionEditor } from "./action-editor";

const PRIORITY_DOTS: Record<string, string> = {
  high: "bg-red-400",
  normal: "bg-clay-400",
  low: "bg-clay-600",
};

const OWNER_BADGE: Record<string, string> = {
  internal: "text-blue-400 bg-blue-500/10",
  client: "text-orange-400 bg-orange-500/10",
};

interface ActionListProps {
  slug: string;
  actions: PortalAction[];
  onCreated: () => void;
  onUpdated: () => void;
  onToggle: (actionId: string) => void;
  onDelete: (actionId: string) => void;
}

export function ActionList({ slug, actions, onCreated, onUpdated, onToggle, onDelete }: ActionListProps) {
  const [creating, setCreating] = useState(false);
  const [editingId, setEditingId] = useState<string | null>(null);

  // Sort: blocked first, then open/in_progress (by priority), done at bottom
  const priorityOrder: Record<string, number> = { high: 0, normal: 1, low: 2 };
  const sorted = [...actions].sort((a, b) => {
    const aIsDone = a.status === "done" ? 1 : 0;
    const bIsDone = b.status === "done" ? 1 : 0;
    if (aIsDone !== bIsDone) return aIsDone - bIsDone;
    const aBlocked = a.blocked_by_client ? 0 : 1;
    const bBlocked = b.blocked_by_client ? 0 : 1;
    if (aBlocked !== bBlocked) return aBlocked - bBlocked;
    return (priorityOrder[a.priority] ?? 1) - (priorityOrder[b.priority] ?? 1);
  });

  const openCount = actions.filter((a) => a.status !== "done").length;
  const blockedCount = actions.filter((a) => a.blocked_by_client && a.status !== "done").length;

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-clay-200 flex items-center gap-2">
          Action Items ({openCount} open, {actions.length} total)
          {blockedCount > 0 && (
            <span className="text-[10px] px-2 py-0.5 rounded-full bg-amber-500/10 text-amber-400 font-medium">
              {blockedCount} blocked
            </span>
          )}
        </h3>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setCreating(true)}
          className="border-clay-600 text-clay-200 hover:bg-clay-700 gap-1.5"
        >
          <Plus className="h-3.5 w-3.5" />
          New Action
        </Button>
      </div>

      {creating && (
        <ActionEditor
          slug={slug}
          onSaved={() => {
            setCreating(false);
            onCreated();
          }}
          onCancel={() => setCreating(false)}
        />
      )}

      {sorted.length === 0 && !creating && (
        <div className="text-center py-8 text-clay-400">
          <p className="text-sm">No action items yet. Create one to track mutual accountability.</p>
        </div>
      )}

      {sorted.map((action) => (
        <div key={action.id} className={cn(
          "rounded-lg border bg-clay-800 overflow-hidden",
          action.blocked_by_client && action.status !== "done"
            ? "border-amber-500/30 border-l-2 border-l-amber-400"
            : "border-clay-700"
        )}>
          {editingId === action.id ? (
            <ActionEditor
              slug={slug}
              action={action}
              onSaved={() => {
                setEditingId(null);
                onUpdated();
              }}
              onCancel={() => setEditingId(null)}
            />
          ) : (
            <div className="flex items-start gap-3 p-3">
              {/* Toggle checkbox */}
              <button
                onClick={() => onToggle(action.id)}
                className="mt-0.5 text-clay-400 hover:text-kiln-teal transition-colors"
              >
                {action.status === "done" ? (
                  <CheckSquare className="h-4.5 w-4.5 text-emerald-400" />
                ) : (
                  <Square className="h-4.5 w-4.5" />
                )}
              </button>

              {/* Content */}
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2">
                  {/* Priority dot */}
                  <span className={cn("h-2 w-2 rounded-full shrink-0", PRIORITY_DOTS[action.priority])} />
                  <span
                    className={cn(
                      "text-sm font-medium truncate",
                      action.status === "done" ? "text-clay-400 line-through" : "text-clay-100"
                    )}
                  >
                    {action.title}
                  </span>
                  {/* Owner badge */}
                  <span
                    className={cn(
                      "text-[10px] px-1.5 py-0.5 rounded-full font-medium shrink-0",
                      OWNER_BADGE[action.owner] || OWNER_BADGE.internal
                    )}
                  >
                    <User className="h-2.5 w-2.5 inline mr-0.5" />
                    {action.owner}
                  </span>
                  {/* Blocked badge */}
                  {action.blocked_by_client && action.status !== "done" && (
                    <span className="text-[10px] px-1.5 py-0.5 rounded-full font-medium shrink-0 text-amber-400 bg-amber-500/10 flex items-center gap-0.5">
                      <AlertTriangle className="h-2.5 w-2.5" />
                      Waiting on you
                    </span>
                  )}
                </div>

                {action.description && (
                  <p className="text-xs text-clay-300 mt-0.5 line-clamp-1">{action.description}</p>
                )}
                {action.blocked_by_client && action.blocked_reason && action.status !== "done" && (
                  <p className="text-xs text-amber-400/70 mt-0.5 line-clamp-1">Blocked: {action.blocked_reason}</p>
                )}

                <div className="flex flex-wrap items-center gap-2 mt-1">
                  {action.due_date && (
                    <span className="text-[11px] text-clay-400 flex items-center gap-1">
                      <Calendar className="h-3 w-3" />
                      {action.due_date}
                    </span>
                  )}
                  {action.recurrence && action.recurrence !== "none" && (
                    <span className="text-[11px] text-clay-400 flex items-center gap-1">
                      <Repeat className="h-3 w-3" />
                      {action.recurrence}
                    </span>
                  )}
                </div>
              </div>

              {/* Actions */}
              <div className="flex items-center gap-1 shrink-0">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setEditingId(action.id)}
                  className="text-clay-400 hover:text-clay-100 h-7 w-7 p-0"
                >
                  <Pencil className="h-3 w-3" />
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => onDelete(action.id)}
                  className="text-clay-400 hover:text-red-400 h-7 w-7 p-0"
                >
                  <Trash2 className="h-3 w-3" />
                </Button>
              </div>
            </div>
          )}
        </div>
      ))}
    </div>
  );
}
