"use client";

import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Mail,
  PenLine,
} from "lucide-react";

/* ── Placeholder data ── */
const stats = {
  emailsGenerated: 47,
  linkedInNotes: 23,
  sequencesCreated: 5,
};

export default function OutboundPage() {
  return (
    <div className="flex flex-col h-full">
      <Header
        title="Outbound"
        breadcrumbs={[{ label: "Home" }]}
      />

      <div className="flex-1 overflow-auto p-4 md:p-6 space-y-6 pb-20 md:pb-6">
        {/* ── Gradient header section ── */}
        <div className="rounded-xl bg-gradient-to-r from-kiln-teal/5 to-transparent p-6 border border-clay-800">
          <h1 className="text-2xl font-bold text-clay-100">
            Good {getGreeting()}, here&apos;s your outbound pulse.
          </h1>
          <p className="text-sm text-clay-500 mt-1">
            Write emails and create sequences — output goes straight to Clay.
          </p>
        </div>

        {/* ── Stat cards ── */}
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          <StatCard
            icon={<Mail className="h-5 w-5 text-kiln-teal" />}
            label="Emails Generated"
            value={stats.emailsGenerated}
          />
          <StatCard
            icon={<PenLine className="h-5 w-5 text-kiln-teal" />}
            label="LinkedIn Notes"
            value={stats.linkedInNotes}
          />
          <StatCard
            icon={<Mail className="h-5 w-5 text-kiln-teal" />}
            label="Sequences Created"
            value={stats.sequencesCreated}
          />
        </div>

        {/* ── Quick actions ── */}
        <div className="flex flex-wrap gap-3">
          <Button asChild className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold">
            <Link href="/run?skill=email-gen">
              <Mail className="h-4 w-4 mr-1.5" />
              Write an Email
            </Link>
          </Button>
          <Button asChild className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold">
            <Link href="/run?skill=sequence-writer">
              <PenLine className="h-4 w-4 mr-1.5" />
              Create Sequence
            </Link>
          </Button>
        </div>
      </div>
    </div>
  );
}

/* ── Stat card component ── */
function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: number;
}) {
  return (
    <Card className="border-clay-800 shadow-sm">
      <CardContent className="pt-0">
        <div className="flex items-center gap-3">
          <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-kiln-teal/10">
            {icon}
          </div>
          <div>
            <p className="text-xs text-clay-500 uppercase tracking-wider">{label}</p>
            <p className="text-3xl font-bold text-clay-100 font-[family-name:var(--font-mono)]">
              {value}
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

/* ── Greeting helper ── */
function getGreeting(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "morning";
  if (hour < 17) return "afternoon";
  return "evening";
}
