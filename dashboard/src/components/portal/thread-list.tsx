"use client";

import { useState } from "react";
import { MessageSquarePlus, MessageCircle, ChevronRight } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { createThread } from "@/lib/api";
import { toast } from "sonner";
import type { PortalThread } from "@/lib/types";

function getStoredAuthor(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("portal_author_name") || "";
}

function formatRelativeTime(epochSeconds: number): string {
  const now = Date.now() / 1000;
  const diff = now - epochSeconds;
  if (diff < 60) return "just now";
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`;
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`;
  if (diff < 604800) return `${Math.floor(diff / 86400)}d ago`;
  const date = new Date(epochSeconds * 1000);
  return date.toLocaleDateString(undefined, { month: "short", day: "numeric" });
}

interface ThreadListProps {
  slug: string;
  projectId: string;
  threads: PortalThread[];
  onSelectThread: (threadId: string) => void;
  onReload: () => void;
}

export function ThreadList({ slug, projectId, threads, onSelectThread, onReload }: ThreadListProps) {
  const [creating, setCreating] = useState(false);
  const [title, setTitle] = useState("");
  const [body, setBody] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const handleCreate = async () => {
    if (!title.trim() || !body.trim()) return;
    const author = getStoredAuthor() || "Anonymous";
    setSubmitting(true);
    try {
      const thread = await createThread(slug, projectId, {
        title: title.trim(),
        body: body.trim(),
        author,
      });
      toast.success("Discussion started");
      setTitle("");
      setBody("");
      setCreating(false);
      onReload();
      onSelectThread(thread.id);
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to create discussion");
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-clay-200">
          Discussions ({threads.length})
        </h3>
        <Button
          variant="outline"
          size="sm"
          onClick={() => setCreating(!creating)}
          className="border-clay-600 text-clay-200 hover:bg-clay-700 gap-1.5"
        >
          <MessageSquarePlus className="h-3.5 w-3.5" />
          New Discussion
        </Button>
      </div>

      {/* Create form */}
      {creating && (
        <div className="rounded-lg border border-kiln-teal/30 bg-clay-800 p-4 space-y-3">
          <input
            type="text"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            placeholder="Discussion topic..."
            className="w-full bg-clay-900 border border-clay-600 rounded-md px-3 py-1.5 text-sm text-clay-100 placeholder:text-clay-500 focus:outline-none focus:border-kiln-teal"
            autoFocus
          />
          <textarea
            value={body}
            onChange={(e) => setBody(e.target.value)}
            placeholder="Start the conversation..."
            rows={3}
            className="w-full bg-clay-900 border border-clay-600 rounded-md px-3 py-2 text-sm text-clay-100 placeholder:text-clay-500 focus:outline-none focus:border-kiln-teal resize-y"
          />
          <div className="flex items-center gap-2 justify-end">
            <Button
              variant="ghost"
              size="sm"
              onClick={() => setCreating(false)}
              className="text-clay-300 hover:text-clay-100"
            >
              Cancel
            </Button>
            <Button
              size="sm"
              onClick={handleCreate}
              disabled={submitting || !title.trim() || !body.trim()}
              className="bg-kiln-teal text-clay-900 hover:bg-kiln-teal/90"
            >
              {submitting ? "Starting..." : "Start Discussion"}
            </Button>
          </div>
        </div>
      )}

      {/* Thread list */}
      {threads.length === 0 && !creating && (
        <div className="text-center py-8 text-clay-400">
          <MessageCircle className="h-8 w-8 mx-auto mb-2 opacity-40" />
          <p className="text-sm">No discussions yet. Start one to collaborate with the team.</p>
        </div>
      )}

      {threads.map((thread) => (
        <button
          key={thread.id}
          onClick={() => onSelectThread(thread.id)}
          className="w-full text-left rounded-lg border border-clay-700 bg-clay-800 p-3 hover:border-clay-500 transition-colors group"
        >
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0 flex-1">
              <h4 className="text-sm font-medium text-clay-100 truncate group-hover:text-white">
                {thread.title}
              </h4>
              <div className="flex items-center gap-2 mt-1">
                <span className="text-[11px] text-clay-400">{thread.created_by}</span>
                <span className="text-[11px] text-clay-500">|</span>
                <span className="text-[11px] text-clay-400">
                  {thread.message_count} message{thread.message_count !== 1 ? "s" : ""}
                </span>
                <span className="text-[11px] text-clay-500">|</span>
                <span className="text-[11px] text-clay-400">{formatRelativeTime(thread.updated_at)}</span>
              </div>
              {thread.last_message_preview && (
                <p className="text-xs text-clay-300 mt-1 truncate">
                  {thread.last_message_author && <span className="text-clay-200">{thread.last_message_author}: </span>}
                  {thread.last_message_preview}
                </p>
              )}
            </div>
            <ChevronRight className="h-4 w-4 text-clay-400 shrink-0 mt-0.5 group-hover:text-clay-200" />
          </div>
        </button>
      ))}
    </div>
  );
}
