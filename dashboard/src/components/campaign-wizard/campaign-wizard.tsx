"use client";

import { useState } from "react";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
  DialogFooter,
} from "@/components/ui/dialog";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  Rocket,
  ArrowRight,
  ArrowLeft,
  RotateCcw,
  Loader2,
  Sparkles,
  TrendingUp,
  Search,
  FolderOpen,
  Target,
  CheckCircle2,
  Plus,
  X,
  Trophy,
  XCircle,
} from "lucide-react";
import {
  useCampaignWizard,
  type CampaignStep,
  type DealEntry,
  type DealOutcome,
  type StepAnalysis,
} from "@/hooks/use-campaign-wizard";

/* ── Step metadata ─────────────────────────────────── */

const STEP_META: Record<
  CampaignStep,
  { label: string; icon: React.ReactNode; description: string }
> = {
  intro: {
    label: "Campaign Builder",
    icon: <Rocket className="h-4 w-4" />,
    description: "Build campaigns your prospects would pay to receive",
  },
  invert: {
    label: "Invert Your Deals",
    icon: <TrendingUp className="h-4 w-4" />,
    description: "Add your closed-won and closed-lost deals for pattern analysis",
  },
  pain: {
    label: "Find Discoverable Pain",
    icon: <Search className="h-4 w-4" />,
    description: "Unique data sources your competitors don't have",
  },
  context: {
    label: "Build Context",
    icon: <FolderOpen className="h-4 w-4" />,
    description: "Assemble everything the AI needs to think like your best rep",
  },
  plan: {
    label: "Plan the Play",
    icon: <Target className="h-4 w-4" />,
    description: "Strategy before execution — define your campaign angle",
  },
  review: {
    label: "Review & Score",
    icon: <CheckCircle2 className="h-4 w-4" />,
    description: "AI scores your campaign on 5 dimensions before launch",
  },
};

const STEPS_ORDER: CampaignStep[] = [
  "intro",
  "invert",
  "pain",
  "context",
  "plan",
  "review",
];

/* ── Shared components ─────────────────────────────── */

function AnalysisPanel({ analysis }: { analysis: StepAnalysis }) {
  if (analysis.loading) {
    return (
      <div className="mt-4 rounded-md border border-kiln-teal/30 bg-kiln-teal/5 p-4">
        <div className="flex items-center gap-2 text-kiln-teal text-sm">
          <Loader2 className="h-4 w-4 animate-spin" />
          Analyzing your data...
        </div>
      </div>
    );
  }
  if (analysis.error) {
    return (
      <div className="mt-4 rounded-md border border-red-500/30 bg-red-500/5 p-4">
        <p className="text-red-400 text-sm">{analysis.error}</p>
      </div>
    );
  }
  if (!analysis.content) return null;
  return (
    <div className="mt-4 rounded-md border border-kiln-teal/30 bg-kiln-teal/5 p-4">
      <div className="flex items-center gap-2 mb-3">
        <Sparkles className="h-3.5 w-3.5 text-kiln-teal" />
        <span className="text-xs font-medium text-kiln-teal tracking-wide uppercase">
          AI Analysis
        </span>
      </div>
      <div className="text-sm text-clay-200 whitespace-pre-wrap leading-relaxed">
        {analysis.content}
      </div>
    </div>
  );
}

function WizardField({
  label,
  value,
  onChange,
  placeholder,
  rows = 2,
}: {
  label: string;
  value: string;
  onChange: (val: string) => void;
  placeholder: string;
  rows?: number;
}) {
  return (
    <div className="space-y-1.5">
      <label className="text-xs font-medium text-clay-300 tracking-wide">
        {label}
      </label>
      <textarea
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        rows={rows}
        className="w-full rounded-md border border-clay-500 bg-clay-800 px-3 py-2 text-sm text-clay-100 placeholder:text-clay-400 focus:border-kiln-teal focus:outline-none focus:ring-1 focus:ring-kiln-teal/30 resize-none"
      />
    </div>
  );
}

function WizardInput({
  label,
  value,
  onChange,
  placeholder,
}: {
  label?: string;
  value: string;
  onChange: (val: string) => void;
  placeholder: string;
}) {
  return (
    <div className="space-y-1">
      {label && (
        <label className="text-xs font-medium text-clay-300 tracking-wide">
          {label}
        </label>
      )}
      <input
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="w-full rounded-md border border-clay-500 bg-clay-800 px-3 py-1.5 text-sm text-clay-100 placeholder:text-clay-400 focus:border-kiln-teal focus:outline-none focus:ring-1 focus:ring-kiln-teal/30"
      />
    </div>
  );
}

/* ── Step: Intro ───────────────────────────────────── */

function IntroStep() {
  return (
    <div className="space-y-4">
      <p className="text-sm text-clay-300 leading-relaxed">
        This wizard walks you through the{" "}
        <span className="text-clay-100 font-medium">Campaign Creation Framework</span>{" "}
        — five steps to build campaigns that deliver market intelligence, not
        pitches.
      </p>
      <div className="grid grid-cols-1 gap-2">
        {STEPS_ORDER.slice(1).map((s) => (
          <div
            key={s}
            className="flex items-start gap-3 rounded-md border border-clay-600 bg-clay-800/50 p-3"
          >
            <div className="mt-0.5 text-kiln-teal">{STEP_META[s].icon}</div>
            <div>
              <p className="text-sm font-medium text-clay-100">
                {STEP_META[s].label}
              </p>
              <p className="text-xs text-clay-400">{STEP_META[s].description}</p>
            </div>
          </div>
        ))}
      </div>
      <div className="rounded-md border border-kiln-teal/20 bg-kiln-teal/5 p-3">
        <p className="text-xs text-clay-300 leading-relaxed">
          <span className="text-kiln-teal font-medium">Permissionless Value Prop:</span>{" "}
          A message so valuable the prospect would pay to receive it. That's
          the bar. The AI will guide you toward it at every step.
        </p>
      </div>
    </div>
  );
}

/* ── Step: Invert Deals ────────────────────────────── */

function DealCard({
  deal,
  onUpdate,
  onRemove,
}: {
  deal: DealEntry;
  onUpdate: (updates: Partial<DealEntry>) => void;
  onRemove: () => void;
}) {
  const isWon = deal.outcome === "won";
  return (
    <div
      className={`rounded-md border p-3 space-y-2 ${
        isWon
          ? "border-emerald-500/30 bg-emerald-500/5"
          : "border-red-500/30 bg-red-500/5"
      }`}
    >
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          {isWon ? (
            <Trophy className="h-3.5 w-3.5 text-emerald-400" />
          ) : (
            <XCircle className="h-3.5 w-3.5 text-red-400" />
          )}
          <span
            className={`text-xs font-medium tracking-wide uppercase ${
              isWon ? "text-emerald-400" : "text-red-400"
            }`}
          >
            {isWon ? "Won" : "Lost"}
          </span>
        </div>
        <button
          onClick={onRemove}
          className="text-clay-500 hover:text-clay-300 transition-colors"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      </div>
      <div className="grid grid-cols-2 gap-2">
        <WizardInput
          value={deal.company}
          onChange={(v) => onUpdate({ company: v })}
          placeholder="Company name"
        />
        <WizardInput
          value={deal.buyerTitle}
          onChange={(v) => onUpdate({ buyerTitle: v })}
          placeholder="Buyer title (e.g. VP Sales)"
        />
      </div>
      <div className="grid grid-cols-3 gap-2">
        <WizardInput
          value={deal.industry}
          onChange={(v) => onUpdate({ industry: v })}
          placeholder="Industry"
        />
        <WizardInput
          value={deal.dealSize}
          onChange={(v) => onUpdate({ dealSize: v })}
          placeholder="Deal size (e.g. $25K)"
        />
        <WizardInput
          value={deal.salesCycle}
          onChange={(v) => onUpdate({ salesCycle: v })}
          placeholder="Cycle (e.g. 45 days)"
        />
      </div>
      <WizardInput
        value={deal.signals}
        onChange={(v) => onUpdate({ signals: v })}
        placeholder="What signals appeared before this deal? (e.g. hired SDRs, raised Series B...)"
      />
      <WizardInput
        value={deal.whyWonOrLost}
        onChange={(v) => onUpdate({ whyWonOrLost: v })}
        placeholder={
          isWon
            ? "Why did they buy? What tipped the decision?"
            : "Why did you lose? What was the blocker?"
        }
      />
    </div>
  );
}

function InvertStep({
  wiz,
}: {
  wiz: ReturnType<typeof useCampaignWizard>;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-clay-300 leading-relaxed">
        Add your recent closed deals — both won and lost. The AI compares
        patterns across both to find what predicts conversion. Aim for{" "}
        <span className="text-clay-100 font-medium">10+ won and 10+ lost</span>{" "}
        in the same segment for the best analysis.
      </p>

      {/* Deal counts */}
      <div className="flex items-center gap-3">
        <Badge
          variant="outline"
          className="bg-emerald-500/10 text-emerald-400 border-emerald-500/30"
        >
          <Trophy className="h-3 w-3 mr-1" />
          {wiz.wonCount} Won
        </Badge>
        <Badge
          variant="outline"
          className="bg-red-500/10 text-red-400 border-red-500/30"
        >
          <XCircle className="h-3 w-3 mr-1" />
          {wiz.lostCount} Lost
        </Badge>
        <span className="text-xs text-clay-500">
          {wiz.deals.length} total
        </span>
      </div>

      {/* Deal cards */}
      <div className="space-y-2 max-h-[320px] overflow-y-auto pr-1">
        {wiz.deals.map((deal) => (
          <DealCard
            key={deal.id}
            deal={deal}
            onUpdate={(updates) => wiz.updateDeal(deal.id, updates)}
            onRemove={() => wiz.removeDeal(deal.id)}
          />
        ))}
      </div>

      {/* Add deal buttons */}
      <div className="flex gap-2">
        <Button
          variant="outline"
          size="sm"
          onClick={() => wiz.addDeal("won")}
          className="gap-1.5 border-emerald-500/30 text-emerald-400 hover:bg-emerald-500/10"
        >
          <Plus className="h-3.5 w-3.5" />
          Add Won Deal
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={() => wiz.addDeal("lost")}
          className="gap-1.5 border-red-500/30 text-red-400 hover:bg-red-500/10"
        >
          <Plus className="h-3.5 w-3.5" />
          Add Lost Deal
        </Button>
      </div>

      {/* Analyze button */}
      {wiz.deals.filter((d) => d.company).length >= 2 && (
        <Button
          variant="outline"
          size="sm"
          onClick={wiz.analyzeDeals}
          disabled={wiz.dealAnalysis.loading}
          className="gap-2"
        >
          {wiz.dealAnalysis.loading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Sparkles className="h-3.5 w-3.5" />
          )}
          Analyze {wiz.deals.filter((d) => d.company).length} deals
        </Button>
      )}

      <AnalysisPanel analysis={wiz.dealAnalysis} />
    </div>
  );
}

/* ── Step: Find Pain ───────────────────────────────── */

function PainStep({
  wiz,
}: {
  wiz: ReturnType<typeof useCampaignWizard>;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-clay-300 leading-relaxed">
        Standard enrichment signals are table stakes. Find data sources unique to
        your segment.{" "}
        <span className="text-clay-100 font-medium">
          Drill, not peanut butter.
        </span>
      </p>
      <div className="space-y-3">
        {wiz.painSources.map((source, idx) => (
          <div
            key={idx}
            className="rounded-md border border-clay-600 bg-clay-800/50 p-3 space-y-2"
          >
            <div className="flex items-center justify-between">
              <span className="text-xs font-medium text-clay-400">
                Data Source {idx + 1}
              </span>
              {wiz.painSources.length > 1 && (
                <button
                  onClick={() => wiz.removePainSource(idx)}
                  className="text-clay-500 hover:text-red-400 transition-colors"
                >
                  <X className="h-3.5 w-3.5" />
                </button>
              )}
            </div>
            <WizardInput
              value={source.dataSource}
              onChange={(v) =>
                wiz.updatePainSource(idx, { ...source, dataSource: v })
              }
              placeholder="e.g. Building permits database, SEC filings, job board scrape..."
            />
            <WizardInput
              value={source.description}
              onChange={(v) =>
                wiz.updatePainSource(idx, { ...source, description: v })
              }
              placeholder="What pain does this data reveal?"
            />
            <select
              value={source.signalType}
              onChange={(e) =>
                wiz.updatePainSource(idx, {
                  ...source,
                  signalType: e.target.value,
                })
              }
              className="w-full rounded-md border border-clay-500 bg-clay-800 px-3 py-1.5 text-sm text-clay-100 focus:border-kiln-teal focus:outline-none"
            >
              <option value="">Signal type...</option>
              <option value="funding">Funding Round</option>
              <option value="hiring">Hiring Surge</option>
              <option value="tech-stack">Tech Stack Change</option>
              <option value="leadership">Leadership Change</option>
              <option value="product-launch">Product Launch</option>
              <option value="expansion">Geographic / Market Expansion</option>
              <option value="partnership">Partnership</option>
              <option value="acquisition">Acquisition</option>
              <option value="regulatory">Regulatory / Compliance</option>
              <option value="custom">Custom / Proprietary</option>
            </select>
          </div>
        ))}
      </div>
      <div className="flex gap-2">
        <Button
          variant="ghost"
          size="sm"
          onClick={wiz.addPainSource}
          className="gap-1.5"
        >
          <Plus className="h-3.5 w-3.5" />
          Add data source
        </Button>
        <Button
          variant="outline"
          size="sm"
          onClick={wiz.analyzePain}
          disabled={
            wiz.painAnalysis.loading ||
            !wiz.painSources.some((s) => s.dataSource)
          }
          className="gap-2"
        >
          {wiz.painAnalysis.loading ? (
            <Loader2 className="h-3.5 w-3.5 animate-spin" />
          ) : (
            <Sparkles className="h-3.5 w-3.5" />
          )}
          Evaluate sources
        </Button>
      </div>
      <AnalysisPanel analysis={wiz.painAnalysis} />
    </div>
  );
}

/* ── Step: Context ─────────────────────────────────── */

function ContextStep({
  wiz,
}: {
  wiz: ReturnType<typeof useCampaignWizard>;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-clay-300 leading-relaxed">
        Before writing a single message, assemble everything the AI needs. This
        context compounds — every future campaign builds on it.
      </p>
      <div className="space-y-3">
        <WizardField
          label="ICP description"
          value={wiz.campaignContext.icpDescription}
          onChange={(v) =>
            wiz.setCampaignContext({ ...wiz.campaignContext, icpDescription: v })
          }
          placeholder="e.g. B2B SaaS, 50-500 employees, post-Series A, building outbound for the first time..."
          rows={3}
        />
        <WizardField
          label="Competitive intelligence"
          value={wiz.campaignContext.competitiveIntel}
          onChange={(v) =>
            wiz.setCampaignContext({ ...wiz.campaignContext, competitiveIntel: v })
          }
          placeholder="e.g. Main competitors: Outreach, Salesloft. We win on personalization quality..."
          rows={3}
        />
        <WizardField
          label="Common objections"
          value={wiz.campaignContext.objections}
          onChange={(v) =>
            wiz.setCampaignContext({ ...wiz.campaignContext, objections: v })
          }
          placeholder="e.g. 'We already have a tool', 'Budget locked until Q3'..."
          rows={2}
        />
        <WizardField
          label="Industry notes"
          value={wiz.campaignContext.industryNotes}
          onChange={(v) =>
            wiz.setCampaignContext({ ...wiz.campaignContext, industryNotes: v })
          }
          placeholder="e.g. Regulatory changes Q2, conference in April, seasonal buying..."
          rows={2}
        />
      </div>
      <Button
        variant="outline"
        size="sm"
        onClick={wiz.analyzeContext}
        disabled={
          wiz.contextAnalysis.loading || !wiz.campaignContext.icpDescription
        }
        className="gap-2"
      >
        {wiz.contextAnalysis.loading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Sparkles className="h-3.5 w-3.5" />
        )}
        Check for gaps
      </Button>
      <AnalysisPanel analysis={wiz.contextAnalysis} />
    </div>
  );
}

/* ── Step: Plan ────────────────────────────────────── */

function PlanStep({
  wiz,
}: {
  wiz: ReturnType<typeof useCampaignWizard>;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-clay-300 leading-relaxed">
        Three questions: What unique data do we have? What pain does it prove?
        What would they pay to know?
      </p>
      <div className="space-y-3">
        <WizardField
          label="Segment"
          value={wiz.campaignPlan.segment}
          onChange={(v) =>
            wiz.setCampaignPlan({ ...wiz.campaignPlan, segment: v })
          }
          placeholder="e.g. B2B SaaS, 100-500 employees, post-Series B, hiring SDRs"
          rows={1}
        />
        <WizardField
          label="Data edge — what do we know that competitors don't?"
          value={wiz.campaignPlan.dataEdge}
          onChange={(v) =>
            wiz.setCampaignPlan({ ...wiz.campaignPlan, dataEdge: v })
          }
          placeholder="e.g. We can see their tech stack includes outdated tools..."
          rows={2}
        />
        <WizardField
          label="Pain hypothesis"
          value={wiz.campaignPlan.painHypothesis}
          onChange={(v) =>
            wiz.setCampaignPlan({ ...wiz.campaignPlan, painHypothesis: v })
          }
          placeholder="e.g. Scaling outbound but reps spend 40% of time researching..."
          rows={2}
        />
        <WizardField
          label="Permissionless Value Prop (PVP)"
          value={wiz.campaignPlan.pvp}
          onChange={(v) =>
            wiz.setCampaignPlan({ ...wiz.campaignPlan, pvp: v })
          }
          placeholder="What insight would they pay to know? e.g. 'Here are 15 companies in your ICP that just switched CRMs...'"
          rows={3}
        />
        <div className="grid grid-cols-2 gap-3">
          <WizardInput
            label="Target persona"
            value={wiz.campaignPlan.persona}
            onChange={(v) =>
              wiz.setCampaignPlan({ ...wiz.campaignPlan, persona: v })
            }
            placeholder="e.g. VP Sales, CRO"
          />
          <div className="space-y-1">
            <label className="text-xs font-medium text-clay-300 tracking-wide">
              Messaging framework
            </label>
            <select
              value={wiz.campaignPlan.framework}
              onChange={(e) =>
                wiz.setCampaignPlan({
                  ...wiz.campaignPlan,
                  framework: e.target.value,
                })
              }
              className="w-full rounded-md border border-clay-500 bg-clay-800 px-3 py-1.5 text-sm text-clay-100 focus:border-kiln-teal focus:outline-none"
            >
              <option value="PVC">PVC (Permission-Value-CTA)</option>
              <option value="PAS">PAS (Pain-Agitate-Solve)</option>
              <option value="BAB">BAB (Before-After-Bridge)</option>
              <option value="AIDA">AIDA</option>
            </select>
          </div>
        </div>
        <div className="grid grid-cols-3 gap-3">
          <div className="space-y-1">
            <label className="text-xs font-medium text-clay-300 tracking-wide">
              Sequence type
            </label>
            <select
              value={wiz.campaignPlan.sequence}
              onChange={(e) =>
                wiz.setCampaignPlan({
                  ...wiz.campaignPlan,
                  sequence: e.target.value,
                })
              }
              className="w-full rounded-md border border-clay-500 bg-clay-800 px-3 py-1.5 text-sm text-clay-100 focus:border-kiln-teal focus:outline-none"
            >
              <option value="cold-email">Cold Email (5-touch)</option>
              <option value="linkedin-first">LinkedIn-First</option>
              <option value="warm-intro">Warm Intro</option>
            </select>
          </div>
          <WizardInput
            label="Batch size"
            value={wiz.campaignPlan.initialBatchSize}
            onChange={(v) =>
              wiz.setCampaignPlan({ ...wiz.campaignPlan, initialBatchSize: v })
            }
            placeholder="30-50"
          />
          <WizardInput
            label="Trigger signals"
            value={wiz.campaignPlan.signals}
            onChange={(v) =>
              wiz.setCampaignPlan({ ...wiz.campaignPlan, signals: v })
            }
            placeholder="e.g. Series B + hiring"
          />
        </div>
      </div>
      <Button
        variant="outline"
        size="sm"
        onClick={wiz.generatePlan}
        disabled={
          wiz.planAnalysis.loading ||
          !wiz.campaignPlan.segment ||
          !wiz.campaignPlan.pvp
        }
        className="gap-2"
      >
        {wiz.planAnalysis.loading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Sparkles className="h-3.5 w-3.5" />
        )}
        Generate campaign plan
      </Button>
      <AnalysisPanel analysis={wiz.planAnalysis} />
    </div>
  );
}

/* ── Step: Review ──────────────────────────────────── */

function ReviewStep({
  wiz,
}: {
  wiz: ReturnType<typeof useCampaignWizard>;
}) {
  return (
    <div className="space-y-4">
      <p className="text-sm text-clay-300 leading-relaxed">
        Final check. The AI scores your campaign on 5 dimensions and flags the
        single biggest improvement.
      </p>

      {/* Summary */}
      <div className="rounded-md border border-clay-600 bg-clay-800/50 p-4 space-y-3">
        <div className="flex items-center justify-between">
          <h4 className="text-xs font-medium text-clay-400 tracking-wide uppercase">
            Campaign Summary
          </h4>
          <div className="flex gap-2">
            <Badge variant="secondary" className="text-[10px]">
              {wiz.wonCount} won / {wiz.lostCount} lost analyzed
            </Badge>
          </div>
        </div>
        <div className="grid grid-cols-2 gap-x-4 gap-y-1.5 text-sm">
          {(
            [
              ["Segment", wiz.campaignPlan.segment],
              ["Data Edge", wiz.campaignPlan.dataEdge],
              ["Pain", wiz.campaignPlan.painHypothesis],
              ["PVP", wiz.campaignPlan.pvp],
              ["Persona", wiz.campaignPlan.persona],
              ["Framework", wiz.campaignPlan.framework],
              ["Sequence", wiz.campaignPlan.sequence],
              ["Batch", wiz.campaignPlan.initialBatchSize],
            ] as const
          ).map(([label, val]) => (
            <div key={label} className="flex gap-2">
              <span className="text-clay-400 shrink-0 w-16">{label}:</span>
              <span className="text-clay-200 truncate">
                {val || (
                  <span className="text-clay-500 italic">not set</span>
                )}
              </span>
            </div>
          ))}
        </div>
      </div>

      <Button
        variant="outline"
        size="sm"
        onClick={wiz.generateReview}
        disabled={wiz.reviewAnalysis.loading}
        className="gap-2"
      >
        {wiz.reviewAnalysis.loading ? (
          <Loader2 className="h-3.5 w-3.5 animate-spin" />
        ) : (
          <Sparkles className="h-3.5 w-3.5" />
        )}
        Score this campaign
      </Button>
      <AnalysisPanel analysis={wiz.reviewAnalysis} />
    </div>
  );
}

/* ── Main dialog ───────────────────────────────────── */

export function CampaignWizard({
  open,
  onOpenChange,
}: {
  open: boolean;
  onOpenChange: (open: boolean) => void;
}) {
  const wiz = useCampaignWizard();
  const meta = STEP_META[wiz.step];

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-2xl max-h-[85vh] flex flex-col">
        <DialogHeader>
          <div className="flex items-center gap-3">
            <DialogTitle className="flex items-center gap-2">
              {meta.icon}
              {meta.label}
            </DialogTitle>
            <Badge variant="secondary" className="text-[10px]">
              {wiz.stepIndex + 1} / {wiz.totalSteps}
            </Badge>
          </div>
          <DialogDescription>{meta.description}</DialogDescription>
        </DialogHeader>

        {/* Progress bar */}
        <div className="px-5 pb-1">
          <div className="flex gap-1">
            {STEPS_ORDER.map((s, idx) => (
              <button
                key={s}
                onClick={() => wiz.goToStep(s)}
                title={STEP_META[s].label}
                className={`h-1.5 flex-1 rounded-full transition-colors ${
                  idx <= wiz.stepIndex ? "bg-kiln-teal" : "bg-clay-600"
                }`}
              />
            ))}
          </div>
        </div>

        {/* Step content */}
        <div className="flex-1 overflow-y-auto px-5 py-3 min-h-0">
          {wiz.step === "intro" && <IntroStep />}
          {wiz.step === "invert" && <InvertStep wiz={wiz} />}
          {wiz.step === "pain" && <PainStep wiz={wiz} />}
          {wiz.step === "context" && <ContextStep wiz={wiz} />}
          {wiz.step === "plan" && <PlanStep wiz={wiz} />}
          {wiz.step === "review" && <ReviewStep wiz={wiz} />}
        </div>

        <DialogFooter className="flex-row justify-between">
          <div className="flex gap-2">
            {wiz.canGoBack && (
              <Button variant="ghost" size="sm" onClick={wiz.goBack}>
                <ArrowLeft className="h-3.5 w-3.5" />
                Back
              </Button>
            )}
            {wiz.stepIndex > 0 && (
              <Button
                variant="ghost"
                size="sm"
                onClick={() => {
                  wiz.reset();
                }}
                className="text-clay-400"
              >
                <RotateCcw className="h-3.5 w-3.5" />
                Reset
              </Button>
            )}
          </div>
          <div>
            {wiz.canGoNext ? (
              <Button size="sm" onClick={wiz.goNext}>
                {wiz.step === "intro" ? "Begin" : "Continue"}
                <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            ) : (
              <Button
                size="sm"
                onClick={() => onOpenChange(false)}
              >
                <CheckCircle2 className="h-3.5 w-3.5" />
                Done
              </Button>
            )}
          </div>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

/* ── Standalone trigger button ─────────────────────── */

export function CampaignWizardButton() {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Button onClick={() => setOpen(true)} className="gap-2">
        <Rocket className="h-4 w-4" />
        New Campaign
      </Button>
      <CampaignWizard open={open} onOpenChange={setOpen} />
    </>
  );
}
