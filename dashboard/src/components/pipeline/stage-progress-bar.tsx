"use client";

import Link from "next/link";
import { cn } from "@/lib/utils";
import {
  Upload,
  Search,
  Target,
  Mail,
  PenLine,
  Send,
  CheckCircle2,
} from "lucide-react";
import type { LucideIcon } from "lucide-react";
import {
  Tooltip,
  TooltipContent,
  TooltipProvider,
  TooltipTrigger,
} from "@/components/ui/tooltip";

interface Stage {
  id: string;
  label: string;
  icon: LucideIcon;
  href: string;
  description: string;
}

const PIPELINE_STAGES: Stage[] = [
  { id: "import", label: "Import", icon: Upload, href: "/pipeline", description: "Import contacts from CSV" },
  { id: "find-email", label: "Find Email", icon: Mail, href: "/pipeline/enrich", description: "Find email addresses using Findymail" },
  { id: "research", label: "Research", icon: Search, href: "/pipeline/research", description: "Enrich with company and people research" },
  { id: "classify", label: "Score", icon: Target, href: "/pipeline/score", description: "Normalize seniority, industry, and department" },
  { id: "email-gen", label: "Generate", icon: PenLine, href: "/pipeline/email-lab", description: "Generate personalized email content" },
  { id: "send", label: "Send", icon: Send, href: "/pipeline/send", description: "Push to destinations and CRM" },
];

interface StageProgressBarProps {
  completedStages: string[];
  currentStage?: string;
  className?: string;
}

export function StageProgressBar({
  completedStages,
  currentStage,
  className,
}: StageProgressBarProps) {
  return (
    <TooltipProvider delayDuration={300}>
      <div className={cn("flex items-center gap-1", className)}>
        {PIPELINE_STAGES.map((stage, i) => {
          const completed = completedStages.includes(stage.id);
          const isRunning = currentStage === stage.id;
          const Icon = completed ? CheckCircle2 : stage.icon;

          return (
            <div key={stage.id} className="flex items-center">
              {i > 0 && (
                <div
                  className={cn(
                    "w-6 h-px mx-0.5",
                    completed ? "bg-kiln-teal" : "bg-clay-600"
                  )}
                />
              )}
              <Tooltip>
                <TooltipTrigger asChild>
                  <Link href={stage.href}>
                    <div
                      className={cn(
                        "flex items-center gap-1.5 px-2.5 py-1.5 rounded-md text-xs font-medium transition-colors",
                        completed
                          ? "bg-kiln-teal/10 text-kiln-teal border border-kiln-teal/20"
                          : "bg-clay-700/50 text-clay-300 border border-clay-600 hover:bg-clay-700 hover:text-clay-200",
                        isRunning && "animate-pulse ring-2 ring-kiln-teal/50"
                      )}
                    >
                      <Icon className="h-3.5 w-3.5" />
                      <span className="hidden sm:inline">{stage.label}</span>
                    </div>
                  </Link>
                </TooltipTrigger>
                <TooltipContent
                  side="bottom"
                  className="bg-clay-800 border-clay-700 text-clay-200 text-xs"
                >
                  {stage.description}
                </TooltipContent>
              </Tooltip>
            </div>
          );
        })}
      </div>
    </TooltipProvider>
  );
}
