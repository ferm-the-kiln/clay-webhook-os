"use client";

import type { PipelineDefinition } from "@/lib/types";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { EmptyState } from "@/components/ui/empty-state";
import { Edit2, Trash2, Play, ArrowRight } from "lucide-react";

export function PipelineList({
  pipelines,
  onEdit,
  onDelete,
  onTest,
}: {
  pipelines: PipelineDefinition[];
  onEdit: (p: PipelineDefinition) => void;
  onDelete: (p: PipelineDefinition) => void;
  onTest: (p: PipelineDefinition) => void;
}) {
  if (pipelines.length === 0) {
    return (
      <EmptyState
        title="No pipelines yet"
        description="Create your first pipeline to chain skills together."
      />
    );
  }

  return (
    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
      {pipelines.map((p) => (
        <Card key={p.name} className="border-clay-800 bg-clay-900 flex flex-col">
          <CardHeader className="pb-2">
            <div className="flex items-center justify-between">
              <h4 className="font-semibold text-clay-100">{p.name}</h4>
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-clay-500 hover:text-kiln-teal"
                  onClick={() => onTest(p)}
                >
                  <Play className="h-3.5 w-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-clay-500 hover:text-clay-200"
                  onClick={() => onEdit(p)}
                >
                  <Edit2 className="h-3.5 w-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  className="h-7 w-7 text-clay-500 hover:text-kiln-coral"
                  onClick={() => onDelete(p)}
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </div>
            </div>
            {p.description && (
              <p className="text-xs text-clay-500 mt-1">{p.description}</p>
            )}
          </CardHeader>
          <CardContent className="pt-0 mt-auto">
            <div className="flex flex-wrap items-center gap-1.5">
              {p.steps.map((s, i) => (
                <span key={i} className="flex items-center gap-1.5">
                  <Badge
                    variant="outline"
                    className="bg-kiln-teal/10 text-kiln-teal border-kiln-teal/30 text-xs"
                  >
                    {s.skill}
                  </Badge>
                  {i < p.steps.length - 1 && (
                    <ArrowRight className="h-3 w-3 text-clay-600" />
                  )}
                </span>
              ))}
            </div>
          </CardContent>
        </Card>
      ))}
    </div>
  );
}
