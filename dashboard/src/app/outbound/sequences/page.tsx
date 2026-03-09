"use client";

import { useState } from "react";
import { Header } from "@/components/layout/header";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Mail, Clock, MessageCircle, Plus, ArrowDown } from "lucide-react";

interface SequenceStep {
  id: number;
  type: "email" | "wait" | "linkedin";
  label: string;
  description: string;
  waitDays?: number;
}

const PLACEHOLDER_STEPS: SequenceStep[] = [
  {
    id: 1,
    type: "email",
    label: "Initial Email",
    description: "Personalized cold outreach using email-gen skill",
  },
  {
    id: 2,
    type: "wait",
    label: "Wait 2 Days",
    description: "Pause before next touch",
    waitDays: 2,
  },
  {
    id: 3,
    type: "linkedin",
    label: "LinkedIn Note",
    description: "Connection request with personalized note via linkedin-note skill",
  },
  {
    id: 4,
    type: "wait",
    label: "Wait 3 Days",
    description: "Pause before follow-up",
    waitDays: 3,
  },
  {
    id: 5,
    type: "email",
    label: "Follow-up Email",
    description: "Value-add follow-up using follow-up skill",
  },
];

const STEP_CONFIG: Record<
  SequenceStep["type"],
  { icon: typeof Mail; accentColor: string; badgeBg: string; badgeText: string }
> = {
  email: {
    icon: Mail,
    accentColor: "border-l-kiln-teal",
    badgeBg: "bg-kiln-teal/10",
    badgeText: "text-kiln-teal",
  },
  wait: {
    icon: Clock,
    accentColor: "border-l-clay-600",
    badgeBg: "bg-clay-600/10",
    badgeText: "text-clay-600",
  },
  linkedin: {
    icon: MessageCircle,
    accentColor: "border-l-kiln-teal",
    badgeBg: "bg-kiln-teal/10",
    badgeText: "text-kiln-teal",
  },
};

function StepCard({ step, index }: { step: SequenceStep; index: number }) {
  const config = STEP_CONFIG[step.type];
  const Icon = config.icon;

  return (
    <div className="border border-clay-800 bg-white rounded-xl p-4 shadow-sm border-l-4 transition-all hover:shadow-md">
      <div className={`-ml-4 pl-4 border-l-4 ${config.accentColor} rounded-l-none`}>
        <div className="flex items-start gap-3">
          <div className={`flex-shrink-0 flex items-center justify-center w-8 h-8 rounded-lg ${config.badgeBg}`}>
            <Icon className={`h-4 w-4 ${config.badgeText}`} />
          </div>
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-1">
              <span className="text-xs font-medium text-clay-500">
                Step {index + 1}
              </span>
              <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-[10px] font-medium uppercase tracking-wide ${config.badgeBg} ${config.badgeText}`}>
                {step.type}
              </span>
            </div>
            <h3 className="text-sm font-semibold text-clay-100">{step.label}</h3>
            <p className="text-xs text-clay-500 mt-0.5">{step.description}</p>
          </div>
        </div>
      </div>
    </div>
  );
}

function TimelineConnector() {
  return (
    <div className="flex flex-col items-center">
      <div className="w-0.5 h-8 bg-clay-700 mx-auto" />
      <ArrowDown className="h-3 w-3 text-clay-600 -mt-1" />
    </div>
  );
}

export default function SequencesPage() {
  const [sequences] = useState([
    {
      id: "seq-1",
      name: "Outbound Sequence v1",
      steps: PLACEHOLDER_STEPS,
    },
  ]);

  const hasSequences = sequences.length > 0;

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Sequences"
        breadcrumbs={[
          { label: "Outbound", href: "/outbound" },
          { label: "Sequences" },
        ]}
      />

      <div className="flex-1 overflow-y-auto px-4 md:px-6 py-6 pb-20 md:pb-6">
        {/* Top bar */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h3 className="text-lg font-semibold text-clay-100">
              Sequence Builder
            </h3>
            <p className="text-sm text-clay-500 mt-0.5">
              Design multi-touch outreach sequences with automated timing
            </p>
          </div>
          <Button className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold">
            <Plus className="h-4 w-4 mr-1.5" />
            New Sequence
          </Button>
        </div>

        {hasSequences ? (
          <div className="space-y-8">
            {sequences.map((seq) => (
              <Card
                key={seq.id}
                className="border-clay-800 bg-white shadow-sm rounded-xl"
              >
                <CardContent className="pt-6">
                  <div className="flex items-center justify-between mb-6">
                    <div>
                      <h4 className="text-base font-semibold text-clay-100">
                        {seq.name}
                      </h4>
                      <p className="text-xs text-clay-500 mt-0.5">
                        {seq.steps.length} steps &middot;{" "}
                        {seq.steps
                          .filter((s) => s.type === "wait")
                          .reduce((acc, s) => acc + (s.waitDays || 0), 0)}{" "}
                        days total duration
                      </p>
                    </div>
                  </div>

                  {/* Timeline */}
                  <div className="max-w-lg mx-auto">
                    {seq.steps.map((step, i) => (
                      <div key={step.id}>
                        <StepCard step={step} index={i} />
                        {i < seq.steps.length - 1 && <TimelineConnector />}
                      </div>
                    ))}
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        ) : (
          /* Empty state */
          <div className="flex flex-col items-center justify-center py-24 text-center">
            <div className="flex items-center justify-center w-14 h-14 rounded-2xl bg-clay-800/50 mb-4">
              <Mail className="h-7 w-7 text-clay-500" />
            </div>
            <h3 className="text-base font-semibold text-clay-200 mb-1">
              No sequences yet
            </h3>
            <p className="text-sm text-clay-500 max-w-md">
              Build multi-touch sequences combining email, LinkedIn, and
              follow-up skills
            </p>
            <Button className="mt-6 bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold">
              <Plus className="h-4 w-4 mr-1.5" />
              New Sequence
            </Button>
          </div>
        )}
      </div>
    </div>
  );
}
