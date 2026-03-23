"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import type { ChannelMessage } from "@/lib/types";
import { ChatMessage } from "./chat-message";
import { EmptyState } from "@/components/ui/empty-state";
import { MessageSquare, ChevronDown, Download } from "lucide-react";

interface ChatThreadProps {
  messages: ChannelMessage[];
  streaming: boolean;
  sessionTitle?: string;
}

function exportAsMarkdown(messages: ChannelMessage[], title: string) {
  const lines: string[] = [];
  lines.push(`# ${title}`);
  lines.push(`\n*Exported ${new Date().toLocaleString()}*\n`);
  lines.push("---\n");

  for (const msg of messages) {
    if (msg.role === "user") {
      lines.push(`> **You:** ${msg.content.replace(/\n/g, "\n> ")}\n`);
    } else {
      lines.push(msg.content || "*(no response)*");
      if (msg.results && msg.results.length > 0) {
        lines.push("\n```json\n" + JSON.stringify(msg.results, null, 2) + "\n```");
      }
      lines.push("");
    }
  }

  const markdown = lines.join("\n");
  const blob = new Blob([markdown], { type: "text/markdown;charset=utf-8" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `${title.replace(/[^a-z0-9]+/gi, "-").toLowerCase() || "chat"}.md`;
  a.click();
  URL.revokeObjectURL(url);
}

export function ChatThread({ messages, streaming, sessionTitle }: ChatThreadProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const sentinelRef = useRef<HTMLDivElement>(null);
  const [showScrollButton, setShowScrollButton] = useState(false);

  // Check if user is near bottom
  const isNearBottom = useCallback(() => {
    const el = containerRef.current;
    if (!el) return true;
    return el.scrollHeight - el.scrollTop - el.clientHeight < 100;
  }, []);

  // Track scroll position
  const handleScroll = useCallback(() => {
    setShowScrollButton(!isNearBottom());
  }, [isNearBottom]);

  // Auto-scroll when messages change or during streaming
  useEffect(() => {
    // Always scroll to bottom when message count changes (new message sent/received)
    // or when streaming (content updating in last message)
    const shouldScroll = isNearBottom() || streaming;
    if (shouldScroll) {
      sentinelRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, streaming, isNearBottom]);

  // Scroll to bottom action
  const scrollToBottom = useCallback(() => {
    sentinelRef.current?.scrollIntoView({ behavior: "smooth" });
    setShowScrollButton(false);
  }, []);

  if (messages.length === 0) {
    return (
      <div className="flex-1 flex items-center justify-center p-6">
        <EmptyState
          title="Ready to go"
          description="Ask anything, or pick a function to process data."
          icon={MessageSquare}
        />
      </div>
    );
  }

  return (
    <div className="flex-1 relative overflow-hidden">
      {/* Export button — top right, visible when there are messages */}
      {messages.length > 0 && (
        <button
          onClick={() => exportAsMarkdown(messages, sessionTitle || "Chat")}
          aria-label="Export chat as Markdown"
          className="absolute top-3 right-3 z-10 flex items-center gap-1 text-xs text-clay-300 hover:text-clay-100 bg-clay-800/80 hover:bg-clay-700 border border-clay-700 rounded px-2 py-1 transition-colors backdrop-blur-sm"
        >
          <Download className="h-3 w-3" />
          Export
        </button>
      )}
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="h-full overflow-y-auto p-4 space-y-4"
      >
        {messages.map((msg, i) => (
          <ChatMessage
            key={`${msg.timestamp}-${i}`}
            message={msg}
            isStreaming={streaming && i === messages.length - 1}
          />
        ))}
        <div ref={sentinelRef} />
      </div>

      {/* Scroll to bottom button */}
      {showScrollButton && messages.length > 0 && (
        <button
          onClick={scrollToBottom}
          aria-label="Scroll to latest messages"
          className="absolute bottom-4 left-1/2 -translate-x-1/2 bg-clay-700 text-clay-200 rounded-full px-3 py-1.5 text-xs flex items-center gap-1 shadow-lg hover:bg-clay-600 transition-colors z-10"
        >
          <ChevronDown className="h-3 w-3" />
          Latest
        </button>
      )}
    </div>
  );
}
