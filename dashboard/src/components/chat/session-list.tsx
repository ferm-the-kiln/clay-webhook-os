"use client";

import type { ChannelSessionSummary } from "@/lib/types";
import { cn, formatRelativeTime } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import {
  Plus,
  MessageSquare,
  MessageCircle,
  PanelLeftClose,
} from "lucide-react";

interface SessionListProps {
  sessions: ChannelSessionSummary[];
  activeSessionId: string | null;
  onSelect: (sessionId: string) => void;
  onCreate: () => void;
  collapsed: boolean;
  onToggleCollapse: () => void;
}

export function SessionList({
  sessions,
  activeSessionId,
  onSelect,
  onCreate,
  collapsed,
  onToggleCollapse,
}: SessionListProps) {
  return (
    <div
      className={cn(
        "border-r border-clay-600 bg-clay-800 flex flex-col transition-all duration-200",
        collapsed ? "w-0 overflow-hidden" : "w-70"
      )}
    >
      {/* Header */}
      <div className="flex items-center justify-between px-3 pt-3 pb-2">
        <span className="text-xs font-semibold text-clay-100 uppercase tracking-wider">
          Sessions
        </span>
        <Button
          variant="ghost"
          size="icon"
          className="h-7 w-7 text-clay-200 hover:text-clay-100 hover:bg-clay-700"
          onClick={onToggleCollapse}
          aria-label="Collapse session list"
        >
          <PanelLeftClose className="h-4 w-4" />
        </Button>
      </div>

      {/* New chat button */}
      <div className="px-3 pb-2">
        <Button
          variant="outline"
          className="w-full border-clay-600 text-clay-200 hover:bg-clay-700 hover:text-clay-100"
          onClick={onCreate}
        >
          <Plus className="h-4 w-4 mr-2" />
          New chat
        </Button>
      </div>

      {/* Session list */}
      <div className="flex-1 overflow-y-auto">
        {sessions.length === 0 ? (
          <p className="text-xs text-clay-300 py-8 text-center">
            No sessions yet
          </p>
        ) : (
          sessions.map((session) => {
            const isActive = session.id === activeSessionId;
            const isFreeChat = !session.function_id;
            const Icon = isFreeChat ? MessageCircle : MessageSquare;
            return (
              <button
                key={session.id}
                className={cn(
                  "w-full text-left px-3 py-2.5 transition-colors duration-150 cursor-pointer",
                  isActive
                    ? "bg-kiln-teal/10 border-l-2 border-kiln-teal"
                    : "hover:bg-clay-700 border-l-2 border-transparent"
                )}
                onClick={() => onSelect(session.id)}
              >
                <div className="flex items-start gap-2 min-w-0">
                  <Icon className="h-3.5 w-3.5 mt-0.5 shrink-0 text-clay-300" />
                  <div className="min-w-0 flex-1">
                    <p
                      className={cn(
                        "text-sm font-medium truncate",
                        isActive ? "text-kiln-teal" : "text-clay-100"
                      )}
                    >
                      {session.title || session.function_name || "Untitled"}
                    </p>
                    <p className="text-xs text-clay-200 truncate">
                      {isFreeChat ? "Free chat" : session.function_name} &mdash; {session.message_count}{" "}
                      messages
                    </p>
                    <p className="text-[11px] text-clay-300 font-mono tabular-nums mt-0.5">
                      {formatRelativeTime(session.updated_at)}
                    </p>
                  </div>
                </div>
              </button>
            );
          })
        )}
      </div>
    </div>
  );
}
