"use client";

import Link from "next/link";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  CheckCircle,
  Circle,
  Sparkles,
  FlaskConical,
  Link2,
  LayoutDashboard,
  ArrowRight,
  Copy,
  ExternalLink,
} from "lucide-react";
import { toast } from "sonner";
import type { HealthResponse, ClientSummary } from "@/lib/types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://clay.nomynoms.com";

interface Props {
  skills: string[];
  clients: ClientSummary[];
  health: HealthResponse | null;
  loading: boolean;
}

function StepCard({
  step,
  title,
  done,
  children,
}: {
  step: number;
  title: string;
  done: boolean;
  children: React.ReactNode;
}) {
  return (
    <Card className="border-clay-800 bg-white shadow-sm overflow-hidden">
      <CardContent className="p-0">
        <div className="flex items-start gap-4 p-5">
          <div className="shrink-0 pt-0.5">
            {done ? (
              <CheckCircle className="h-6 w-6 text-kiln-teal" />
            ) : (
              <div className="relative">
                <Circle className="h-6 w-6 text-clay-600" />
                <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-clay-500">
                  {step}
                </span>
              </div>
            )}
          </div>
          <div className="flex-1 min-w-0">
            <h3 className="text-base font-semibold text-clay-100 font-[family-name:var(--font-sans)] mb-2">
              {title}
            </h3>
            {children}
          </div>
        </div>
      </CardContent>
    </Card>
  );
}

export function OnboardingChecklist({ skills, clients, health, loading }: Props) {
  if (loading) {
    return (
      <div className="space-y-4">
        {Array.from({ length: 5 }).map((_, i) => (
          <Card key={i} className="border-clay-800 bg-white shadow-sm">
            <CardContent className="p-5">
              <Skeleton className="h-5 w-48 bg-clay-900 rounded mb-3" />
              <Skeleton className="h-4 w-full bg-clay-900 rounded" />
            </CardContent>
          </Card>
        ))}
      </div>
    );
  }

  const isConnected = health?.status === "ok";
  const hasSkills = skills.length > 0;
  const hasClients = clients.length > 0;

  return (
    <div className="space-y-4">
      {/* Step 1: Platform connected */}
      <StepCard step={1} title="Platform is connected" done={isConnected}>
        <p className="text-sm text-clay-400 mb-3">
          {isConnected
            ? `The Kiln engine is online with ${health?.workers_max ?? 0} workers available and ${health?.skills_loaded?.length ?? 0} skills loaded.`
            : "Waiting for the engine to come online..."}
        </p>
        {isConnected && (
          <Badge
            variant="outline"
            className="bg-kiln-teal/10 text-kiln-teal border-kiln-teal/30"
          >
            {health?.engine} — {health?.workers_max} workers
          </Badge>
        )}
      </StepCard>

      {/* Step 2: Skills ready */}
      <StepCard step={2} title="Your skills are ready" done={hasSkills}>
        <p className="text-sm text-clay-400 mb-3">
          {hasSkills
            ? `${skills.length} skills are configured and ready to use:`
            : "No skills loaded yet. Contact The Kiln team to configure your skills."}
        </p>
        {hasSkills && (
          <div className="flex flex-wrap gap-2">
            {skills.map((s) => (
              <Badge
                key={s}
                variant="outline"
                className="bg-clay-900/50 text-clay-300 border-clay-700"
              >
                <Sparkles className="h-3 w-3 mr-1 text-kiln-teal" />
                {s}
              </Badge>
            ))}
          </div>
        )}
      </StepCard>

      {/* Step 3: Try first skill */}
      <StepCard step={3} title="Try your first skill" done={false}>
        <p className="text-sm text-clay-400 mb-3">
          Head to the Playground to test a skill with sample data. See the AI output in real-time.
        </p>
        <div className="flex flex-wrap gap-2">
          {(hasSkills ? skills.slice(0, 3) : ["email-gen"]).map((s) => (
            <Button
              key={s}
              variant="outline"
              size="sm"
              asChild
              className="border-kiln-teal/30 text-kiln-teal hover:bg-kiln-teal/10"
            >
              <Link href={`/playground?skill=${s}`}>
                <FlaskConical className="h-3.5 w-3.5 mr-1.5" />
                Try {s}
              </Link>
            </Button>
          ))}
        </div>
      </StepCard>

      {/* Step 4: Clay integration */}
      <StepCard step={4} title="Set up Clay integration" done={false}>
        <p className="text-sm text-clay-400 mb-3">
          Connect Clay to The Kiln using an HTTP Action. Copy the settings below into your Clay table.
        </p>
        <div className="space-y-3 rounded-lg bg-clay-900/50 border border-clay-800 p-4">
          <div>
            <p className="text-xs text-clay-500 uppercase tracking-wider mb-1">
              Webhook URL
            </p>
            <div className="flex items-center gap-2">
              <code className="text-sm text-kiln-teal font-[family-name:var(--font-mono)] break-all">
                {API_URL}/webhook
              </code>
              <button
                onClick={() => {
                  navigator.clipboard.writeText(`${API_URL}/webhook`);
                  toast.success("Copied webhook URL");
                }}
                className="shrink-0 text-clay-500 hover:text-clay-300"
              >
                <Copy className="h-3.5 w-3.5" />
              </button>
            </div>
          </div>
          <div>
            <p className="text-xs text-clay-500 uppercase tracking-wider mb-1">
              Method
            </p>
            <code className="text-sm text-clay-300 font-[family-name:var(--font-mono)]">
              POST
            </code>
          </div>
          <div>
            <p className="text-xs text-clay-500 uppercase tracking-wider mb-1">
              Headers
            </p>
            <code className="text-sm text-clay-300 font-[family-name:var(--font-mono)] block">
              Content-Type: application/json
            </code>
            <code className="text-sm text-clay-300 font-[family-name:var(--font-mono)] block">
              X-API-Key: {"<your-api-key>"}
            </code>
          </div>
          <div>
            <p className="text-xs text-clay-500 uppercase tracking-wider mb-1">
              Body Template
            </p>
            <pre className="text-xs text-clay-300 font-[family-name:var(--font-mono)] bg-clay-950 rounded p-2 overflow-x-auto">
{`{
  "skill": "email-gen",
  "data": {
    "first_name": "{{First Name}}",
    "company_name": "{{Company}}",
    "title": "{{Title}}",
    "client_slug": "${hasClients ? clients[0].slug : "your-client"}"
  }
}`}
            </pre>
          </div>
          <div>
            <p className="text-xs text-clay-500 uppercase tracking-wider mb-1">
              Timeout
            </p>
            <code className="text-sm text-clay-300 font-[family-name:var(--font-mono)]">
              120 seconds
            </code>
          </div>
        </div>
      </StepCard>

      {/* Step 5: Explore dashboard */}
      <StepCard step={5} title="Explore your dashboard" done={false}>
        <p className="text-sm text-clay-400 mb-3">
          Your dashboard tracks every job, shows analytics, and lets you rate outputs to improve quality over time.
        </p>
        <div className="flex flex-wrap gap-2">
          <Button
            variant="outline"
            size="sm"
            asChild
            className="border-clay-700 text-clay-300 hover:bg-clay-800"
          >
            <Link href="/">
              <LayoutDashboard className="h-3.5 w-3.5 mr-1.5" />
              Dashboard
            </Link>
          </Button>
          <Button
            variant="outline"
            size="sm"
            asChild
            className="border-clay-700 text-clay-300 hover:bg-clay-800"
          >
            <Link href="/analytics">
              Analytics
              <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
            </Link>
          </Button>
          <Button
            variant="outline"
            size="sm"
            asChild
            className="border-clay-700 text-clay-300 hover:bg-clay-800"
          >
            <Link href="/batch">
              Batch Processing
              <ArrowRight className="h-3.5 w-3.5 ml-1.5" />
            </Link>
          </Button>
        </div>
      </StepCard>
    </div>
  );
}
