"use client";

import type { Experiment } from "@/lib/types";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Trash2, Eye, ArrowRight } from "lucide-react";
import { formatRelativeTime } from "@/lib/utils";

const STATUS_STYLES: Record<string, string> = {
  draft: "bg-clay-800 text-clay-400 border-clay-700",
  running: "bg-kiln-mustard/10 text-kiln-mustard border-kiln-mustard/30",
  completed: "bg-kiln-teal/10 text-kiln-teal border-kiln-teal/30",
};

export function ExperimentList({
  experiments,
  onView,
  onDelete,
}: {
  experiments: Experiment[];
  onView: (e: Experiment) => void;
  onDelete: (e: Experiment) => void;
}) {
  if (experiments.length === 0) {
    return (
      <EmptyState
        title="No experiments yet"
        description="Create an experiment to A/B test skill variants."
      />
    );
  }

  const sorted = [...experiments].sort(
    (a, b) => b.created_at - a.created_at
  );

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
      {sorted.map((exp) => {
        const totalRuns = Object.values(exp.results).reduce(
          (sum, r) => sum + r.runs,
          0
        );
        return (
          <Card key={exp.id} className="border-clay-800 bg-clay-900">
            <CardHeader className="pb-2">
              <div className="flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <h5 className="font-medium text-clay-100 text-sm">
                    {exp.name}
                  </h5>
                  <Badge
                    variant="outline"
                    className={STATUS_STYLES[exp.status]}
                  >
                    {exp.status}
                  </Badge>
                </div>
                <div className="flex items-center gap-1">
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-clay-500 hover:text-clay-200"
                    onClick={() => onView(exp)}
                  >
                    <Eye className="h-3.5 w-3.5" />
                  </Button>
                  <Button
                    variant="ghost"
                    size="icon"
                    className="h-7 w-7 text-clay-500 hover:text-kiln-coral"
                    onClick={() => onDelete(exp)}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </Button>
                </div>
              </div>
            </CardHeader>
            <CardContent className="pt-0 space-y-2">
              <div className="flex items-center gap-2 text-xs">
                <span className="text-clay-500">Skill:</span>
                <span className="text-kiln-teal">{exp.skill}</span>
              </div>
              <div className="flex flex-wrap items-center gap-1">
                {exp.variant_ids.map((vid, i) => (
                  <span key={vid} className="flex items-center gap-1">
                    <Badge
                      variant="outline"
                      className="text-[10px] border-clay-700 text-clay-400"
                    >
                      {vid}
                    </Badge>
                    {i < exp.variant_ids.length - 1 && (
                      <span className="text-clay-700 text-xs">vs</span>
                    )}
                  </span>
                ))}
              </div>
              <div className="flex items-center gap-3 text-xs text-clay-500">
                <span>{totalRuns} runs</span>
                <span>{formatRelativeTime(exp.created_at)}</span>
              </div>
            </CardContent>
          </Card>
        );
      })}
    </div>
  );
}
