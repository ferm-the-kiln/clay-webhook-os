"use client";

import { useState } from "react";
import { Plus, CheckSquare, Square, Calendar, ChevronDown, ChevronUp, Trash2, AlertTriangle } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { toast } from "sonner";
import { createAction, deleteAction } from "@/lib/api";
import type { PortalAction } from "@/lib/types";

const PRIORITY_DOTS: Record<string, string> = {
  high: "bg-red-400",
  normal: "bg-clay-400",
  low: "bg-clay-600",
};

interface ProjectActionsSectionProps {
  slug: string;
  projectId: string;
  actions: PortalAction[];
  onToggle: (actionId: string) => void;
  onReload: () => void;
}

export function ProjectActionsSection({ slug, projectId, actions, onToggle, onReload }: ProjectActionsSectionProps) {
  const [expanded, setExpanded] = useState(false);
  const [adding, setAdding] = useState(false);
  const [newTitle, setNewTitle] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const COLLAPSE_THRESHOLD = 5;
  const openCount = actions.filter((a) => a.status !== "done").length;

  // Sort: blocked first, then open (by priority), done at bottom
  const priorityOrder: Record<string, number> = { high: 0, normal: 1, low: 2 };
  const sorted = [...actions].sort((a, b) => {
    const aD = a.status === "done" ? 1 : 0;
    const bD = b.status === "done" ? 1 : 0;
    if (aD !== bD) return aD - bD;
    const aBlocked = a.blocked_by_client ? 0 : 1;
    const bBlocked = b.blocked_by_client ? 0 : 1;
    if (aBlocked !== bBlocked) return aBlocked - bBlocked;
    return (priorityOrder[a.priority] ?? 1) - (priorityOrder[b.priority] ?? 1);
  });

  const visible = expanded ? sorted : sorted.slice(0, COLLAPSE_THRESHOLD);

  const handleAdd = async () => {
    if (!newTitle.trim()) return;
    setSubmitting(true);
    try {
      await createAction(slug, {
        title: newTitle.trim(),
        project_id: projectId,
      });
      setNewTitle("");
      setAdding(false);
      onReload();
      toast.success("Action created");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to create action");
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (actionId: string) => {
    try {
      await deleteAction(slug, actionId);
      onReload();
      toast.success("Action deleted");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to delete action");
    }
  };

  return (
    <div className="rounded-xl border border-clay-600 bg-clay-800 p-4">
      <div className="flex items-center justify-between mb-3">
        <h3 className="text-xs font-medium text-clay-100 uppercase tracking-wider flex items-center gap-1.5">
          <CheckSquare className="h-3 w-3" />
          Actions
          {openCount > 0 && (
            <span className="text-[11px] text-clay-300">({openCount} open)</span>
          )}
        </h3>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setAdding(!adding)}
          className="h-6 text-[11px] text-clay-400 hover:text-clay-200 hover:bg-clay-700 gap-1"
        >
          <Plus className="h-3 w-3" />
        </Button>
      </div>

      {/* Quick add */}
      {adding && (
        <div className="flex gap-2 mb-3">
          <input
            type="text"
            value={newTitle}
            onChange={(e) => setNewTitle(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && handleAdd()}
            placeholder="Action title..."
            className="flex-1 bg-clay-900 border border-clay-600 rounded-md px-2.5 py-1 text-xs text-clay-100 placeholder:text-clay-500 focus:outline-none focus:border-kiln-teal"
            autoFocus
          />
          <Button
            variant="outline"
            size="sm"
            onClick={handleAdd}
            disabled={submitting || !newTitle.trim()}
            className="h-7 border-clay-600 text-clay-300 hover:bg-clay-700 text-xs"
          >
            Add
          </Button>
        </div>
      )}

      {actions.length === 0 && !adding ? (
        <p className="text-xs text-clay-400">No actions yet</p>
      ) : (
        <div className="space-y-1">
          {visible.map((action) => (
            <div
              key={action.id}
              className="flex items-center gap-2 group py-1"
            >
              <button
                onClick={() => onToggle(action.id)}
                className="flex-shrink-0"
              >
                {action.status === "done" ? (
                  <CheckSquare className="h-3.5 w-3.5 text-emerald-500" />
                ) : (
                  <Square className="h-3.5 w-3.5 text-clay-400 hover:text-clay-200" />
                )}
              </button>

              <span
                className={cn(
                  "h-1.5 w-1.5 rounded-full flex-shrink-0",
                  PRIORITY_DOTS[action.priority] || PRIORITY_DOTS.normal,
                )}
              />

              <span
                className={cn(
                  "text-sm flex-1 truncate",
                  action.status === "done" ? "text-clay-400 line-through" : "text-clay-100",
                )}
              >
                {action.title}
              </span>

              {action.blocked_by_client && action.status !== "done" && (
                <span className="text-amber-400 flex-shrink-0" title={action.blocked_reason || "Blocked by client"}>
                  <AlertTriangle className="h-3 w-3" />
                </span>
              )}

              {action.due_date && (
                <span className="text-[10px] text-clay-400 flex items-center gap-0.5 flex-shrink-0">
                  <Calendar className="h-2.5 w-2.5" />
                  {new Date(action.due_date + "T00:00:00").toLocaleDateString(undefined, { month: "short", day: "numeric" })}
                </span>
              )}

              <button
                onClick={() => handleDelete(action.id)}
                className="opacity-0 group-hover:opacity-100 text-clay-500 hover:text-red-400 transition-opacity flex-shrink-0"
              >
                <Trash2 className="h-3 w-3" />
              </button>
            </div>
          ))}
        </div>
      )}

      {sorted.length > COLLAPSE_THRESHOLD && (
        <button
          onClick={() => setExpanded(!expanded)}
          className="flex items-center gap-1 mt-2 text-[10px] text-clay-400 hover:text-clay-200 transition-colors"
        >
          {expanded ? (
            <>
              <ChevronUp className="h-3 w-3" />
              Show less
            </>
          ) : (
            <>
              <ChevronDown className="h-3 w-3" />
              {sorted.length - COLLAPSE_THRESHOLD} more
            </>
          )}
        </button>
      )}
    </div>
  );
}
