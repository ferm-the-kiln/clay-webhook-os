"use client";

import { useState, useCallback } from "react";
import { runWebhook } from "@/lib/api";

export type CampaignStep =
  | "intro"
  | "invert"
  | "pain"
  | "context"
  | "plan"
  | "review";

/* ── Deal entry for inversion step ─────────────────── */

export type DealOutcome = "won" | "lost";

export interface DealEntry {
  id: string;
  company: string;
  outcome: DealOutcome;
  dealSize: string;
  salesCycle: string;
  buyerTitle: string;
  industry: string;
  signals: string;
  whyWonOrLost: string;
}

export interface PainSource {
  dataSource: string;
  description: string;
  signalType: string;
}

export interface CampaignContext {
  icpDescription: string;
  competitiveIntel: string;
  objections: string;
  industryNotes: string;
}

export interface CampaignPlan {
  segment: string;
  dataEdge: string;
  painHypothesis: string;
  pvp: string;
  persona: string;
  framework: string;
  sequence: string;
  signals: string;
  initialBatchSize: string;
}

export interface StepAnalysis {
  content: string;
  loading: boolean;
  error: string | null;
}

export interface UseCampaignWizardReturn {
  // Navigation
  step: CampaignStep;
  stepIndex: number;
  totalSteps: number;
  goNext: () => void;
  goBack: () => void;
  goToStep: (step: CampaignStep) => void;
  canGoNext: boolean;
  canGoBack: boolean;

  // Step 1: Invert from best deals
  deals: DealEntry[];
  addDeal: (outcome: DealOutcome) => void;
  updateDeal: (id: string, deal: Partial<DealEntry>) => void;
  removeDeal: (id: string) => void;
  dealAnalysis: StepAnalysis;
  analyzeDeals: () => Promise<void>;
  wonCount: number;
  lostCount: number;

  // Step 2: Find discoverable pain
  painSources: PainSource[];
  addPainSource: () => void;
  updatePainSource: (idx: number, source: PainSource) => void;
  removePainSource: (idx: number) => void;
  painAnalysis: StepAnalysis;
  analyzePain: () => Promise<void>;

  // Step 3: Build context
  campaignContext: CampaignContext;
  setCampaignContext: (val: CampaignContext) => void;
  contextAnalysis: StepAnalysis;
  analyzeContext: () => Promise<void>;

  // Step 4: Plan the play
  campaignPlan: CampaignPlan;
  setCampaignPlan: (val: CampaignPlan) => void;
  planAnalysis: StepAnalysis;
  generatePlan: () => Promise<void>;

  // Step 5: Review
  reviewAnalysis: StepAnalysis;
  generateReview: () => Promise<void>;

  // Global
  reset: () => void;
}

const STEPS: CampaignStep[] = ["intro", "invert", "pain", "context", "plan", "review"];

function makeDealId(): string {
  return `deal-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
}

function newDeal(outcome: DealOutcome): DealEntry {
  return {
    id: makeDealId(),
    company: "",
    outcome,
    dealSize: "",
    salesCycle: "",
    buyerTitle: "",
    industry: "",
    signals: "",
    whyWonOrLost: "",
  };
}

const emptyContext: CampaignContext = {
  icpDescription: "",
  competitiveIntel: "",
  objections: "",
  industryNotes: "",
};

const emptyPlan: CampaignPlan = {
  segment: "",
  dataEdge: "",
  painHypothesis: "",
  pvp: "",
  persona: "",
  framework: "PVC",
  sequence: "cold-email",
  signals: "",
  initialBatchSize: "50",
};

const emptyAnalysis: StepAnalysis = { content: "", loading: false, error: null };

export function useCampaignWizard(): UseCampaignWizardReturn {
  const [step, setStep] = useState<CampaignStep>("intro");

  // Step 1 — deals
  const [deals, setDeals] = useState<DealEntry[]>([]);
  const [dealAnalysis, setDealAnalysis] = useState<StepAnalysis>(emptyAnalysis);

  // Step 2 — pain sources
  const [painSources, setPainSources] = useState<PainSource[]>([
    { dataSource: "", description: "", signalType: "" },
  ]);
  const [painAnalysis, setPainAnalysis] = useState<StepAnalysis>(emptyAnalysis);

  // Step 3 — context
  const [campaignContext, setCampaignContext] = useState<CampaignContext>(emptyContext);
  const [contextAnalysis, setContextAnalysis] = useState<StepAnalysis>(emptyAnalysis);

  // Step 4 — plan
  const [campaignPlan, setCampaignPlan] = useState<CampaignPlan>(emptyPlan);
  const [planAnalysis, setPlanAnalysis] = useState<StepAnalysis>(emptyAnalysis);

  // Step 5 — review
  const [reviewAnalysis, setReviewAnalysis] = useState<StepAnalysis>(emptyAnalysis);

  const stepIndex = STEPS.indexOf(step);
  const canGoNext = stepIndex < STEPS.length - 1;
  const canGoBack = stepIndex > 0;

  const goNext = useCallback(() => {
    const idx = STEPS.indexOf(step);
    if (idx < STEPS.length - 1) setStep(STEPS[idx + 1]);
  }, [step]);

  const goBack = useCallback(() => {
    const idx = STEPS.indexOf(step);
    if (idx > 0) setStep(STEPS[idx - 1]);
  }, [step]);

  const goToStep = useCallback((s: CampaignStep) => setStep(s), []);

  // Deal management
  const wonCount = deals.filter((d) => d.outcome === "won").length;
  const lostCount = deals.filter((d) => d.outcome === "lost").length;

  const addDeal = useCallback((outcome: DealOutcome) => {
    setDeals((prev) => [...prev, newDeal(outcome)]);
  }, []);

  const updateDeal = useCallback((id: string, updates: Partial<DealEntry>) => {
    setDeals((prev) =>
      prev.map((d) => (d.id === id ? { ...d, ...updates } : d))
    );
  }, []);

  const removeDeal = useCallback((id: string) => {
    setDeals((prev) => prev.filter((d) => d.id !== id));
  }, []);

  // AI analysis runner
  const runAiAnalysis = useCallback(
    async (prompt: string, setter: (val: StepAnalysis) => void) => {
      setter({ content: "", loading: true, error: null });
      try {
        const res = await runWebhook({
          skill: "classify",
          data: { raw_text: prompt },
          instructions:
            "You are a GTM campaign strategist helping build a high-conversion outbound campaign. Analyze the data provided and give specific, actionable recommendations. Use bullet points. Be opinionated — tell them what to do, not what they could do. No fluff, no hedging.",
          model: "sonnet",
        });
        const content =
          typeof res === "string"
            ? res
            : (res as Record<string, unknown>)?.result
              ? String((res as Record<string, unknown>).result)
              : JSON.stringify(res, null, 2);
        setter({ content, loading: false, error: null });
      } catch (e) {
        setter({
          content: "",
          loading: false,
          error: e instanceof Error ? e.message : "Analysis failed",
        });
      }
    },
    []
  );

  // Step 1 — Analyze deals
  const analyzeDeals = useCallback(async () => {
    const wonDeals = deals.filter((d) => d.outcome === "won" && d.company);
    const lostDeals = deals.filter((d) => d.outcome === "lost" && d.company);

    const formatDeal = (d: DealEntry) =>
      `- ${d.company} | ${d.buyerTitle} | ${d.industry} | $${d.dealSize} | ${d.salesCycle} cycle | Signals: ${d.signals} | Why: ${d.whyWonOrLost}`;

    const prompt = `Analyze these closed deals to find patterns that predict future conversions.

CLOSED-WON (${wonDeals.length} deals):
${wonDeals.map(formatDeal).join("\n")}

CLOSED-LOST (${lostDeals.length} deals):
${lostDeals.map(formatDeal).join("\n")}

Analyze and provide:

1. **WINNING PATTERN** — What do won deals have in common that lost deals don't? Look at: buyer titles, industries, deal sizes, sales cycles, signals, and reasons.

2. **PREDICTIVE SIGNALS** — What public/observable signals appeared before won deals? Which of these could you detect BEFORE they enter pipeline?

3. **LOSS PATTERN** — What characterizes losses? Is it pricing, timing, competition, or wrong buyer?

4. **ICP REFINEMENT** — Based on this data, who should you target? Be specific: title, company size, industry, and what trigger signals to watch for.

5. **DATA SOURCES** — What databases, APIs, or public records could surface these predictive signals early? Think beyond standard enrichment (everyone has job changes and funding rounds).

6. **PVP SEED** — Based on won deals, what market intelligence would be so valuable to this buyer that they'd respond to a cold email delivering it?`;

    await runAiAnalysis(prompt, setDealAnalysis);
  }, [deals, runAiAnalysis]);

  // Step 2 — Analyze pain sources
  const analyzePain = useCallback(async () => {
    const wonDeals = deals.filter((d) => d.outcome === "won" && d.company);
    const sourcesText = painSources
      .filter((s) => s.dataSource || s.description)
      .map(
        (s, i) =>
          `Source ${i + 1}: ${s.dataSource} — ${s.description} (signal type: ${s.signalType})`
      )
      .join("\n");

    const prompt = `Evaluate these discoverable pain data sources for a GTM campaign:

${sourcesText}

Context from deal analysis — won deals had these patterns:
${wonDeals.map((d) => `${d.company}: ${d.signals} → ${d.whyWonOrLost}`).join("\n")}

For each data source, tell me:
1. **Uniqueness** — Does everyone have this data, or is it a proprietary edge?
2. **Pain signal** — What specific pain does this data prove?
3. **PVP potential** — What insight from this data would the prospect pay to receive?
4. **Verdict** — Go deeper on this source, or find something better?

Then recommend: which combination of these sources creates the strongest campaign angle?`;
    await runAiAnalysis(prompt, setPainAnalysis);
  }, [painSources, deals, runAiAnalysis]);

  // Step 3 — Analyze context
  const analyzeContext = useCallback(async () => {
    const prompt = `Review this campaign context and identify gaps:

ICP: ${campaignContext.icpDescription}
Competitive intel: ${campaignContext.competitiveIntel}
Common objections: ${campaignContext.objections}
Industry notes: ${campaignContext.industryNotes}

Deal context: ${deals.filter((d) => d.outcome === "won").map((d) => `${d.company}: ${d.whyWonOrLost}`).join("; ")}
Data sources: ${painSources.map((s) => s.dataSource).filter(Boolean).join(", ")}

Tell me:
1. What context is missing that would make messages stronger?
2. Which objections should we preempt in messaging?
3. Which persona should we target first and why?
4. Biggest risk with this campaign?`;
    await runAiAnalysis(prompt, setContextAnalysis);
  }, [campaignContext, deals, painSources, runAiAnalysis]);

  // Step 4 — Generate plan
  const generatePlan = useCallback(async () => {
    const prompt = `Generate a campaign execution plan:

Segment: ${campaignPlan.segment}
Data edge: ${campaignPlan.dataEdge}
Pain hypothesis: ${campaignPlan.painHypothesis}
PVP: ${campaignPlan.pvp}
Persona: ${campaignPlan.persona}
Framework: ${campaignPlan.framework}
Sequence: ${campaignPlan.sequence}
Signals: ${campaignPlan.signals}
Batch size: ${campaignPlan.initialBatchSize}

Context: ICP is ${campaignContext.icpDescription}.
Won deal patterns: ${deals.filter((d) => d.outcome === "won").map((d) => `${d.company}: ${d.whyWonOrLost}`).join("; ")}

Provide:
1. A sample first-touch message using the ${campaignPlan.framework} framework
2. The exact data fields needed per prospect
3. Qualification criteria
4. Success metrics and thresholds
5. When to scale vs. iterate`;
    await runAiAnalysis(prompt, setPlanAnalysis);
  }, [campaignPlan, campaignContext, deals, runAiAnalysis]);

  // Step 5 — Generate review
  const generateReview = useCallback(async () => {
    const prompt = `Final campaign review. Score 1-10 on each dimension:

SEGMENT: ${campaignPlan.segment}
DATA EDGE: ${campaignPlan.dataEdge}
PAIN HYPOTHESIS: ${campaignPlan.painHypothesis}
PVP: ${campaignPlan.pvp}
PERSONA: ${campaignPlan.persona}
FRAMEWORK: ${campaignPlan.framework}
SEQUENCE: ${campaignPlan.sequence}

Based on ${deals.length} analyzed deals (${deals.filter((d) => d.outcome === "won").length} won, ${deals.filter((d) => d.outcome === "lost").length} lost).
ICP: ${campaignContext.icpDescription}
Data sources: ${painSources.map((s) => s.dataSource).filter(Boolean).join(", ")}

Score on:
1. Specificity (is the segment tight enough?)
2. Data edge (do competitors have this data too?)
3. PVP strength (would they pay to receive this?)
4. Pain-to-product connection
5. Scalability (can you run this on 500+ prospects?)

Then give the ONE thing that would most improve this campaign.`;
    await runAiAnalysis(prompt, setReviewAnalysis);
  }, [campaignPlan, campaignContext, deals, painSources, runAiAnalysis]);

  // Pain source management
  const addPainSource = useCallback(() => {
    setPainSources((prev) => [...prev, { dataSource: "", description: "", signalType: "" }]);
  }, []);

  const updatePainSource = useCallback((idx: number, source: PainSource) => {
    setPainSources((prev) => prev.map((s, i) => (i === idx ? source : s)));
  }, []);

  const removePainSource = useCallback((idx: number) => {
    setPainSources((prev) => prev.filter((_, i) => i !== idx));
  }, []);

  const reset = useCallback(() => {
    setStep("intro");
    setDeals([]);
    setPainSources([{ dataSource: "", description: "", signalType: "" }]);
    setCampaignContext(emptyContext);
    setCampaignPlan(emptyPlan);
    setDealAnalysis(emptyAnalysis);
    setPainAnalysis(emptyAnalysis);
    setContextAnalysis(emptyAnalysis);
    setPlanAnalysis(emptyAnalysis);
    setReviewAnalysis(emptyAnalysis);
  }, []);

  return {
    step,
    stepIndex,
    totalSteps: STEPS.length,
    goNext,
    goBack,
    goToStep,
    canGoNext,
    canGoBack,
    deals,
    addDeal,
    updateDeal,
    removeDeal,
    dealAnalysis,
    analyzeDeals,
    wonCount,
    lostCount,
    painSources,
    addPainSource,
    updatePainSource,
    removePainSource,
    painAnalysis,
    analyzePain,
    campaignContext,
    setCampaignContext,
    contextAnalysis,
    analyzeContext,
    campaignPlan,
    setCampaignPlan,
    planAnalysis,
    generatePlan,
    reviewAnalysis,
    generateReview,
    reset,
  };
}
