"use client";

import { Header } from "@/components/layout/header";
import { GitBranch } from "lucide-react";

export default function CrmSyncPage() {
  return (
    <div className="flex flex-col h-full">
      <Header
        title="CRM Sync"
        breadcrumbs={[
          { label: "Pipeline", href: "/pipeline" },
          { label: "CRM Sync" },
        ]}
      />

      <div className="flex flex-col gap-6 p-6 max-w-[1200px]">
        <div className="flex flex-col items-center justify-center py-24 text-clay-300 border border-dashed border-clay-600 rounded-lg">
          <GitBranch className="h-12 w-12 mb-4 text-clay-500" />
          <p className="text-lg font-medium mb-1">Coming Soon</p>
          <p className="text-sm">CRM integration and sync will be available here.</p>
        </div>
      </div>
    </div>
  );
}
