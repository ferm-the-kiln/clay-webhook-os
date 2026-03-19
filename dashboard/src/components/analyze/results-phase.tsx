"use client";

import React from "react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import {
  ArrowLeft,
  Download,
  AlertTriangle,
  Loader2,
  CheckCircle2,
  Lightbulb,
  Target,
  Shield,
  TrendingUp,
  BarChart3,
} from "lucide-react";
import type { AnalysisResult } from "@/lib/types";

interface ResultsPhaseProps {
  analysis: AnalysisResult | null;
  isRunning: boolean;
  onBack: () => void;
}

export function ResultsPhase({ analysis, isRunning, onBack }: ResultsPhaseProps) {
  if (isRunning || analysis?.status === "processing") {
    return (
      <div className="flex flex-col items-center justify-center py-20">
        <Loader2 className="h-10 w-10 text-kiln-amber animate-spin mb-4" />
        <p className="text-sm font-medium text-clay-200">Running analysis...</p>
        <p className="text-xs text-clay-400 mt-1">
          Pre-processing data and generating insights with AI
        </p>
        {analysis?.preprocessed_summary && (
          <p className="text-xs text-clay-500 mt-3">
            Processed {analysis.preprocessed_summary.row_count} rows,{" "}
            {analysis.preprocessed_summary.column_count} columns,{" "}
            {analysis.preprocessed_summary.cross_tab_count} cross-tabs
          </p>
        )}
      </div>
    );
  }

  if (!analysis) {
    return (
      <div className="flex flex-col items-center justify-center py-20 text-clay-400">
        <p>No analysis selected</p>
      </div>
    );
  }

  if (analysis.status === "failed") {
    return (
      <div className="space-y-4">
        <Button variant="ghost" size="sm" onClick={onBack} className="text-clay-300">
          <ArrowLeft className="h-4 w-4 mr-1" /> Back
        </Button>
        <div className="flex flex-col items-center justify-center py-12">
          <AlertTriangle className="h-10 w-10 text-red-400 mb-4" />
          <p className="text-sm font-medium text-red-400">Analysis failed</p>
          <p className="text-xs text-clay-400 mt-1 max-w-md text-center">
            {analysis.error_message ?? "Unknown error"}
          </p>
          <Button variant="outline" size="sm" className="mt-4" onClick={onBack}>
            Try Again
          </Button>
        </div>
      </div>
    );
  }

  const results = analysis.results ?? {};
  const takeaways = (results.key_takeaways as string[]) ?? [];
  const confidence = (results.confidence_score as number) ?? 0;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button variant="ghost" size="sm" onClick={onBack} className="text-clay-300">
            <ArrowLeft className="h-4 w-4 mr-1" /> Back
          </Button>
          <div>
            <h3 className="text-lg font-semibold text-clay-100">
              {analysis.analysis_type.replace(/-/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())} Results
            </h3>
            <div className="flex items-center gap-2 text-xs text-clay-400">
              <CheckCircle2 className="h-3 w-3 text-green-400" />
              <span>Completed</span>
              {confidence > 0 && (
                <>
                  <span>&middot;</span>
                  <span>Confidence: {(confidence * 100).toFixed(0)}%</span>
                </>
              )}
            </div>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          onClick={() => {
            const blob = new Blob([JSON.stringify(results, null, 2)], { type: "application/json" });
            const url = URL.createObjectURL(blob);
            const a = document.createElement("a");
            a.href = url;
            a.download = `analysis-${analysis.analysis_type}-${analysis.analysis_id}.json`;
            a.click();
            URL.revokeObjectURL(url);
          }}
        >
          <Download className="h-4 w-4 mr-1" /> Export JSON
        </Button>
      </div>

      {/* Key takeaways */}
      {takeaways.length > 0 && (
        <Card className="rounded-xl border-kiln-amber/20 bg-kiln-amber/5">
          <CardContent className="pt-4 pb-4">
            <div className="flex items-center gap-2 mb-3">
              <Lightbulb className="h-4 w-4 text-kiln-amber" />
              <span className="text-sm font-semibold text-clay-100">Key Takeaways</span>
            </div>
            <ul className="space-y-2">
              {takeaways.map((t, i) => (
                <li key={i} className="flex items-start gap-2 text-sm text-clay-200">
                  <span className="text-kiln-amber font-mono text-xs mt-0.5">{i + 1}.</span>
                  {t}
                </li>
              ))}
            </ul>
          </CardContent>
        </Card>
      )}

      {/* Dynamic result sections */}
      {renderAnalysisResults(analysis.analysis_type, results)}

      {/* Raw JSON fallback */}
      <details className="group">
        <summary className="text-xs text-clay-500 cursor-pointer hover:text-clay-400">
          View raw JSON
        </summary>
        <pre className="mt-2 p-3 rounded-lg bg-clay-800 text-xs text-clay-300 overflow-auto max-h-96">
          {JSON.stringify(results, null, 2)}
        </pre>
      </details>
    </div>
  );
}

function renderAnalysisResults(analysisType: string, results: Record<string, unknown>) {
  const sections: React.ReactElement[] = [];

  // ICP
  if (results.icp_definition) {
    sections.push(
      <Card key="icp-def" className="rounded-xl">
        <CardContent className="pt-4 pb-4">
          <div className="flex items-center gap-2 mb-2">
            <Target className="h-4 w-4 text-kiln-amber" />
            <span className="text-sm font-semibold text-clay-100">ICP Definition</span>
          </div>
          <p className="text-sm text-clay-200">{results.icp_definition as string}</p>
        </CardContent>
      </Card>
    );
  }

  // Strongest predictors / win themes / churn predictors etc
  const listSections: { key: string; label: string; icon: typeof Target }[] = [
    { key: "strongest_predictors", label: "Strongest Predictors", icon: TrendingUp },
    { key: "anti_patterns", label: "Anti-Patterns", icon: Shield },
    { key: "recommended_filters", label: "Recommended Filters", icon: BarChart3 },
    { key: "segment_insights", label: "Segment Insights", icon: Target },
    { key: "win_themes", label: "Win Themes", icon: TrendingUp },
    { key: "loss_themes", label: "Loss Themes", icon: Shield },
    { key: "objection_angles", label: "Objection Angles", icon: Shield },
    { key: "qualification_questions", label: "Qualification Questions", icon: Target },
    { key: "churn_predictors", label: "Churn Predictors", icon: AlertTriangle },
    { key: "retention_signals", label: "Retention Signals", icon: TrendingUp },
    { key: "aha_features", label: "Aha Features", icon: Lightbulb },
    { key: "risk_indicators", label: "Risk Indicators", icon: AlertTriangle },
    { key: "adoption_patterns", label: "Adoption Patterns", icon: BarChart3 },
    { key: "underused_features", label: "Underused Features", icon: BarChart3 },
    { key: "engagement_tiers", label: "Engagement Tiers", icon: Target },
    { key: "top_performing_patterns", label: "Top Performing Patterns", icon: TrendingUp },
    { key: "underperforming_patterns", label: "Underperforming", icon: Shield },
    { key: "timing_insights", label: "Timing Insights", icon: Target },
    { key: "subject_line_analysis", label: "Subject Line Analysis", icon: Target },
    { key: "expansion_triggers", label: "Expansion Triggers", icon: TrendingUp },
    { key: "upsell_segments", label: "Upsell Segments", icon: Target },
    { key: "timing_patterns", label: "Timing Patterns", icon: Target },
    { key: "risk_factors", label: "Risk Factors", icon: AlertTriangle },
  ];

  for (const { key, label, icon: Icon } of listSections) {
    const data = results[key];
    if (!Array.isArray(data) || data.length === 0) continue;

    sections.push(
      <Card key={key} className="rounded-xl">
        <CardContent className="pt-4 pb-4">
          <div className="flex items-center gap-2 mb-3">
            <Icon className="h-4 w-4 text-clay-400" />
            <span className="text-sm font-semibold text-clay-100">{label}</span>
            <span className="text-xs text-clay-500">({data.length})</span>
          </div>
          <div className="space-y-2">
            {(data as Record<string, unknown>[]).map((item, i) => (
              <div key={i} className="p-2.5 rounded-lg bg-clay-800/50 text-sm">
                {Object.entries(item).map(([k, v]) => (
                  <div key={k} className="flex gap-2">
                    <span className="text-clay-500 text-xs min-w-[100px]">{k}:</span>
                    <span className="text-clay-200 text-xs">
                      {Array.isArray(v) ? v.join(", ") : String(v ?? "")}
                    </span>
                  </div>
                ))}
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    );
  }

  // Power user profile (object)
  if (results.power_user_profile && typeof results.power_user_profile === "object") {
    const profile = results.power_user_profile as Record<string, unknown>;
    sections.push(
      <Card key="power-user" className="rounded-xl">
        <CardContent className="pt-4 pb-4">
          <div className="flex items-center gap-2 mb-2">
            <Target className="h-4 w-4 text-clay-400" />
            <span className="text-sm font-semibold text-clay-100">Power User Profile</span>
          </div>
          {profile.description ? <p className="text-sm text-clay-200 mb-2">{String(profile.description)}</p> : null}
          {Array.isArray(profile.key_behaviors) ? (
            <ul className="list-disc list-inside text-xs text-clay-300 space-y-1">
              {(profile.key_behaviors as string[]).map((b, i) => <li key={i}>{b}</li>)}
            </ul>
          ) : null}
          {profile.percentage_of_users ? (
            <p className="text-xs text-clay-400 mt-2">{String(profile.percentage_of_users)} of users</p>
          ) : null}
        </CardContent>
      </Card>
    );
  }

  // Personalization impact (object)
  if (results.personalization_impact && typeof results.personalization_impact === "object") {
    const impact = results.personalization_impact as Record<string, unknown>;
    sections.push(
      <Card key="personalization" className="rounded-xl">
        <CardContent className="pt-4 pb-4">
          <div className="flex items-center gap-2 mb-2">
            <Target className="h-4 w-4 text-clay-400" />
            <span className="text-sm font-semibold text-clay-100">Personalization Impact</span>
          </div>
          {impact.finding ? <p className="text-sm text-clay-200 mb-2">{String(impact.finding)}</p> : null}
          {impact.recommendation ? <p className="text-xs text-clay-400">{String(impact.recommendation)}</p> : null}
        </CardContent>
      </Card>
    );
  }

  return <div className="space-y-4">{sections}</div>;
}
