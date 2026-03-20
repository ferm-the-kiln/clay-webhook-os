"use client";

import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Target,
  Trophy,
  UserX,
  BarChart3,
  Mail,
  TrendingUp,
  Play,
  Loader2,
  ChevronRight,
} from "lucide-react";
import type { AnalysisType, AnalysisResult } from "@/lib/types";
import type { LucideIcon } from "lucide-react";

interface AnalysisTypeCard {
  type: AnalysisType;
  label: string;
  description: string;
  icon: LucideIcon;
  requiresOutcome: boolean;
}

const ANALYSIS_TYPES: AnalysisTypeCard[] = [
  {
    type: "icp",
    label: "ICP Detection",
    description: "Find patterns in your closed-won vs closed-lost deals",
    icon: Target,
    requiresOutcome: true,
  },
  {
    type: "win-loss",
    label: "Win/Loss Analysis",
    description: "Categorize win and loss reasons, surface objection patterns",
    icon: Trophy,
    requiresOutcome: true,
  },
  {
    type: "churn",
    label: "Churn Patterns",
    description: "Identify churn predictors from usage and support data",
    icon: UserX,
    requiresOutcome: true,
  },
  {
    type: "usage",
    label: "Feature Adoption",
    description: "Analyze which features drive retention and expansion",
    icon: BarChart3,
    requiresOutcome: false,
  },
  {
    type: "sequence-performance",
    label: "Sequence Performance",
    description: "Find winning patterns in your outbound sequences",
    icon: Mail,
    requiresOutcome: false,
  },
  {
    type: "expansion",
    label: "Expansion Triggers",
    description: "Identify signals that predict upsell and expansion",
    icon: TrendingUp,
    requiresOutcome: false,
  },
];

interface ConfigurePhaseProps {
  datasetName: string;
  rowCount: number;
  columns: string[];
  analysisType: AnalysisType | null;
  outcomeColumn: string | null;
  segmentColumns: string[];
  businessContext: string;
  isRunning: boolean;
  analyses: AnalysisResult[];
  onConfigChange: (config: {
    analysisType?: AnalysisType;
    outcomeColumn?: string | null;
    segmentColumns?: string[];
    businessContext?: string;
  }) => void;
  onRun: () => void;
  onViewAnalysis: (analysis: AnalysisResult) => void;
}

export function ConfigurePhase({
  datasetName,
  rowCount,
  columns,
  analysisType,
  outcomeColumn,
  segmentColumns,
  businessContext,
  isRunning,
  analyses,
  onConfigChange,
  onRun,
  onViewAnalysis,
}: ConfigurePhaseProps) {
  const selectedType = ANALYSIS_TYPES.find((t) => t.type === analysisType);
  const canRun = analysisType && (!selectedType?.requiresOutcome || outcomeColumn);

  return (
    <div className="space-y-6">
      {/* Dataset info bar */}
      <div className="flex items-center gap-3 text-sm text-clay-300">
        <span className="font-medium text-clay-100">{datasetName}</span>
        <span>&middot;</span>
        <span>{rowCount.toLocaleString()} rows</span>
        <span>&middot;</span>
        <span>{columns.length} columns</span>
      </div>

      {/* Analysis type selection */}
      <div>
        <h3 className="text-sm font-medium text-clay-200 mb-3">Choose analysis type</h3>
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
          {ANALYSIS_TYPES.map((at) => (
            <Card
              key={at.type}
              className={`rounded-xl cursor-pointer transition-all ${
                analysisType === at.type
                  ? "border-kiln-amber bg-kiln-amber/5"
                  : "hover:border-clay-500"
              }`}
              onClick={() => onConfigChange({ analysisType: at.type })}
            >
              <CardContent className="pt-4 pb-4">
                <div className="flex items-center gap-2 mb-1">
                  <at.icon className={`h-4 w-4 ${analysisType === at.type ? "text-kiln-amber" : "text-clay-300"}`} />
                  <span className="text-sm font-medium text-clay-100">{at.label}</span>
                </div>
                <p className="text-xs text-clay-300">{at.description}</p>
              </CardContent>
            </Card>
          ))}
        </div>
      </div>

      {/* Column mapping (show when type is selected) */}
      {analysisType && (
        <div className="space-y-4">
          {selectedType?.requiresOutcome && (
            <div>
              <label className="text-sm font-medium text-clay-200 block mb-1.5">
                Outcome column <span className="text-red-400">*</span>
              </label>
              <p className="text-xs text-clay-300 mb-2">
                Which column contains the outcome? (e.g., Won/Lost, Churned/Retained)
              </p>
              <Select
                value={outcomeColumn ?? ""}
                onValueChange={(v) => onConfigChange({ outcomeColumn: v || null })}
              >
                <SelectTrigger className="w-full max-w-sm">
                  <SelectValue placeholder="Select column..." />
                </SelectTrigger>
                <SelectContent>
                  {columns.map((col) => (
                    <SelectItem key={col} value={col}>{col}</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          )}

          <div>
            <label className="text-sm font-medium text-clay-200 block mb-1.5">
              Segment columns <span className="text-clay-300">(optional)</span>
            </label>
            <p className="text-xs text-clay-300 mb-2">
              Columns to cross-tabulate against. Leave empty for auto-detection.
            </p>
            <div className="flex flex-wrap gap-2">
              {columns.map((col) => (
                <button
                  key={col}
                  onClick={() => {
                    const next = segmentColumns.includes(col)
                      ? segmentColumns.filter((c) => c !== col)
                      : [...segmentColumns, col];
                    onConfigChange({ segmentColumns: next });
                  }}
                  className={`px-2.5 py-1 text-xs rounded-md border transition-colors ${
                    segmentColumns.includes(col)
                      ? "border-kiln-amber bg-kiln-amber/10 text-kiln-amber"
                      : "border-clay-600 text-clay-300 hover:border-clay-500"
                  }`}
                >
                  {col}
                </button>
              ))}
            </div>
          </div>

          <div>
            <label className="text-sm font-medium text-clay-200 block mb-1.5">
              Business context <span className="text-clay-300">(optional)</span>
            </label>
            <p className="text-xs text-clay-300 mb-2">
              What does your company sell? Who is your ICP? This helps the AI contextualize patterns.
            </p>
            <Textarea
              placeholder="e.g., B2B SaaS selling to mid-market DevOps teams, $50-500 employee companies"
              value={businessContext}
              onChange={(e) => onConfigChange({ businessContext: e.target.value })}
              rows={3}
            />
          </div>
        </div>
      )}

      {/* Run button */}
      <div className="flex items-center gap-3">
        <Button
          onClick={onRun}
          disabled={!canRun || isRunning}
          className="bg-kiln-amber text-clay-900 hover:bg-kiln-amber/90 font-semibold"
        >
          {isRunning ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Analyzing...
            </>
          ) : (
            <>
              <Play className="h-4 w-4 mr-2" />
              Run Analysis
            </>
          )}
        </Button>
        {isRunning && (
          <span className="text-xs text-clay-300">
            Pre-processing data and running AI analysis...
          </span>
        )}
      </div>

      {/* Previous analyses */}
      {analyses.length > 0 && (
        <div>
          <h3 className="text-sm font-medium text-clay-200 mb-3">Previous analyses</h3>
          <div className="space-y-2">
            {analyses.map((a) => (
              <button
                key={a.analysis_id}
                onClick={() => onViewAnalysis(a)}
                className="w-full flex items-center justify-between p-3 rounded-lg border border-clay-700 hover:border-clay-600 transition-colors text-left"
              >
                <div>
                  <span className="text-sm text-clay-100 font-medium">
                    {ANALYSIS_TYPES.find((t) => t.type === a.analysis_type)?.label ?? a.analysis_type}
                  </span>
                  <span className="text-xs text-clay-300 ml-2">
                    {a.status === "completed" ? "Completed" : a.status === "failed" ? "Failed" : "Processing"}
                  </span>
                </div>
                <ChevronRight className="h-4 w-4 text-clay-300" />
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
