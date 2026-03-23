"use client";

import { useState, useEffect, useRef } from "react";
import { ArrowLeft, Send, Trash2 } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { fetchThread, postThreadMessage, deleteThread } from "@/lib/api";
import { toast } from "sonner";
import type { ThreadDetail as ThreadDetailType } from "@/lib/types";

function getStoredAuthor(): string {
  if (typeof window === "undefined") return "";
  return localStorage.getItem("portal_author_name") || "";
}

function formatTime(epoch: number): string {
  return new Date(epoch * 1000).toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    hour: "numeric",
    minute: "2-digit",
  });
}

interface ThreadDetailProps {
  slug: string;
  threadId: string;
  onBack: () => void;
  onDeleted: () => void;
}

export function ThreadDetail({ slug, threadId, onBack, onDeleted }: ThreadDetailProps) {
  const [thread, setThread] = useState<ThreadDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [message, setMessage] = useState("");
  const [sending, setSending] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const loadThread = async () => {
    try {
      const data = await fetchThread(slug, threadId);
      setThread(data);
    } catch {
      toast.error("Failed to load thread");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadThread();
  }, [slug, threadId]); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [thread?.messages?.length]);

  const handleSend = async () => {
    if (!message.trim()) return;
    const author = getStoredAuthor() || "Anonymous";
    setSending(true);
    try {
      const updated = await postThreadMessage(slug, threadId, {
        body: message.trim(),
        author,
      });
      setThread(updated);
      setMessage("");
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to send message");
    } finally {
      setSending(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Delete this discussion? This cannot be undone.")) return;
    try {
      await deleteThread(slug, threadId);
      toast.success("Discussion deleted");
      onDeleted();
    } catch (e) {
      toast.error(e instanceof Error ? e.message : "Failed to delete");
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center py-12">
        <div className="animate-spin h-5 w-5 border-2 border-clay-500 border-t-kiln-teal rounded-full" />
      </div>
    );
  }

  if (!thread) {
    return (
      <div className="text-center py-8 text-clay-400">
        <p>Thread not found.</p>
        <Button variant="ghost" size="sm" onClick={onBack} className="mt-2">Go back</Button>
      </div>
    );
  }

  const currentUser = getStoredAuthor();

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="flex items-center gap-2 pb-3 border-b border-clay-700/40">
        <Button
          variant="ghost"
          size="sm"
          onClick={onBack}
          className="text-clay-400 hover:text-clay-100 h-7 w-7 p-0"
        >
          <ArrowLeft className="h-4 w-4" />
        </Button>
        <div className="flex-1 min-w-0">
          <h3 className="text-sm font-semibold text-clay-100 truncate">{thread.title}</h3>
          <span className="text-[11px] text-clay-400">
            Started by {thread.created_by} | {thread.messages.length} message{thread.messages.length !== 1 ? "s" : ""}
          </span>
        </div>
        <Button
          variant="ghost"
          size="sm"
          onClick={handleDelete}
          className="text-clay-400 hover:text-red-400 h-7 w-7 p-0"
        >
          <Trash2 className="h-3.5 w-3.5" />
        </Button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto py-3 space-y-3 min-h-0 max-h-[400px]">
        {thread.messages.map((msg) => {
          const isOwnMessage = msg.author === currentUser;
          const isInternal = msg.author_org === "internal";
          return (
            <div key={msg.id} className={cn("flex gap-2", isOwnMessage && "flex-row-reverse")}>
              {/* Avatar */}
              <div className={cn(
                "h-7 w-7 rounded-full flex items-center justify-center shrink-0 text-xs font-semibold",
                isInternal ? "bg-kiln-teal/20 text-kiln-teal" : "bg-purple-500/20 text-purple-400"
              )}>
                {msg.author.charAt(0).toUpperCase()}
              </div>
              {/* Bubble */}
              <div className={cn(
                "max-w-[80%] rounded-lg px-3 py-2",
                isOwnMessage
                  ? "bg-kiln-teal/10 border border-kiln-teal/20"
                  : "bg-clay-700/50 border border-clay-700"
              )}>
                <div className="flex items-center gap-2 mb-0.5">
                  <span className="text-[10px] font-medium text-clay-200">{msg.author}</span>
                  <span className="text-[10px] text-clay-400">{formatTime(msg.created_at)}</span>
                </div>
                <p className="text-xs text-clay-100 whitespace-pre-wrap">{msg.body}</p>
              </div>
            </div>
          );
        })}
        <div ref={messagesEndRef} />
      </div>

      {/* Reply input */}
      <div className="flex gap-2 pt-3 border-t border-clay-700/40">
        <input
          type="text"
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              handleSend();
            }
          }}
          placeholder="Type a reply..."
          className="flex-1 bg-clay-900 border border-clay-600 rounded-md px-3 py-1.5 text-sm text-clay-100 placeholder:text-clay-500 focus:outline-none focus:border-kiln-teal"
        />
        <Button
          size="sm"
          onClick={handleSend}
          disabled={sending || !message.trim()}
          className="bg-kiln-teal text-clay-900 hover:bg-kiln-teal/90 h-8 w-8 p-0"
        >
          <Send className="h-3.5 w-3.5" />
        </Button>
      </div>
    </div>
  );
}
