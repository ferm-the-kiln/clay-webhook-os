"use client";

import { useState } from "react";
import { AlertCircle, Clock, Check, ChevronDown, ChevronUp } from "lucide-react";
import { cn } from "@/lib/utils";
import type { PortalAction } from "@/lib/types";

interface AttentionStripProps {
  clientActions: PortalAction[];
  overdueActions: PortalAction[];
  onToggleAction: (id: string) => void;
}

export function AttentionStrip({ clientActions, overdueActions, onToggleAction }: AttentionStripProps) {
  const [expanded, setExpanded] = useState(false);

  if (clientActions.length === 0 && overdueActions.length === 0) return null;

  return (
    <div className="rounded-lg border border-clay-700 bg-clay-800 overflow-hidden">
      <button
        onClick={() => setExpanded(!expanded)}
        className="w-full flex items-center gap-3 px-4 py-2.5 hover:bg-clay-750 transition-colors"
      >
        <div className="flex items-center gap-3 flex-wrap flex-1">
          {overdueActions.length > 0 && (
            <span className="flex items-center gap-1.5 text-xs text-red-400">
              <Clock className="h-3.5 w-3.5" />
              {overdueActions.length} overdue
            </span>
          )}
          {clientActions.length > 0 && (
            <span className="flex items-center gap-1.5 text-xs text-orange-400">
              <AlertCircle className="h-3.5 w-3.5" />
              {clientActions.length} waiting on client
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
        <div className="border-t border-clay-700 px-4 py-3 space-y-2">
          {[...overdueActions, ...clientActions.filter((a) => !overdueActions.some((o) => o.id === a.id))].map((action) => {
            const today = new Date().toISOString().split("T")[0];
            const isOverdue = action.due_date && action.due_date < today;
            const isClient = action.owner === "client";

            return (
              <div key={action.id} className="flex items-start gap-2 group">
                <button
                  onClick={() => onToggleAction(action.id)}
                  className="mt-0.5 h-4 w-4 rounded border border-clay-600 flex items-center justify-center shrink-0 hover:border-clay-400 transition-colors"
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
      )}
    </div>
  );
}
