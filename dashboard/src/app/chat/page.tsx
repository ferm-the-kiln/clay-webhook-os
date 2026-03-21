"use client";

import { Suspense } from "react";
import { Header } from "@/components/layout/header";
import { EmptyState } from "@/components/ui/empty-state";
import { MessageSquare, Activity } from "lucide-react";

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
  return (
    <div className="flex flex-col h-full">
      <Header title="Chat" />
      <div className="flex-1 overflow-hidden flex">
        {/* Session list panel -- Plan 03 will populate */}
        {/* Chat thread area */}
        <div className="flex-1 flex flex-col min-w-0">
          {/* Function picker -- Plan 02 will mount here */}
          {/* Messages -- Plan 02 will mount here */}
          <div className="flex-1 flex items-center justify-center p-6">
            <EmptyState
              title="Start a conversation"
              description="Pick a function and paste your data to get started."
              icon={MessageSquare}
            />
          </div>
          {/* Chat input -- Plan 02 will mount here */}
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
