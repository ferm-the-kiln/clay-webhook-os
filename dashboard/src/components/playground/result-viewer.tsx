"use client";

import { useState, useEffect } from "react";
import type { Destination, WebhookResponse } from "@/lib/types";
import { pushDataToDestination } from "@/lib/api";
import { formatSmartDuration } from "@/lib/utils";
import { Card, CardContent, CardHeader, CardFooter } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { EmptyState } from "@/components/ui/empty-state";
import { CheckCircle, Loader2, Send, Sparkles, XCircle, Code } from "lucide-react";
import { toast } from "sonner";
import { FeedbackButtons } from "@/components/feedback/feedback-buttons";
import { FormattedResult } from "@/components/playground/formatted-results";

const STEPS = [
  { label: "Queued", icon: Send },
  { label: "Processing with Claude", icon: Sparkles },
  { label: "Formatting response", icon: Loader2 },
  { label: "Complete", icon: CheckCircle },
];

function ProgressSteps({ elapsed }: { elapsed: number }) {
  // Heuristic: estimate step based on elapsed time
  const step = elapsed < 500 ? 0 : elapsed < 2000 ? 1 : elapsed < 3000 ? 2 : 3;

  return (
    <div className="space-y-3 w-full max-w-xs">
      {STEPS.map((s, i) => {
        const active = i === step;
        const done = i < step;
        const Icon = s.icon;
        return (
          <div
            key={s.label}
            className={`flex items-center gap-3 transition-all duration-300 ${
              done
                ? "text-kiln-teal"
                : active
                  ? "text-kiln-teal"
                  : "text-clay-700"
            }`}
          >
            <Icon
              className={`h-4 w-4 shrink-0 ${active ? "animate-pulse" : ""}`}
            />
            <span className="text-sm">{s.label}{i === 1 && elapsed > 500 ? "..." : ""}</span>
            {done && <CheckCircle className="h-3.5 w-3.5 ml-auto text-kiln-teal" />}
          </div>
        );
      })}
    </div>
  );
}

export function ResultViewer({
  result,
  loading,
  skill,
  model,
  destinations = [],
  jobId,
}: {
  result: WebhookResponse | null;
  loading: boolean;
  skill?: string;
  model?: string;
  destinations?: Destination[];
  jobId?: string;
}) {
  const [elapsed, setElapsed] = useState(0);
  const [pushDestId, setPushDestId] = useState("");
  const [pushing, setPushing] = useState(false);

  useEffect(() => {
    if (!loading) {
      setElapsed(0);
      return;
    }
    const start = Date.now();
    const id = setInterval(() => {
      setElapsed(Date.now() - start);
    }, 200);
    return () => clearInterval(id);
  }, [loading]);

  if (loading) {
    return (
      <Card className="border-clay-800 bg-white shadow-sm h-full">
        <CardContent className="flex h-full items-center justify-center">
          <ProgressSteps elapsed={elapsed} />
        </CardContent>
      </Card>
    );
  }

  if (!result) {
    return (
      <div className="h-full flex items-center">
        <EmptyState
          title="Ready to test"
          description="Pick a skill, tweak the data, and hit Run. Results appear here instantly."
        />
      </div>
    );
  }

  const meta = result._meta;
  const isError = result.error;
  const display = { ...result };
  delete display._meta;

  const [showRaw, setShowRaw] = useState(false);

  return (
    <Card className="border-clay-800 bg-white shadow-sm flex flex-col h-full overflow-hidden">
      {meta && (
        <CardHeader className="flex-row items-center gap-3 border-b border-clay-800 px-4 py-2.5 space-y-0">
          <Badge
            variant="outline"
            className="bg-kiln-teal/10 text-kiln-teal border-kiln-teal/30"
          >
            {meta.model}
          </Badge>
          <span className="text-xs text-clay-500">
            {formatSmartDuration(meta.duration_ms)}
          </span>
          {meta.cached && (
            <Badge
              variant="outline"
              className="bg-kiln-mustard/10 text-kiln-mustard border-kiln-mustard/30"
            >
              cached
            </Badge>
          )}
          <div className="flex items-center gap-1 ml-auto">
            {!isError && skill && (
              <button
                onClick={() => setShowRaw(!showRaw)}
                className={`p-1 rounded transition-colors ${
                  showRaw ? "text-kiln-teal bg-kiln-teal/10" : "text-clay-500 hover:text-clay-300"
                }`}
                title={showRaw ? "Show formatted" : "Show raw JSON"}
              >
                <Code className="h-3.5 w-3.5" />
              </button>
            )}
            {!isError && (
              <CheckCircle className="h-4 w-4 text-kiln-teal" />
            )}
            {isError && (
              <XCircle className="h-4 w-4 text-kiln-coral" />
            )}
          </div>
        </CardHeader>
      )}
      <CardContent className="flex-1 overflow-auto p-0">
        {isError ? (
          <pre className="p-4 font-[family-name:var(--font-mono)] text-sm leading-relaxed text-kiln-coral">
            {JSON.stringify(display, null, 2)}
          </pre>
        ) : skill && !showRaw ? (
          <FormattedResult skill={skill} data={display} />
        ) : (
          <pre className="p-4 font-[family-name:var(--font-mono)] text-sm leading-relaxed text-clay-200">
            {JSON.stringify(display, null, 2)}
          </pre>
        )}
      </CardContent>
      {!isError && skill && (
        <div className="border-t border-clay-800 px-4 py-3">
          <FeedbackButtons
            jobId={jobId || "playground"}
            skill={skill}
            model={model}
          />
        </div>
      )}
      {!isError && destinations.length > 0 && (
        <CardFooter className="border-t border-clay-800 px-4 py-3 gap-2">
          <Select value={pushDestId} onValueChange={setPushDestId}>
            <SelectTrigger className="flex-1 border-clay-700 bg-clay-900 text-clay-200 h-9 text-sm">
              <SelectValue placeholder="Push to..." />
            </SelectTrigger>
            <SelectContent className="border-clay-700 bg-clay-900">
              {destinations.map((d) => (
                <SelectItem key={d.id} value={d.id}>
                  {d.name} ({d.type === "clay_webhook" ? "Clay" : "Webhook"})
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
          <Button
            size="sm"
            disabled={!pushDestId || pushing}
            className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold h-9"
            onClick={async () => {
              if (!pushDestId) return;
              setPushing(true);
              try {
                const res = await pushDataToDestination(pushDestId, display);
                if (res.ok) {
                  toast.success("Pushed to destination", {
                    description: `Sent to ${res.destination_name}`,
                  });
                } else {
                  toast.error("Push failed", { description: res.error });
                }
              } catch (e) {
                toast.error("Push failed", { description: (e as Error).message });
              } finally {
                setPushing(false);
              }
            }}
          >
            <Send className="h-3.5 w-3.5 mr-1.5" />
            {pushing ? "Pushing..." : "Push"}
          </Button>
        </CardFooter>
      )}
    </Card>
  );
}
