"use client";

import { Suspense, useState } from "react";
import { Header } from "@/components/layout/header";
import { EmptyState } from "@/components/ui/empty-state";
import { Button } from "@/components/ui/button";
import { Activity, PanelLeft } from "lucide-react";
import { useChat } from "@/hooks/use-chat";
import { ChatThread } from "@/components/chat/chat-thread";
import { ChatInput } from "@/components/chat/chat-input";
import { FunctionPicker } from "@/components/chat/function-picker";
import { SessionList } from "@/components/chat/session-list";
import { toast } from "sonner";

export default function ChatPageWrapper() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col h-full">
          <Header title="Chat" />
          <div className="flex-1 flex items-center justify-center text-clay-300">
            Loading...
          </div>
        </div>
      }
    >
      <ChatPage />
    </Suspense>
  );
}

function ChatPage() {
  const chat = useChat();
  const [sessionListCollapsed, setSessionListCollapsed] = useState(false);

  return (
    <div className="flex flex-col h-full">
      <Header title="Chat" />
      <div className="flex-1 overflow-hidden flex relative">
        {/* Session list panel */}
        <SessionList
          sessions={chat.sessions}
          activeSessionId={chat.activeSession?.id ?? null}
          onSelect={(id) => chat.loadSession(id)}
          onCreate={() => {
            if (chat.selectedFunction) {
              chat.createSession(chat.selectedFunction.id);
            } else {
              toast("Select a function first", {
                description: "Pick a function from the dropdown to start a new chat.",
              });
            }
          }}
          collapsed={sessionListCollapsed}
          onToggleCollapse={() => setSessionListCollapsed((v) => !v)}
        />

        {/* Expand button when session list is collapsed */}
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

        {/* Chat thread area */}
        <div className="flex-1 flex flex-col min-w-0">
          <FunctionPicker
            functions={chat.functions}
            functionsByFolder={chat.functionsByFolder}
            selectedFunction={chat.selectedFunction}
            onSelect={(func) => {
              chat.selectFunction(func);
              if (!chat.activeSession) {
                chat.createSession(func.id);
              }
            }}
            disabled={!!chat.activeSession}
          />

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

        {/* Activity panel placeholder -- Phase 3 fills this */}
        <div className="hidden lg:flex w-80 border-l border-clay-600 flex-col items-center justify-center p-6">
          <EmptyState
            title="Activity"
            description="Execution details will appear here when you run a function."
            icon={Activity}
          />
        </div>
      </div>
    </div>
  );
}
