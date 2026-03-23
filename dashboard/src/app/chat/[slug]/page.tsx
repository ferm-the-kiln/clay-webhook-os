"use client";

import { Suspense, useState } from "react";
import { useParams, useSearchParams } from "next/navigation";
import { useChat } from "@/hooks/use-chat";
import { ActivityPanel } from "@/components/chat/activity-panel";
import { ChatThread } from "@/components/chat/chat-thread";
import { ChatInput } from "@/components/chat/chat-input";
import { SessionList } from "@/components/chat/session-list";
import { Button } from "@/components/ui/button";
import { PanelLeft, ShieldAlert } from "lucide-react";

export default function ClientChatPageWrapper() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col h-screen bg-clay-950">
          <div className="flex-1 flex items-center justify-center text-clay-300">
            Loading...
          </div>
        </div>
      }
    >
      <ClientChatPage />
    </Suspense>
  );
}

function ClientChatPage() {
  const params = useParams();
  const searchParams = useSearchParams();
  const slug = params.slug as string;
  const token = searchParams.get("token") || "";
  const functionId = searchParams.get("fn") || "";

  const [sessionListCollapsed, setSessionListCollapsed] = useState(false);

  // Show error if no token provided
  if (!token) {
    return (
      <div className="flex flex-col h-screen bg-clay-950 items-center justify-center gap-4">
        <ShieldAlert className="h-12 w-12 text-kiln-coral" />
        <h1 className="text-xl font-semibold text-clay-100">Access Denied</h1>
        <p className="text-sm text-clay-300">
          No access token provided. Please use the link shared with you.
        </p>
      </div>
    );
  }

  const chat = useChat({
    clientSlug: slug,
    shareToken: token,
    clientFunctionId: functionId || undefined,
  });

  return (
    <div className="flex flex-col h-screen bg-clay-950">
      {/* Minimal header for client view */}
      <div className="h-14 border-b border-clay-600 flex items-center px-6">
        <h1 className="text-xl font-semibold text-clay-100">Chat</h1>
      </div>

      <div className="flex-1 overflow-hidden flex relative">
        {/* Session list panel */}
        <SessionList
          sessions={chat.sessions}
          activeSessionId={chat.activeSession?.id ?? null}
          onSelect={(id) => chat.loadSession(id)}
          onCreate={() => {
            if (functionId) {
              chat.createSession(functionId);
            }
            // No function picker in client mode -- if no fn param, new session creation is not available
          }}
          collapsed={sessionListCollapsed}
          onToggleCollapse={() => setSessionListCollapsed((v) => !v)}
        />

        {sessionListCollapsed && (
          <Button
            variant="ghost"
            size="icon"
            className="absolute left-0 top-1/2 -translate-y-1/2 z-10 h-8 w-8 text-clay-300 hover:text-clay-100 hover:bg-clay-700"
            onClick={() => setSessionListCollapsed(false)}
            aria-label="Show session list"
          >
            <PanelLeft className="h-4 w-4" />
          </Button>
        )}

        {/* Chat thread area -- no FunctionPicker in client mode */}
        <div className="flex-1 flex flex-col min-w-0">
          <ChatThread
            messages={chat.messages}
            streaming={chat.streaming}
          />

          <ChatInput
            value={chat.inputValue}
            onChange={chat.setInputValue}
            onSend={chat.sendMessage}
            disabled={chat.streaming || !chat.activeSession}
            selectedFunction={chat.selectedFunction}
          />
        </div>

        {/* Activity panel */}
        <ActivityPanel
          executionState={chat.executionState}
          rowStatuses={chat.rowStatuses}
          streamProgress={chat.streamProgress}
          completedResults={chat.completedResults}
          streaming={chat.streaming}
          selectedFunction={chat.selectedFunction}
        />
      </div>
    </div>
  );
}
