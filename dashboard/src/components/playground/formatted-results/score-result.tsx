"use client";

import { Badge } from "@/components/ui/badge";
import { Target } from "lucide-react";

function ScoreGauge({ score }: { score: number }) {
  const pct = Math.min(100, Math.max(0, score));
  const color =
    pct >= 80
      ? "#5ce0d2"
      : pct >= 60
        ? "#e0c85c"
        : pct >= 40
          ? "#e09a5c"
          : "#e07a5c";

  return (
    <div className="flex items-center gap-4">
      <div className="relative h-24 w-24">
        <svg viewBox="0 0 100 100" className="h-full w-full -rotate-90">
          <circle
            cx="50"
            cy="50"
            r="40"
            fill="none"
            stroke="#2a2724"
            strokeWidth="8"
          />
          <circle
            cx="50"
            cy="50"
            r="40"
            fill="none"
            stroke={color}
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={`${pct * 2.51} ${251 - pct * 2.51}`}
          />
        </svg>
        <div className="absolute inset-0 flex items-center justify-center">
          <span className="text-2xl font-bold text-clay-100 font-[family-name:var(--font-mono)]">
            {Math.round(pct)}
          </span>
        </div>
      </div>
    </div>
  );
}

function getTier(score: number): { label: string; color: string } {
  if (score >= 80) return { label: "Hot", color: "bg-kiln-teal/15 text-kiln-teal border-kiln-teal/30" };
  if (score >= 60) return { label: "Warm", color: "bg-kiln-mustard/15 text-kiln-mustard border-kiln-mustard/30" };
  if (score >= 40) return { label: "Neutral", color: "bg-clay-800 text-clay-400 border-clay-700" };
  return { label: "Cold", color: "bg-kiln-coral/15 text-kiln-coral border-kiln-coral/30" };
}

export function ScoreResult({ data }: { data: Record<string, unknown> }) {
  const score =
    typeof data.score === "number"
      ? data.score
      : typeof data.icp_score === "number"
        ? data.icp_score
        : typeof data.total_score === "number"
          ? data.total_score
          : null;

  if (score === null) {
    return (
      <pre className="p-4 font-[family-name:var(--font-mono)] text-sm leading-relaxed text-clay-200">
        {JSON.stringify(data, null, 2)}
      </pre>
    );
  }

  const tier = getTier(score);

  // Look for dimension breakdown
  const dimensions =
    (data.dimensions as Record<string, unknown>) ||
    (data.scores as Record<string, unknown>) ||
    (data.breakdown as Record<string, unknown>) ||
    null;

  const reasoning = (data.reasoning as string) || (data.explanation as string) || "";

  return (
    <div className="p-4 space-y-4">
      <div className="flex items-center gap-2 text-clay-500">
        <Target className="h-4 w-4" />
        <span className="text-xs uppercase tracking-wider">ICP Score</span>
      </div>

      <div className="flex items-center gap-4">
        <ScoreGauge score={score} />
        <div>
          <Badge variant="outline" className={tier.color}>
            {tier.label}
          </Badge>
          {reasoning && (
            <p className="text-sm text-clay-400 mt-2 max-w-xs">{reasoning}</p>
          )}
        </div>
      </div>

      {/* Dimension breakdown */}
      {dimensions && (
        <div className="space-y-2">
          <p className="text-xs text-clay-500 uppercase tracking-wider">
            Breakdown
          </p>
          <div className="space-y-1.5">
            {Object.entries(dimensions).map(([key, val]) => {
              const numVal = typeof val === "number" ? val : 0;
              return (
                <div key={key} className="flex items-center gap-2">
                  <span className="text-xs text-clay-400 w-32 truncate capitalize">
                    {key.replace(/_/g, " ")}
                  </span>
                  <div className="flex-1 h-2 rounded-full bg-clay-800 overflow-hidden">
                    <div
                      className="h-full rounded-full bg-kiln-teal transition-all"
                      style={{ width: `${Math.min(100, numVal)}%` }}
                    />
                  </div>
                  <span className="text-xs text-clay-500 font-[family-name:var(--font-mono)] w-8 text-right">
                    {Math.round(numVal)}
                  </span>
                </div>
              );
            })}
          </div>
        </div>
      )}

      {/* Full JSON fallback */}
      <details className="group">
        <summary className="text-xs text-clay-500 cursor-pointer hover:text-clay-400">
          Show raw JSON
        </summary>
        <pre className="mt-2 text-xs text-clay-400 font-[family-name:var(--font-mono)] overflow-x-auto">
          {JSON.stringify(data, null, 2)}
        </pre>
      </details>
    </div>
  );
}
