"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { Building2, AlertCircle, RefreshCw } from "lucide-react";
import { Button } from "@/components/ui/button";
import type { WebhookResponse } from "@/lib/types";
import type { SkillStatus } from "@/hooks/use-research";

interface CompanyOverviewCardProps {
  data: WebhookResponse | null;
  status: SkillStatus;
  error?: string | null;
  onRetry?: () => void;
}

export function CompanyOverviewCard({
  data,
  status,
  error,
  onRetry,
}: CompanyOverviewCardProps) {
  return (
    <Card className="border-clay-600 bg-clay-800/50">
      <CardHeader className="pb-2">
        <CardTitle className="flex items-center gap-2 text-sm font-medium text-clay-200">
          <Building2 className="h-4 w-4 text-kiln-teal" />
          Company Overview
        </CardTitle>
      </CardHeader>
      <CardContent>
        {status === "loading" && (
          <div className="space-y-2.5">
            <Skeleton className="h-3 w-full bg-clay-600" />
            <Skeleton className="h-3 w-4/5 bg-clay-600" />
            <Skeleton className="h-3 w-3/5 bg-clay-600" />
          </div>
        )}

        {status === "error" && (
          <div className="flex items-center gap-2 text-xs text-red-400">
            <AlertCircle className="h-3.5 w-3.5 shrink-0" />
            <span className="flex-1">{error || "Failed to load"}</span>
            {onRetry && (
              <Button
                variant="ghost"
                size="sm"
                onClick={onRetry}
                className="h-6 px-2 text-[10px] text-clay-300 hover:text-clay-100"
              >
                <RefreshCw className="h-3 w-3 mr-1" /> Retry
              </Button>
            )}
          </div>
        )}

        {status === "done" && data && (
          <div className="space-y-3">
            {!!data.company_summary && (
              <p className="text-xs text-clay-200 leading-relaxed">
                {String(data.company_summary)}
              </p>
            )}
            <div className="flex flex-wrap gap-1.5">
              {!!data.industry && (
                <Badge
                  variant="outline"
                  className="text-[10px] border-clay-500 text-clay-200"
                >
                  {String(data.industry)}
                </Badge>
              )}
              {!!data.employee_count && (
                <Badge
                  variant="outline"
                  className="text-[10px] border-clay-500 text-clay-200"
                >
                  {String(data.employee_count)} employees
                </Badge>
              )}
              {!!data.funding_stage && (
                <Badge
                  variant="outline"
                  className="text-[10px] border-clay-500 text-clay-200"
                >
                  {String(data.funding_stage)}
                </Badge>
              )}
            </div>
            {Array.isArray(data.recent_news) && (
              <div className="pt-2 border-t border-clay-700">
                <p className="text-[10px] font-semibold uppercase tracking-wider text-clay-300 mb-1.5">
                  Recent News
                </p>
                <ul className="space-y-1">
                  {(data.recent_news as string[]).slice(0, 3).map((item, i) => (
                    <li
                      key={i}
                      className="text-xs text-clay-200 leading-relaxed"
                    >
                      {item}
                    </li>
                  ))}
                </ul>
              </div>
            )}
            {typeof data.confidence_score === "number" && (
              <div className="flex items-center gap-1.5 pt-1">
                <span className="text-[10px] text-clay-300">Confidence</span>
                <div className="flex-1 h-1 rounded-full bg-clay-600 overflow-hidden">
                  <div
                    className="h-full rounded-full bg-kiln-teal transition-all"
                    style={{
                      width: `${Math.round(Number(data.confidence_score) * 100)}%`,
                    }}
                  />
                </div>
                <span className="text-[10px] text-clay-200">
                  {Math.round(Number(data.confidence_score) * 100)}%
                </span>
              </div>
            )}
          </div>
        )}

        {status === "idle" && (
          <p className="text-xs text-clay-300">Waiting...</p>
        )}
      </CardContent>
    </Card>
  );
}
