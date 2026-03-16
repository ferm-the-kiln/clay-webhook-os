"use client";

import { Suspense } from "react";
import { Header } from "@/components/layout/header";
import { SequenceLabContent } from "@/components/sequence-lab/sequence-lab-content";
import { Loader2 } from "lucide-react";

export default function PipelineSequenceLabPage() {
  return (
    <div className="flex flex-col h-full">
      <Header
        title="Sequence Lab"
        breadcrumbs={[
          { label: "Pipeline", href: "/pipeline" },
          { label: "Sequence Lab" },
        ]}
      />

      <Suspense
        fallback={
          <div className="flex-1 flex items-center justify-center text-clay-300">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        }
      >
        <SequenceLabContent />
      </Suspense>
    </div>
  );
}
