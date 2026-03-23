"use client";

import { useRef, useEffect, useState, useCallback } from "react";
import type { ChannelMessage } from "@/lib/types";
import { ChatMessage } from "./chat-message";
import { EmptyState } from "@/components/ui/empty-state";
import { MessageSquare, ChevronDown } from "lucide-react";

interface ChatThreadProps {
  messages: ChannelMessage[];
  streaming: boolean;
}

export function ChatThread({ messages, streaming }: ChatThreadProps) {
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

  // Auto-scroll when messages change
  useEffect(() => {
    if (isNearBottom()) {
      sentinelRef.current?.scrollIntoView({ behavior: "smooth" });
    }
  }, [messages, isNearBottom]);

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
