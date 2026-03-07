"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { Header } from "@/components/layout/header";
import { OnboardingChecklist } from "@/components/getting-started/onboarding-checklist";
import { fetchSkills, fetchClients, fetchHealth } from "@/lib/api";
import type { HealthResponse, ClientSummary } from "@/lib/types";

export default function GettingStartedPage() {
  const [skills, setSkills] = useState<string[]>([]);
  const [clients, setClients] = useState<ClientSummary[]>([]);
  const [health, setHealth] = useState<HealthResponse | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    Promise.allSettled([
      fetchSkills().then((r) => setSkills(r.skills)),
      fetchClients().then((r) => setClients(r.clients)),
      fetchHealth().then((r) => setHealth(r)),
    ]).finally(() => setLoading(false));
  }, []);

  return (
    <div className="flex flex-col h-full">
      <Header title="Getting Started" />
      <div className="flex-1 overflow-auto p-4 md:p-6 pb-20 md:pb-6">
        <div className="max-w-2xl mx-auto space-y-8">
          {/* Welcome */}
          <div className="text-center space-y-3 py-6">
            <h1 className="text-3xl font-bold text-clay-100 font-[family-name:var(--font-sans)]">
              Welcome to The Kiln
            </h1>
            <p className="text-clay-400 text-lg max-w-lg mx-auto">
              Your AI-powered outbound engine is ready. We've configured your
              skills, loaded your context, and connected your integrations.
            </p>
          </div>

          <OnboardingChecklist
            skills={skills}
            clients={clients}
            health={health}
            loading={loading}
          />
        </div>
      </div>
    </div>
  );
}
