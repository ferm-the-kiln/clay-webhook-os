"use client";

import type { QualityAlert } from "@/lib/types";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";
import { AlertTriangle, AlertCircle } from "lucide-react";

export function QualityAlerts({ alerts }: { alerts: QualityAlert[] }) {
  if (alerts.length === 0) {
    return (
      <div className="rounded-xl border border-clay-500 p-6 text-center">
        <p className="text-sm text-clay-200">
          No quality alerts. All skills are above threshold.
        </p>
      </div>
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {alerts.map((alert) => {
        const isCritical = alert.severity === "critical";
        const approvalPct = Math.round(alert.approval_rate * 100);

        return (
          <Card
            key={alert.skill}
            className={cn(
              "border transition-colors duration-150",
              isCritical
                ? "border-kiln-coral/40 bg-kiln-coral/5"
                : "border-kiln-mustard/40 bg-kiln-mustard/5"
            )}
          >
            <CardContent className="p-5">
              <div className="flex items-start justify-between mb-3">
                <div className="flex items-center gap-2">
                  {isCritical ? (
                    <AlertCircle className="h-4 w-4 text-kiln-coral" />
                  ) : (
                    <AlertTriangle className="h-4 w-4 text-kiln-mustard" />
                  )}
                  <span className="text-sm font-medium text-clay-100">
                    {alert.skill}
                  </span>
                </div>
                <Badge
                  className={cn(
                    "text-[10px] uppercase tracking-wider font-semibold",
                    isCritical
                      ? "bg-kiln-coral/15 text-kiln-coral border-kiln-coral/25"
                      : "bg-kiln-mustard/15 text-kiln-mustard border-kiln-mustard/25"
                  )}
                >
                  {alert.severity}
                </Badge>
              </div>

              <div className="space-y-2">
                <div className="flex items-center justify-between">
                  <span className="text-xs text-clay-300">Approval Rate</span>
                  <span
                    className={cn(
                      "text-sm font-bold font-[family-name:var(--font-mono)]",
                      isCritical ? "text-kiln-coral" : "text-kiln-mustard"
                    )}
                  >
                    {approvalPct}%
                  </span>
                </div>

                <div className="h-2 bg-clay-800 rounded-full overflow-hidden">
                  <div
                    className={cn(
                      "h-full rounded-full transition-all",
                      isCritical ? "bg-kiln-coral" : "bg-kiln-mustard"
                    )}
                    style={{ width: `${approvalPct}%` }}
                  />
                </div>

                <div className="flex items-center justify-between text-xs text-clay-300">
                  <span>{alert.total_ratings} total ratings</span>
                  <span>{alert.thumbs_down} negative</span>
                </div>

                {alert.recommendation && (
                  <p className="text-xs text-clay-200 mt-2 pt-2 border-t border-clay-600">
                    {alert.recommendation}
                  </p>
                )}
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
