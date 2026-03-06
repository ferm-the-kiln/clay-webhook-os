"use client";

import { useState } from "react";
import { Header } from "@/components/layout/header";
import { SkillSelector } from "@/components/playground/skill-selector";
import { JsonEditor } from "@/components/playground/json-editor";
import { ModelSelector } from "@/components/playground/model-selector";
import { ResultViewer } from "@/components/playground/result-viewer";
import { SKILL_SAMPLES, type Model } from "@/lib/constants";
import { runWebhook } from "@/lib/api";
import type { WebhookResponse } from "@/lib/types";

export default function PlaygroundPage() {
  const [skill, setSkill] = useState("");
  const [json, setJson] = useState("{}");
  const [model, setModel] = useState<Model>("sonnet");
  const [result, setResult] = useState<WebhookResponse | null>(null);
  const [loading, setLoading] = useState(false);

  const handleSkillChange = (s: string) => {
    setSkill(s);
    if (SKILL_SAMPLES[s]) {
      setJson(JSON.stringify(SKILL_SAMPLES[s], null, 2));
    }
    setResult(null);
  };

  const handleRun = async () => {
    if (!skill) return;
    let data: Record<string, unknown>;
    try {
      data = JSON.parse(json);
    } catch {
      return;
    }

    setLoading(true);
    setResult(null);
    try {
      const res = await runWebhook({ skill, data, model });
      setResult(res);
    } catch (e) {
      setResult({
        error: true,
        error_message: (e as Error).message,
      });
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full">
      <Header title="Playground" />
      <div className="flex-1 overflow-auto p-6">
        <div className="grid grid-cols-2 gap-6 h-full">
          {/* Left: Input */}
          <div className="flex flex-col gap-4">
            <SkillSelector value={skill} onChange={handleSkillChange} />
            <JsonEditor value={json} onChange={setJson} />
            <ModelSelector value={model} onChange={setModel} />
            <button
              onClick={handleRun}
              disabled={!skill || loading}
              className="rounded-lg bg-teal-500 px-4 py-2.5 text-sm font-semibold text-zinc-950 hover:bg-teal-400 disabled:opacity-40 disabled:cursor-not-allowed transition-colors"
            >
              {loading ? "Processing..." : "Run"}
            </button>
          </div>

          {/* Right: Output */}
          <ResultViewer result={result} loading={loading} />
        </div>
      </div>
    </div>
  );
}
