"use client";

import { useState } from "react";
import { testPipeline } from "@/lib/api";
import type { PipelineTestResult } from "@/lib/types";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Textarea } from "@/components/ui/textarea";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { formatDuration } from "@/lib/utils";
import { CheckCircle, XCircle, Loader2, Play } from "lucide-react";
import { toast } from "sonner";

export function PipelineTestPanel({ pipelineName }: { pipelineName: string }) {
  const [dataStr, setDataStr] = useState(
    JSON.stringify(
      {
        first_name: "Sarah",
        company_name: "Acme",
        industry: "SaaS",
        client_slug: "twelve-labs",
      },
      null,
      2
    )
  );
  const [result, setResult] = useState<PipelineTestResult | null>(null);
  const [running, setRunning] = useState(false);

  const handleTest = async () => {
    let data: Record<string, unknown>;
    try {
      data = JSON.parse(dataStr);
    } catch {
      toast.error("Invalid JSON");
      return;
    }

    setRunning(true);
    setResult(null);
    try {
      const res = await testPipeline(pipelineName, { data });
      setResult(res);
    } catch (e) {
      toast.error("Test failed", { description: (e as Error).message });
    } finally {
      setRunning(false);
    }
  };

  return (
    <div className="space-y-4">
      <div>
        <label className="text-xs text-clay-500 uppercase tracking-wide mb-2 block">
          Test Data (JSON)
        </label>
        <Textarea
          value={dataStr}
          onChange={(e) => setDataStr(e.target.value)}
          className="h-32 font-[family-name:var(--font-mono)] text-sm border-clay-700 bg-clay-950 text-clay-200 resize-none"
        />
      </div>
      <Button
        onClick={handleTest}
        disabled={running}
        className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
      >
        {running ? (
          <>
            <Loader2 className="h-4 w-4 mr-2 animate-spin" />
            Running...
          </>
        ) : (
          <>
            <Play className="h-4 w-4 mr-2" />
            Test Pipeline
          </>
        )}
      </Button>

      {result && (
        <div className="space-y-3">
          <div className="flex items-center gap-3">
            <Badge
              variant="outline"
              className="bg-kiln-teal/10 text-kiln-teal border-kiln-teal/30"
            >
              {formatDuration(result.total_duration_ms)}
            </Badge>
            <span className="text-xs text-clay-500">
              {result.steps.length} steps
            </span>
          </div>

          {result.steps.map((step, i) => (
            <Card key={i} className="border-clay-800 bg-clay-950">
              <CardHeader className="py-2 px-3 flex-row items-center gap-2 space-y-0">
                {step.success ? (
                  <CheckCircle className="h-4 w-4 text-kiln-teal" />
                ) : (
                  <XCircle className="h-4 w-4 text-kiln-coral" />
                )}
                <span className="text-sm font-medium text-clay-200">
                  {step.skill}
                </span>
                {step.duration_ms > 0 && (
                  <span className="text-xs text-clay-500 ml-auto font-[family-name:var(--font-mono)]">
                    {formatDuration(step.duration_ms)}
                  </span>
                )}
              </CardHeader>
              <CardContent className="px-3 pb-3 pt-0">
                {step.error && (
                  <p className="text-xs text-kiln-coral">{step.error}</p>
                )}
                {step.output && (
                  <pre className="text-xs text-clay-300 font-[family-name:var(--font-mono)] max-h-40 overflow-auto whitespace-pre-wrap">
                    {JSON.stringify(step.output, null, 2)}
                  </pre>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
}
