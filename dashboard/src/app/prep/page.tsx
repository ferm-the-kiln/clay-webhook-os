"use client";

import { useState, useCallback, useRef } from "react";
import { Header } from "@/components/layout/header";
import { PrepInputForm } from "@/components/prep/prep-input-form";
import { PrepSkillStatus } from "@/components/prep/prep-skill-status";
import { PrepBrief } from "@/components/prep/prep-brief";
import { runWebhook } from "@/lib/api";
import { toast } from "sonner";
import {
  PREP_SKILLS,
  savePrepHistory,
  type PrepInputs,
  type PrepSkillKey,
  type SkillResultState,
} from "@/lib/prep-types";

type Phase = "input" | "running" | "complete";

export default function PrepPage() {
  const [phase, setPhase] = useState<Phase>("input");
  const [inputs, setInputs] = useState<PrepInputs | null>(null);
  const [skillStates, setSkillStates] = useState<
    Record<PrepSkillKey, SkillResultState>
  >({} as Record<PrepSkillKey, SkillResultState>);
  const abortRef = useRef<AbortController | null>(null);

  const updateSkill = useCallback(
    (skill: PrepSkillKey, update: Partial<SkillResultState>) => {
      setSkillStates((prev) => ({
        ...prev,
        [skill]: { ...prev[skill], ...update },
      }));
    },
    []
  );

  const buildData = useCallback((inp: PrepInputs) => {
    const data: Record<string, unknown> = {
      company_name: inp.companyName,
    };
    if (inp.contactName) {
      const parts = inp.contactName.split(" ");
      data.first_name = parts[0];
      data.last_name = parts.slice(1).join(" ");
    }
    if (inp.contactTitle) data.title = inp.contactTitle;
    if (inp.clientSlug && inp.clientSlug !== "none") {
      data.client_slug = inp.clientSlug;
    }
    return data;
  }, []);

  const handleSubmit = useCallback(
    async (inp: PrepInputs) => {
      abortRef.current?.abort();
      setInputs(inp);
      setPhase("running");

      const initial = {} as Record<PrepSkillKey, SkillResultState>;
      for (const skill of PREP_SKILLS) {
        initial[skill] = {
          status: "running",
          data: null,
          error: null,
          startedAt: Date.now(),
          completedAt: null,
        };
      }
      setSkillStates(initial);

      const controller = new AbortController();
      abortRef.current = controller;
      const data = buildData(inp);

      const promises = PREP_SKILLS.map(async (skill) => {
        try {
          const result = await runWebhook({ skill, data, priority: "high" });
          if (!controller.signal.aborted) {
            updateSkill(skill, {
              status: "complete",
              data: result,
              completedAt: Date.now(),
            });
          }
          return { skill, result };
        } catch (e) {
          if (!controller.signal.aborted) {
            updateSkill(skill, {
              status: "error",
              error: e instanceof Error ? e.message : "Failed",
              completedAt: Date.now(),
            });
          }
          return { skill, error: e };
        }
      });

      const results = await Promise.allSettled(promises);

      if (!controller.signal.aborted) {
        setPhase("complete");

        // Count successes
        const succeeded = results.filter(
          (r) =>
            r.status === "fulfilled" &&
            (r.value as { result?: unknown }).result !== undefined
        ).length;
        const failed = PREP_SKILLS.length - succeeded;

        if (failed > 0 && succeeded > 0) {
          toast.warning(
            `${succeeded} of ${PREP_SKILLS.length} skills completed`
          );
        } else if (failed === PREP_SKILLS.length) {
          toast.error("All skills failed");
        }

        // Save to history
        const resultMap: Record<string, Record<string, unknown> | null> = {};
        for (const skill of PREP_SKILLS) {
          // Read from latest state via the settled results
          const settled = results.find(
            (r) =>
              r.status === "fulfilled" &&
              (r.value as { skill: string }).skill === skill
          );
          resultMap[skill] =
            settled?.status === "fulfilled"
              ? ((settled.value as { result?: Record<string, unknown> }).result ?? null)
              : null;
        }

        savePrepHistory({
          id: crypto.randomUUID(),
          inputs: inp,
          results: resultMap,
          timestamp: Date.now(),
          oneLiner:
            typeof resultMap["meeting-prep"]?.one_liner === "string"
              ? resultMap["meeting-prep"].one_liner
              : undefined,
        });
      }
    },
    [buildData, updateSkill]
  );

  const handleRetry = useCallback(
    async (skill: PrepSkillKey) => {
      if (!inputs) return;
      const data = buildData(inputs);
      updateSkill(skill, {
        status: "running",
        error: null,
        startedAt: Date.now(),
      });
      try {
        const result = await runWebhook({ skill, data, priority: "high" });
        updateSkill(skill, {
          status: "complete",
          data: result,
          completedAt: Date.now(),
        });
      } catch (e) {
        updateSkill(skill, {
          status: "error",
          error: e instanceof Error ? e.message : "Failed",
          completedAt: Date.now(),
        });
      }
    },
    [inputs, buildData, updateSkill]
  );

  const handleReset = useCallback(() => {
    abortRef.current?.abort();
    setPhase("input");
    setInputs(null);
    setSkillStates({} as Record<PrepSkillKey, SkillResultState>);
  }, []);

  return (
    <div className="flex flex-col h-full">
      <Header title="Prep" />
      <div className="flex-1 overflow-auto p-4 md:p-6 pb-20 md:pb-6">
        {phase === "input" && (
          <div className="flex items-start justify-center pt-8">
            <PrepInputForm onSubmit={handleSubmit} disabled={false} />
          </div>
        )}

        {(phase === "running" || phase === "complete") && inputs && (
          <div className="space-y-6 max-w-3xl mx-auto">
            <div className="print:hidden">
              <PrepSkillStatus skillStates={skillStates} />
            </div>
            <PrepBrief
              inputs={inputs}
              skillStates={skillStates}
              onRetry={handleRetry}
              onReset={handleReset}
            />
          </div>
        )}
      </div>
    </div>
  );
}
