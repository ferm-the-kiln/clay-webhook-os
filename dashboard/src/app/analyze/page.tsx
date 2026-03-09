"use client";

import Link from "next/link";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  Radar,
  Brain,
  Search,
  Target,
  Library,
  ArrowRight,
  Users,
} from "lucide-react";

/* ── Placeholder data ── */

const funnelStats = [
  { label: "Accounts Researched", value: "1,247", icon: Search },
  { label: "Meetings Prepped", value: "384", icon: Brain },
  { label: "Active Plays", value: "12", icon: Target },
];

const recentResearch = [
  {
    id: "r1",
    company: "Snowflake",
    skill: "account-researcher",
    date: "2 hours ago",
    status: "complete" as const,
  },
  {
    id: "r2",
    company: "Databricks",
    skill: "meeting-prep",
    date: "4 hours ago",
    status: "complete" as const,
  },
  {
    id: "r3",
    company: "Confluent",
    skill: "multi-thread-mapper",
    date: "6 hours ago",
    status: "complete" as const,
  },
  {
    id: "r4",
    company: "HashiCorp",
    skill: "account-researcher",
    date: "Yesterday",
    status: "complete" as const,
  },
  {
    id: "r5",
    company: "CrowdStrike",
    skill: "meeting-prep",
    date: "Yesterday",
    status: "complete" as const,
  },
];

const activePlays = [
  {
    id: "p1",
    name: "Enterprise Expansion — Q1",
    accounts: 34,
    lastRun: "Today",
    pipeline: "outbound-email",
  },
  {
    id: "p2",
    name: "PLG Upsell Motion",
    accounts: 89,
    lastRun: "Today",
    pipeline: "linkedin-connect",
  },
  {
    id: "p3",
    name: "Competitive Displacement",
    accounts: 17,
    lastRun: "Yesterday",
    pipeline: "competitive-deal",
  },
  {
    id: "p4",
    name: "Meeting Prep — AEs",
    accounts: 52,
    lastRun: "2 days ago",
    pipeline: "meeting-prep-suite",
  },
];

const quickActions = [
  {
    label: "Research an Account",
    href: "/run?skill=account-researcher",
    icon: Search,
  },
  {
    label: "Prep for Meeting",
    href: "/run?skill=meeting-prep",
    icon: Brain,
  },
  {
    label: "Map Buying Committee",
    href: "/run?skill=multi-thread-mapper",
    icon: Users,
  },
];

const skillLabel: Record<string, string> = {
  "account-researcher": "Account Research",
  "meeting-prep": "Meeting Prep",
  "multi-thread-mapper": "Thread Mapper",
};

/* ── Page ── */

export default function AnalyzePage() {
  return (
    <div className="flex flex-col h-full">
      <Header
        title="Analyze"
        breadcrumbs={[{ label: "Home" }]}
      />

      <div className="flex-1 overflow-auto p-4 md:p-6 space-y-8 pb-20 md:pb-6">
        {/* ── Gradient hero section ── */}
        <div className="rounded-xl bg-gradient-to-r from-kiln-indigo/5 to-transparent border border-clay-800 p-6">
          <div className="flex items-center gap-3 mb-1">
            <Radar className="h-5 w-5 text-kiln-indigo" />
            <h3 className="text-lg font-semibold text-clay-100">
              Research Pipeline
            </h3>
          </div>
          <p className="text-sm text-clay-500 mb-6">
            Funnel overview across all strategic analysis skills.
          </p>

          {/* ── Funnel stat cards ── */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
            {funnelStats.map((stat) => (
              <Card
                key={stat.label}
                className="border-clay-800 bg-white shadow-sm rounded-xl"
              >
                <CardContent className="pt-5">
                  <div className="flex items-center gap-2 mb-2">
                    <stat.icon className="h-4 w-4 text-kiln-indigo" />
                    <span className="text-xs text-clay-500 uppercase tracking-wider">
                      {stat.label}
                    </span>
                  </div>
                  <span className="text-3xl font-bold text-clay-100 font-[family-name:var(--font-mono)]">
                    {stat.value}
                  </span>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>

        {/* ── Quick actions ── */}
        <div>
          <h3 className="text-lg font-semibold text-clay-100 mb-4">
            Quick Actions
          </h3>
          <div className="flex flex-wrap gap-3">
            {quickActions.map((action) => (
              <Link key={action.href} href={action.href}>
                <Button className="bg-kiln-indigo text-white hover:bg-kiln-indigo-light font-semibold">
                  <action.icon className="h-4 w-4 mr-2" />
                  {action.label}
                  <ArrowRight className="h-4 w-4 ml-2" />
                </Button>
              </Link>
            ))}
          </div>
        </div>

        {/* ── Two-column layout: Recent Research + Active Plays ── */}
        <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
          {/* Recent research results */}
          <div>
            <h3 className="text-lg font-semibold text-clay-100 mb-4">
              Recent Research
            </h3>
            <Card className="border-clay-800 bg-white shadow-sm rounded-xl">
              <CardContent className="pt-4 divide-y divide-clay-800">
                {recentResearch.map((item) => (
                  <div
                    key={item.id}
                    className="flex items-center justify-between py-3 first:pt-0 last:pb-0"
                  >
                    <div className="flex items-center gap-3">
                      <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-kiln-indigo/10">
                        <Library className="h-4 w-4 text-kiln-indigo" />
                      </div>
                      <div>
                        <p className="text-sm font-medium text-clay-100">
                          {item.company}
                        </p>
                        <p className="text-xs text-clay-500">
                          {skillLabel[item.skill] ?? item.skill}
                        </p>
                      </div>
                    </div>
                    <span className="text-xs text-clay-500">{item.date}</span>
                  </div>
                ))}
              </CardContent>
            </Card>
          </div>

          {/* Active plays */}
          <div>
            <h3 className="text-lg font-semibold text-clay-100 mb-4">
              Active Plays
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              {activePlays.map((play) => (
                <Card
                  key={play.id}
                  className="border-clay-800 bg-white shadow-sm rounded-xl"
                >
                  <CardContent className="pt-5">
                    <p className="text-sm font-medium text-clay-100 mb-2">
                      {play.name}
                    </p>
                    <div className="flex items-center justify-between">
                      <span className="text-xs text-clay-500">
                        {play.accounts} accounts
                      </span>
                      <span className="text-xs text-clay-500">
                        {play.lastRun}
                      </span>
                    </div>
                    <div className="mt-2">
                      <span className="inline-block rounded-md bg-kiln-indigo/10 px-2 py-0.5 text-[11px] font-medium text-kiln-indigo">
                        {play.pipeline}
                      </span>
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
