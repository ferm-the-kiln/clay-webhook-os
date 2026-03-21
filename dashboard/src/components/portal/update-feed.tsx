"use client";

import { Pin, PinOff, Trash2, Milestone, Package, StickyNote, Bell } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { PortalUpdate } from "@/lib/types";
import { MarkdownContent } from "./markdown-content";
import { CommentThread } from "./comment-thread";

const TYPE_CONFIG: Record<string, { icon: React.ElementType; color: string }> = {
  update: { icon: Bell, color: "text-blue-400 bg-blue-500/10" },
  milestone: { icon: Milestone, color: "text-emerald-400 bg-emerald-500/10" },
  deliverable: { icon: Package, color: "text-purple-400 bg-purple-500/10" },
  note: { icon: StickyNote, color: "text-amber-400 bg-amber-500/10" },
};

interface UpdateFeedProps {
  slug: string;
  updates: PortalUpdate[];
  onTogglePin: (updateId: string) => void;
  onDelete: (updateId: string) => void;
}

export function UpdateFeed({ slug, updates, onTogglePin, onDelete }: UpdateFeedProps) {
  if (updates.length === 0) {
    return (
      <div className="text-center py-8 text-clay-400">
        <p className="text-sm">No updates yet. Post your first update to start the activity feed.</p>
      </div>
    );
  }

  // Pinned first, then by created_at desc
  const sorted = [...updates].sort((a, b) => {
    if (a.pinned && !b.pinned) return -1;
    if (!a.pinned && b.pinned) return 1;
    return b.created_at - a.created_at;
  });

  return (
    <div className="space-y-3">
      {sorted.map((update) => {
        const config = TYPE_CONFIG[update.type] || TYPE_CONFIG.update;
        const Icon = config.icon;

        return (
          <div
            key={update.id}
            className={cn(
              "rounded-lg border bg-clay-800 p-4",
              update.pinned ? "border-amber-500/30" : "border-clay-700"
            )}
          >
            <div className="flex items-start gap-3">
              <div className={cn("p-1.5 rounded-md shrink-0", config.color)}>
                <Icon className="h-4 w-4" />
              </div>
              <div className="min-w-0 flex-1">
                <div className="flex items-center gap-2 mb-1">
                  <h4 className="text-sm font-medium text-clay-100">{update.title}</h4>
                  {update.pinned && <Pin className="h-3 w-3 text-amber-400" />}
                </div>
                {update.body && <MarkdownContent content={update.body} />}
                <div className="flex items-center gap-1 mt-2">
                  <span className="text-[10px] text-clay-500">
                    {new Date(update.created_at * 1000).toLocaleString()}
                  </span>
                </div>
                <CommentThread slug={slug} updateId={update.id} />
              </div>
              <div className="flex items-center gap-1 shrink-0">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => onTogglePin(update.id)}
                  className="h-7 w-7 text-clay-400 hover:text-amber-400"
                  title={update.pinned ? "Unpin" : "Pin"}
                >
                  {update.pinned ? <PinOff className="h-3.5 w-3.5" /> : <Pin className="h-3.5 w-3.5" />}
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => onDelete(update.id)}
                  className="h-7 w-7 text-clay-400 hover:text-red-400"
                  title="Delete"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
          </div>
        );
      })}
    </div>
  );
}
