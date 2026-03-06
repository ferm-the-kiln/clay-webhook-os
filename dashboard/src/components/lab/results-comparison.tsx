"use client";

import { useState } from "react";
import type { Experiment } from "@/lib/types";
import { promoteVariant } from "@/lib/api";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Crown, Clock, Hash, ThumbsUp, ThumbsDown } from "lucide-react";
import { toast } from "sonner";

export function ResultsComparison({
  experiment,
  onPromoted,
}: {
  experiment: Experiment;
  onPromoted?: () => void;
}) {
  const [promoting, setPromoting] = useState<string | null>(null);

  const variantResults = experiment.variant_ids.map((vid) => ({
    id: vid,
    ...(experiment.results[vid] || {
      variant_id: vid,
      runs: 0,
      avg_duration_ms: 0,
      total_tokens: 0,
      thumbs_up: 0,
      thumbs_down: 0,
    }),
  }));

  // Find winner by approval rate, then by runs
  const withApproval = variantResults.map((v) => {
    const total = v.thumbs_up + v.thumbs_down;
    return {
      ...v,
      approval_rate: total > 0 ? v.thumbs_up / total : 0,
      total_feedback: total,
    };
  });
  const winner =
    withApproval.length > 0
      ? withApproval.reduce((best, curr) =>
          curr.approval_rate > best.approval_rate ||
          (curr.approval_rate === best.approval_rate && curr.runs > best.runs)
            ? curr
            : best
        )
      : null;

  const handlePromote = async (variantId: string) => {
    setPromoting(variantId);
    try {
      await promoteVariant(experiment.id, variantId);
      toast.success(`Promoted ${variantId} to default`);
      onPromoted?.();
    } catch (e) {
      toast.error("Promote failed", { description: (e as Error).message });
    } finally {
      setPromoting(null);
    }
  };

  if (Object.keys(experiment.results).length === 0) {
    return (
      <div className="text-center py-8">
        <p className="text-sm text-clay-500">
          No results yet. Run the experiment first.
        </p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <h4 className="text-sm font-medium text-clay-300">
        Results: {experiment.name}
      </h4>
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        {withApproval.map((v) => {
          const isWinner = winner && v.id === winner.id && v.runs > 0;
          return (
            <Card
              key={v.id}
              className={`border-clay-800 bg-clay-900 ${
                isWinner ? "ring-1 ring-kiln-teal/30" : ""
              }`}
            >
              <CardHeader className="pb-2">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <h5 className="font-medium text-clay-100 text-sm">
                      {v.id}
                    </h5>
                    {isWinner && (
                      <Crown className="h-4 w-4 text-kiln-mustard" />
                    )}
                  </div>
                  <Badge
                    variant="outline"
                    className="text-[10px] border-clay-700 text-clay-400"
                  >
                    {v.runs} runs
                  </Badge>
                </div>
              </CardHeader>
              <CardContent className="pt-0 space-y-3">
                <div className="grid grid-cols-2 gap-2 text-sm">
                  <div className="flex items-center gap-1.5">
                    <Clock className="h-3 w-3 text-clay-500" />
                    <span className="text-clay-400 text-xs">
                      {Math.round(v.avg_duration_ms)}ms avg
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Hash className="h-3 w-3 text-clay-500" />
                    <span className="text-clay-400 text-xs">
                      {v.total_tokens} tokens
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <ThumbsUp className="h-3 w-3 text-kiln-teal" />
                    <span className="text-clay-400 text-xs">
                      {v.thumbs_up}
                    </span>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <ThumbsDown className="h-3 w-3 text-kiln-coral" />
                    <span className="text-clay-400 text-xs">
                      {v.thumbs_down}
                    </span>
                  </div>
                </div>

                {v.total_feedback > 0 && (
                  <div>
                    <div className="flex items-center justify-between text-xs mb-1">
                      <span className="text-clay-500">Approval</span>
                      <span
                        className={
                          v.approval_rate >= 0.7
                            ? "text-kiln-teal"
                            : "text-kiln-coral"
                        }
                      >
                        {Math.round(v.approval_rate * 100)}%
                      </span>
                    </div>
                    <div className="h-1.5 bg-clay-800 rounded-full overflow-hidden">
                      <div
                        className={`h-full rounded-full ${
                          v.approval_rate >= 0.7
                            ? "bg-kiln-teal"
                            : "bg-kiln-coral"
                        }`}
                        style={{
                          width: `${Math.round(v.approval_rate * 100)}%`,
                        }}
                      />
                    </div>
                  </div>
                )}

                {experiment.status === "completed" && v.id !== "default" && (
                  <Button
                    size="sm"
                    variant="outline"
                    disabled={promoting !== null}
                    onClick={() => handlePromote(v.id)}
                    className="w-full border-clay-700 text-clay-300 hover:text-kiln-teal hover:border-kiln-teal/30 text-xs"
                  >
                    {promoting === v.id ? "Promoting..." : "Promote to Default"}
                  </Button>
                )}
              </CardContent>
            </Card>
          );
        })}
      </div>
    </div>
  );
}
