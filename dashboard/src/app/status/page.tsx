"use client";

import { Header } from "@/components/layout/header";
import { SystemHealth } from "@/components/status/system-health";
import { ErrorBoundary } from "@/components/ui/error-boundary";

export default function StatusPage() {
  return (
    <div className="flex flex-col h-full">
      <Header title="System Status" />
      <div className="flex-1 overflow-auto p-4 md:p-6 pb-20 md:pb-6">
        <ErrorBoundary>
          <SystemHealth />
        </ErrorBoundary>
      </div>
    </div>
  );
}
