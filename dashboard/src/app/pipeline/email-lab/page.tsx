"use client";

import { Suspense } from "react";
import { Header } from "@/components/layout/header";
import { EmailLabContent } from "@/components/email-lab/email-lab-content";
import { Loader2 } from "lucide-react";

export default function PipelineEmailLabPage() {
  return (
    <div className="flex flex-col h-full">
      <Header
        title="Email Lab"
        breadcrumbs={[
          { label: "Pipeline", href: "/pipeline" },
          { label: "Email Lab" },
        ]}
      />

      <Suspense
        fallback={
          <div className="flex-1 flex items-center justify-center text-clay-300">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        }
      >
        <EmailLabContent />
      </Suspense>
    </div>
  );
}
