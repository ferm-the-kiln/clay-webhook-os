"use client";

import { Header } from "@/components/layout/header";
import { WorkbenchPage } from "@/components/workbench/workbench-page";

export default function ProspectPage() {
  return (
    <div className="flex flex-col h-full">
      <Header
        title="Prospecting Workbench"
        breadcrumbs={[{ label: "Prospect" }]}
      />
      <WorkbenchPage />
    </div>
  );
}
