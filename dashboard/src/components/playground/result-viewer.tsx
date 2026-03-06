"use client";

import type { WebhookResponse } from "@/lib/types";
import { formatDuration } from "@/lib/utils";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { EmptyState } from "@/components/ui/empty-state";

export function ResultViewer({
  result,
  loading,
}: {
  result: WebhookResponse | null;
  loading: boolean;
}) {
  if (loading) {
    return (
      <Card className="border-clay-800 bg-clay-900 h-full">
        <CardContent className="flex h-full items-center justify-center">
          <div className="space-y-3 w-full max-w-sm">
            <Skeleton className="h-4 w-full bg-clay-800" />
            <Skeleton className="h-4 w-3/4 bg-clay-800" />
            <Skeleton className="h-4 w-5/6 bg-clay-800" />
            <p className="text-sm text-clay-500 text-center mt-4">
              Processing...
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!result) {
    return (
      <div className="h-full flex items-center">
        <EmptyState
          title="Ready to test"
          description="Select a skill and click Run to see results."
          asset="/brand-assets/v2-playground.png"
        />
      </div>
    );
  }

  const meta = result._meta;
  const isError = result.error;
  const display = { ...result };
  delete display._meta;

  return (
    <Card className="border-clay-800 bg-clay-900 flex flex-col h-full overflow-hidden">
      {meta && (
        <CardHeader className="flex-row items-center gap-3 border-b border-clay-800 px-4 py-2.5 space-y-0">
          <Badge
            variant="outline"
            className="bg-kiln-teal/10 text-kiln-teal border-kiln-teal/30"
          >
            {meta.model}
          </Badge>
          <span className="text-xs text-clay-500">
            {formatDuration(meta.duration_ms)}
          </span>
          {meta.cached && (
            <Badge
              variant="outline"
              className="bg-kiln-mustard/10 text-kiln-mustard border-kiln-mustard/30"
            >
              cached
            </Badge>
          )}
        </CardHeader>
      )}
      <CardContent className="flex-1 overflow-auto p-0">
        <pre
          className={`p-4 font-[family-name:var(--font-mono)] text-sm leading-relaxed ${
            isError ? "text-kiln-coral" : "text-clay-200"
          }`}
        >
          {JSON.stringify(display, null, 2)}
        </pre>
      </CardContent>
    </Card>
  );
}
