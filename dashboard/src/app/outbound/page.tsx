"use client";

import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Mail,
  PenLine,
  CheckSquare,
  Rocket,
  ArrowRight,
  Users,
} from "lucide-react";

/* ── Placeholder data ── */
const stats = {
  emailsGenerated: 47,
  linkedInNotes: 23,
  sequencesCreated: 5,
};

const reviewQueue = {
  pending: 12,
  items: [
    { id: "1", contact: "Sarah Chen", company: "Stripe", skill: "email-gen", time: "2m ago" },
    { id: "2", contact: "Marcus Johnson", company: "Datadog", skill: "linkedin-note", time: "8m ago" },
    { id: "3", contact: "Priya Patel", company: "Snowflake", skill: "sequence-writer", time: "14m ago" },
  ],
};

const activeCampaigns = [
  { id: "1", name: "Q1 Enterprise Outbound", progress: 68, total: 250, sent: 170, status: "active" as const },
  { id: "2", name: "Series B Startup Push", progress: 34, total: 120, sent: 41, status: "active" as const },
  { id: "3", name: "Mid-Market Re-engage", progress: 12, total: 80, sent: 10, status: "active" as const },
];

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
            Today&apos;s output across all active campaigns and one-off runs.
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
            icon={<Rocket className="h-5 w-5 text-kiln-teal" />}
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
            <Link href="/outbound/sequences">
              <PenLine className="h-4 w-4 mr-1.5" />
              Create Sequence
            </Link>
          </Button>
          <Button asChild className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold">
            <Link href="/outbound/review">
              <CheckSquare className="h-4 w-4 mr-1.5" />
              Review Pending
            </Link>
          </Button>
        </div>

        {/* ── Two-column layout: Review Queue + Campaigns ── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* ── Review queue preview ── */}
          <Card className="border-clay-800 bg-white shadow-sm">
            <CardContent className="pt-0">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-clay-100">Review Queue</h3>
                <span className="inline-flex items-center gap-1.5 rounded-full bg-kiln-teal/10 px-2.5 py-0.5 text-xs font-medium text-kiln-teal">
                  {reviewQueue.pending} pending
                </span>
              </div>

              <div className="space-y-3">
                {reviewQueue.items.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between rounded-lg border border-clay-800 bg-clay-950/50 px-4 py-3"
                  >
                    <div className="flex items-center gap-3 min-w-0">
                      <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-kiln-teal/10">
                        <Users className="h-4 w-4 text-kiln-teal" />
                      </div>
                      <div className="min-w-0">
                        <p className="text-sm font-medium text-clay-200 truncate">
                          {item.contact}
                        </p>
                        <p className="text-xs text-clay-500">
                          {item.company} &middot; {item.skill}
                        </p>
                      </div>
                    </div>
                    <span className="text-xs text-clay-600 shrink-0 ml-2">{item.time}</span>
                  </div>
                ))}
              </div>

              <Link
                href="/outbound/review"
                className="flex items-center gap-1 text-sm text-kiln-teal hover:text-kiln-teal-light font-medium mt-4 transition-colors"
              >
                View all pending
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </CardContent>
          </Card>

          {/* ── Active campaigns ── */}
          <Card className="border-clay-800 bg-white shadow-sm">
            <CardContent className="pt-0">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-clay-100">Active Campaigns</h3>
                <span className="text-xs text-clay-500">
                  {activeCampaigns.length} running
                </span>
              </div>

              <div className="space-y-4">
                {activeCampaigns.map((campaign) => (
                  <div key={campaign.id} className="space-y-2">
                    <div className="flex items-center justify-between">
                      <p className="text-sm font-medium text-clay-200">{campaign.name}</p>
                      <p className="text-xs text-clay-500">
                        {campaign.sent}/{campaign.total}
                      </p>
                    </div>
                    <div className="h-2 rounded-full bg-clay-800 overflow-hidden">
                      <div
                        className="h-full rounded-full bg-kiln-teal transition-all duration-500"
                        style={{ width: `${campaign.progress}%` }}
                      />
                    </div>
                    <p className="text-xs text-clay-600">{campaign.progress}% complete</p>
                  </div>
                ))}
              </div>

              <Link
                href="/outbound/campaigns"
                className="flex items-center gap-1 text-sm text-kiln-teal hover:text-kiln-teal-light font-medium mt-4 transition-colors"
              >
                Manage campaigns
                <ArrowRight className="h-3.5 w-3.5" />
              </Link>
            </CardContent>
          </Card>
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
    <Card className="border-clay-800 bg-white shadow-sm">
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
