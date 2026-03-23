"use client";

import type { ChannelMessage } from "@/lib/types";
import { cn, formatRelativeTime } from "@/lib/utils";
import { ResultCard } from "./result-card";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

interface ChatMessageProps {
  message: ChannelMessage;
  isStreaming?: boolean;
}

export function ChatMessage({ message, isStreaming }: ChatMessageProps) {
  const isUser = message.role === "user";
  const isError =
    message.content.startsWith("Processing failed") ||
    message.content.startsWith("Connection lost") ||
    message.content.startsWith("No results returned") ||
    message.content.startsWith("Something went wrong") ||
    message.content.startsWith("Free chat unavailable");
  const hasResults =
    message.results && message.results.length > 0;
  const isFreeChatReply = message.mode === "free_chat" && message.role === "assistant";

  return (
    <div
      className={
        isUser ? "flex justify-end" : "flex justify-start"
      }
    >
      <div className="max-w-[80%]">
        <div
          className={
            isUser
              ? "bg-clay-700 text-clay-100 rounded-2xl rounded-br-md px-4 py-2.5"
              : "bg-clay-850 text-clay-100 border border-clay-700 rounded-2xl rounded-bl-md px-4 py-2.5"
          }
        >
          {/* Message content */}
          {message.content && (
            <>
              {isFreeChatReply && !isError ? (
                <div className="text-sm prose prose-invert prose-sm max-w-none prose-p:my-1 prose-headings:my-2 prose-li:my-0.5 prose-pre:bg-clay-900 prose-pre:border prose-pre:border-clay-700 prose-code:text-kiln-teal">
                  <ReactMarkdown remarkPlugins={[remarkGfm]}>
                    {message.content}
                  </ReactMarkdown>
                  {isStreaming && !hasResults && (
                    <span className="animate-pulse bg-kiln-teal rounded-full h-2 w-2 inline-block ml-1 align-middle" />
                  )}
                </div>
              ) : (
                <p
                  className={cn(
                    "text-sm",
                    message.content.startsWith("Processing failed") &&
                      "text-kiln-coral",
                    message.content.startsWith("Connection lost") &&
                      "text-kiln-coral",
                    message.content.startsWith("Something went wrong") &&
                      "text-kiln-coral",
                    message.content.startsWith("Free chat unavailable") &&
                      "text-kiln-coral",
                    message.content.startsWith("No results returned") &&
                      "text-clay-200 italic",
                    !isError && "whitespace-pre-wrap"
                  )}
                >
                  {message.content}
                  {/* Streaming pulse indicator */}
                  {isStreaming && !hasResults && !isError && (
                    <span className="animate-pulse bg-kiln-teal rounded-full h-2 w-2 inline-block ml-2 align-middle" />
                  )}
                </p>
              )}
            </>
          )}

          {/* Empty streaming state (free chat, waiting for first chunk) */}
          {!message.content && isStreaming && isFreeChatReply && (
            <div className="flex items-center gap-2">
              <span className="animate-pulse bg-kiln-teal rounded-full h-2 w-2 inline-block" />
              <span className="text-sm text-clay-300">Thinking...</span>
            </div>
          )}

          {/* Structured results */}
          {hasResults && (
            <ResultCard results={message.results!} />
          )}
        </div>

        {/* Timestamp */}
        <div
          className={
            isUser
              ? "text-[11px] text-clay-200 font-mono tabular-nums mt-1 text-right"
              : "text-[11px] text-clay-200 font-mono tabular-nums mt-1"
          }
        >
          {formatRelativeTime(message.timestamp)}
        </div>
      </div>
    </div>
  );
}
