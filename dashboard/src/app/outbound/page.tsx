"use client";

import { Suspense } from "react";
import { Header } from "@/components/layout/header";
import { EmailLabContent } from "@/components/email-lab/email-lab-content";
import { SequenceLabContent } from "@/components/sequence-lab/sequence-lab-content";
import { CampaignWizardButton } from "@/components/campaign-wizard/campaign-wizard";
import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { Mail, ListOrdered, Loader2 } from "lucide-react";

export default function OutboundPage() {
  return (
    <div className="flex flex-col h-full">
      <Header title="Outbound" />

      <Tabs defaultValue="email-lab" className="flex flex-col flex-1">
        <div className="border-b border-clay-600 px-4 md:px-6 flex items-center justify-between">
          <TabsList variant="line">
            <TabsTrigger value="email-lab">
              <Mail className="h-4 w-4" />
              Email Lab
            </TabsTrigger>
            <TabsTrigger value="sequence-lab">
              <ListOrdered className="h-4 w-4" />
              Sequence Lab
            </TabsTrigger>
          </TabsList>
          <CampaignWizardButton />
        </div>

        <TabsContent value="email-lab" className="flex-1">
          <Suspense
            fallback={
              <div className="flex-1 flex items-center justify-center text-clay-300">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            }
          >
            <EmailLabContent />
          </Suspense>
        </TabsContent>

        <TabsContent value="sequence-lab" className="flex-1">
          <Suspense
            fallback={
              <div className="flex-1 flex items-center justify-center text-clay-300">
                <Loader2 className="h-6 w-6 animate-spin" />
              </div>
            }
          >
            <SequenceLabContent />
          </Suspense>
        </TabsContent>
      </Tabs>
    </div>
  );
}
