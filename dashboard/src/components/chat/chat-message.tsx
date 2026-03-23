"use client";

import { useState, useCallback } from "react";
import type { ChannelMessage } from "@/lib/types";
import { cn, formatRelativeTime } from "@/lib/utils";
import { ResultCard } from "./result-card";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Check } from "lucide-react";

function CopyableCodeBlock({ children }: { children: React.ReactNode }) {
  const [copied, setCopied] = useState(false);

  const handleCopy = useCallback(() => {
    const text = extractText(children);
    navigator.clipboard.writeText(text).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }).catch(() => {/* silent */});
  }, [children]);

  return (
    <div className="relative group">
      <pre className="bg-clay-900 border border-clay-700 rounded-md overflow-x-auto p-3 text-sm">
        {children}
      </pre>
      <button
        onClick={handleCopy}
        className="absolute top-2 right-2 opacity-0 group-hover:opacity-100 transition-opacity bg-clay-700 hover:bg-clay-600 text-clay-200 hover:text-clay-100 rounded p-1"
        aria-label="Copy code"
      >
        {copied ? <Check className="h-3.5 w-3.5 text-kiln-teal" /> : <Copy className="h-3.5 w-3.5" />}
      </button>
    </div>
  );
}

function extractText(node: React.ReactNode): string {
  if (typeof node === "string") return node;
  if (typeof node === "number") return String(node);
  if (Array.isArray(node)) return node.map(extractText).join("");
  if (node && typeof node === "object") {
    const obj = node as unknown as Record<string, unknown>;
    if ("props" in obj) {
      const props = obj.props as Record<string, unknown> | undefined;
      if (props && "children" in props) {
        return extractText(props.children as React.ReactNode);
      }
    }
  }
  return "";
}

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
                <div className="text-sm prose prose-invert prose-sm max-w-none prose-p:my-1 prose-headings:my-2 prose-li:my-0.5 prose-pre:p-0 prose-pre:bg-transparent prose-pre:border-0 prose-code:text-kiln-teal">
                  <ReactMarkdown
                    remarkPlugins={[remarkGfm]}
                    components={{ pre: ({ children }) => <CopyableCodeBlock>{children}</CopyableCodeBlock> }}
                  >
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
            <div className="flex items-center gap-1 py-0.5">
              <span
                className="bg-kiln-teal rounded-full h-2 w-2 inline-block"
                style={{ animation: "typing-bounce 1.2s ease-in-out infinite", animationDelay: "0ms" }}
              />
              <span
                className="bg-kiln-teal rounded-full h-2 w-2 inline-block"
                style={{ animation: "typing-bounce 1.2s ease-in-out infinite", animationDelay: "200ms" }}
              />
              <span
                className="bg-kiln-teal rounded-full h-2 w-2 inline-block"
                style={{ animation: "typing-bounce 1.2s ease-in-out infinite", animationDelay: "400ms" }}
              />
              <style>{`
                @keyframes typing-bounce {
                  0%, 60%, 100% { transform: translateY(0); opacity: 0.5; }
                  30% { transform: translateY(-4px); opacity: 1; }
                }
              `}</style>
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
