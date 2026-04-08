"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import {
  Target,
  AlertCircle,
  RefreshCw,
  CheckCircle2,
  XCircle,
  Lightbulb,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import type { WebhookResponse } from "@/lib/types";
import type { SkillStatus } from "@/hooks/use-research";

interface IcpFitCardProps {
  qualifierData: WebhookResponse | null;
  qualifierStatus: SkillStatus;
  qualifierError?: string | null;
  researcherData: WebhookResponse | null;
  researcherStatus: SkillStatus;
  researcherError?: string | null;
  onRetryQualifier?: () => void;
  onRetryResearcher?: () => void;
}

interface AngleEntry {
  angle?: string;
  reasoning?: string;
}

export function IcpFitCard({
  qualifierData,
  qualifierStatus,
  qualifierError,
  researcherData,
  researcherStatus,
  researcherError,
  onRetryQualifier,
  onRetryResearcher,
}: IcpFitCardProps) {
  const isLoading =
    qualifierStatus === "loading" || researcherStatus === "loading";
  const bothDone =
    (qualifierStatus === "done" || qualifierStatus === "error") &&
    (researcherStatus === "done" || researcherStatus === "error");

  const qualified = qualifierData?.qualified;
  const score =
    typeof qualifierData?.qualification_score === "number"
      ? qualifierData.qualification_score
      : typeof researcherData?.product_relevance === "object" &&
          researcherData?.product_relevance !== null
        ? (researcherData.product_relevance as { score?: number }).score
        : null;

  const angles: AngleEntry[] = Array.isArray(
    researcherData?.recommended_angles
  )
    ? (researcherData.recommended_angles as AngleEntry[])
    : [];

  return (
    <Card className="border-clay-600 bg-clay-800/50 md:col-span-2">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-clay-200">
          <Target className="h-4 w-4 text-amber-400" />
          ICP Fit & Angles
        </CardTitle>
      </CardHeader>
      <CardContent>
        {isLoading && !bothDone && (
          <div className="space-y-2.5">
            <Skeleton className="h-8 w-48 bg-clay-600" />
            <Skeleton className="h-3 w-full bg-clay-600" />
            <Skeleton className="h-3 w-3/4 bg-clay-600" />
          </div>
        )}

        {qualifierStatus === "error" && (
          <div className="flex items-center gap-2 text-xs text-red-400 mb-3">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            <span className="flex-1">
              Qualifier: {qualifierError || "Failed"}
            </span>
            {onRetryQualifier && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onRetryQualifier}
                className="h-6 px-2 text-[10px] text-clay-300 hover:text-clay-100"
              >
                <RefreshCw className="h-3 w-3 mr-1" /> Retry
              </Button>
            )}
          </div>
        )}

        {researcherStatus === "error" && (
          <div className="flex items-center gap-2 text-xs text-red-400 mb-3">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            <span className="flex-1">
              Researcher: {researcherError || "Failed"}
            </span>
            {onRetryResearcher && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onRetryResearcher}
                className="h-6 px-2 text-[10px] text-clay-300 hover:text-clay-100"
              >
                <RefreshCw className="h-3 w-3 mr-1" /> Retry
              </Button>
            )}
          </div>
        )}

        {bothDone && (qualifierData || researcherData) && (
          <div className="space-y-4">
            {/* Qualification verdict */}
            <div className="flex items-center gap-4">
              {qualified != null && (
                <div
                  className={cn(
                    "flex items-center gap-2 px-3 py-1.5 rounded-lg border",
                    String(qualified).toLowerCase() === "y" ||
                      qualified === true
                      ? "border-green-500/30 bg-green-500/5 text-green-400"
                      : "border-red-500/30 bg-red-500/5 text-red-400"
                  )}
                >
                  {String(qualified).toLowerCase() === "y" ||
                  qualified === true ? (
                    <CheckCircle2 className="h-4 w-4" />
                  ) : (
                    <XCircle className="h-4 w-4" />
                  )}
                  <span className="text-sm font-medium">
                    {String(qualified).toLowerCase() === "y" ||
                    qualified === true
                      ? "Qualified"
                      : "Not Qualified"}
                  </span>
                </div>
              )}
              {score !== null && score !== undefined && (
                <div className="flex items-center gap-2">
                  <div className="relative w-10 h-10">
                    <svg className="w-10 h-10 -rotate-90" viewBox="0 0 36 36">
                      <circle
                        cx="18"
                        cy="18"
                        r="14"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="3"
                        className="text-clay-600"
                      />
                      <circle
                        cx="18"
                        cy="18"
                        r="14"
                        fill="none"
                        stroke="currentColor"
                        strokeWidth="3"
                        strokeDasharray={`${(Number(score) / 10) * 88} 88`}
                        className="text-kiln-teal"
                      />
                    </svg>
                    <span className="absolute inset-0 flex items-center justify-center text-[10px] font-bold text-clay-100">
                      {Number(score).toFixed(1)}
                    </span>
                  </div>
                  <span className="text-[10px] text-clay-300">/ 10</span>
                </div>
              )}
              {!!qualifierData?.archetype && (
                <Badge
                  variant="outline"
                  className="text-[10px] border-clay-500 text-clay-200"
                >
                  {String(qualifierData.archetype)}
                </Badge>
              )}
            </div>

            {/* Reasoning */}
            {!!(qualifierData?.reasoning ||
              researcherData?.icp_fit_assessment) && (
              <p className="text-xs text-clay-200 leading-relaxed">
                {String(
                  qualifierData?.reasoning ||
                    researcherData?.icp_fit_assessment
                )}
              </p>
            )}

            {/* Recommended angles */}
            {angles.length > 0 && (
              <div className="pt-2 border-t border-clay-700">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-clay-300 mb-2 flex items-center gap-1.5">
                  <Lightbulb className="h-3 w-3" />
                  Recommended Angles
                </p>
                <div className="space-y-2">
                  {angles.slice(0, 4).map((a, i) => (
                    <div key={i} className="pl-3 border-l-2 border-kiln-teal/30">
                      <p className="text-xs font-medium text-clay-100">
                        {a.angle || `Angle ${i + 1}`}
                      </p>
                      {a.reasoning && (
                        <p className="text-[11px] text-clay-300 mt-0.5">
                          {a.reasoning}
                        </p>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {/* Negative signals */}
            {Array.isArray(researcherData?.negative_signals) &&
              (researcherData.negative_signals as string[]).length > 0 && (
                <div className="pt-2 border-t border-clay-700">
                  <p className="text-[10px] font-semibold uppercase tracking-wider text-red-400/70 mb-1.5">
                    Caution
                  </p>
                  <ul className="space-y-1">
                    {(researcherData.negative_signals as string[])
                      .slice(0, 3)
                      .map((s, i) => (
                        <li
                          key={i}
                          className="text-xs text-clay-300 leading-relaxed"
                        >
                          {s}
                        </li>
                      ))}
                  </ul>
                </div>
              )}
          </div>
        )}

        {qualifierStatus === "idle" && researcherStatus === "idle" && (
          <p className="text-xs text-clay-300">Waiting...</p>
        )}
      </CardContent>
    </Card>
  );
}
