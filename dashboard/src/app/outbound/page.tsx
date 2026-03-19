"use client";

import { useState, Suspense } from "react";
import { Header } from "@/components/layout/header";
import { EmailLabContent } from "@/components/email-lab/email-lab-content";
import { SequenceLabContent } from "@/components/sequence-lab/sequence-lab-content";
import { cn } from "@/lib/utils";
import { Mail, ListOrdered, Loader2 } from "lucide-react";

type OutboundTab = "email-lab" | "sequence-lab";

export default function OutboundPage() {
  const [activeTab, setActiveTab] = useState<OutboundTab>("email-lab");

  return (
    <div className="flex flex-col h-full">
      <Header title="Outbound" />

      {/* Tab bar */}
      <div className="border-b border-clay-600 px-4 md:px-6">
        <div className="flex items-center gap-1">
          <button
            onClick={() => setActiveTab("email-lab")}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px",
              activeTab === "email-lab"
                ? "border-kiln-teal text-kiln-teal"
                : "border-transparent text-clay-300 hover:text-clay-100 hover:border-clay-500"
            )}
          >
            <Mail className="h-4 w-4" />
            Email Lab
          </button>
          <button
            onClick={() => setActiveTab("sequence-lab")}
            className={cn(
              "flex items-center gap-2 px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px",
              activeTab === "sequence-lab"
                ? "border-kiln-teal text-kiln-teal"
                : "border-transparent text-clay-300 hover:text-clay-100 hover:border-clay-500"
            )}
          >
            <ListOrdered className="h-4 w-4" />
            Sequence Lab
          </button>
        </div>
      </div>

      {/* Tab content */}
      <Suspense
        fallback={
          <div className="flex-1 flex items-center justify-center text-clay-300">
            <Loader2 className="h-6 w-6 animate-spin" />
          </div>
        }
      >
        {activeTab === "email-lab" && <EmailLabContent />}
        {activeTab === "sequence-lab" && <SequenceLabContent />}
      </Suspense>
    </div>
  );
}
