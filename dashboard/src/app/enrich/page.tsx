"use client";

import { useState, useCallback, useMemo } from "react";
import { ArrowLeft, ArrowRight, Zap } from "lucide-react";
import { Button } from "@/components/ui/button";
import { cn } from "@/lib/utils";
import { WORKFLOW_TEMPLATES } from "@/components/templates/template-data";
import { StepUpload, type CsvPreview } from "@/components/enrich/step-upload";
import { StepRecipes } from "@/components/enrich/step-recipes";
import { StepMapColumns } from "@/components/enrich/step-map-columns";
import { StepProgress } from "@/components/enrich/step-progress";
import type { WorkflowTemplate } from "@/lib/types";

type Step = "upload" | "recipes" | "map" | "run";

const STEPS: { key: Step; label: string }[] = [
  { key: "upload", label: "Upload" },
  { key: "recipes", label: "Enrich" },
  { key: "map", label: "Map" },
  { key: "run", label: "Run" },
];

export default function EnrichPage() {
  const [step, setStep] = useState<Step>("upload");
  const [csvPreview, setCsvPreview] = useState<CsvPreview | null>(null);
  const [selectedRecipeIds, setSelectedRecipeIds] = useState<Set<string>>(new Set());
  const [columnMapping, setColumnMapping] = useState<Record<string, string>>({});
  const [allRequiredMapped, setAllRequiredMapped] = useState(false);

  const selectedRecipes: WorkflowTemplate[] = useMemo(
    () => WORKFLOW_TEMPLATES.filter((t) => selectedRecipeIds.has(t.id)),
    [selectedRecipeIds],
  );

  const handleToggleRecipe = useCallback((id: string) => {
    setSelectedRecipeIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleMappingChange = useCallback(
    (mapping: Record<string, string>, requiredMet: boolean) => {
      setColumnMapping(mapping);
      setAllRequiredMapped(requiredMet);
    },
    [],
  );

  const handleStartOver = useCallback(() => {
    setCsvPreview(null);
    setSelectedRecipeIds(new Set());
    setColumnMapping({});
    setAllRequiredMapped(false);
    setStep("upload");
  }, []);

  // Can advance to next step?
  const canAdvance: Record<Step, boolean> = {
    upload: !!csvPreview,
    recipes: selectedRecipeIds.size > 0,
    map: allRequiredMapped,
    run: false, // no next step
  };

  const stepIdx = STEPS.findIndex((s) => s.key === step);

  const goNext = () => {
    const next = STEPS[stepIdx + 1];
    if (next) setStep(next.key);
  };

  const goBack = () => {
    const prev = STEPS[stepIdx - 1];
    if (prev) setStep(prev.key);
  };

  return (
    <div className="flex flex-col h-full">
      {/* Top bar with step indicators */}
      <div className="border-b border-clay-700 bg-clay-800/50 px-6 py-4">
        <div className="max-w-2xl mx-auto">
          <div className="flex items-center justify-between mb-4">
            <h1 className="text-base font-semibold text-clay-100 flex items-center gap-2">
              <Zap className="h-4 w-4 text-kiln-teal" />
              Quick Enrich
            </h1>
          </div>

          {/* Step indicator pills */}
          <div className="flex items-center gap-2">
            {STEPS.map((s, i) => (
              <div key={s.key} className="flex items-center gap-2">
                <div
                  className={cn(
                    "flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-medium transition-colors",
                    i === stepIdx
                      ? "bg-kiln-teal/15 text-kiln-teal"
                      : i < stepIdx
                        ? "bg-clay-700 text-clay-300"
                        : "bg-clay-800 text-clay-500",
                  )}
                >
                  <span className="w-4 h-4 flex items-center justify-center rounded-full text-[10px] bg-current/10">
                    {i + 1}
                  </span>
                  {s.label}
                </div>
                {i < STEPS.length - 1 && (
                  <div className={cn(
                    "w-6 h-px",
                    i < stepIdx ? "bg-kiln-teal/30" : "bg-clay-700",
                  )} />
                )}
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Step content */}
      <div className="flex-1 overflow-y-auto py-8 px-6">
        <div className="max-w-2xl mx-auto">
          {step === "upload" && (
            <StepUpload
              preview={csvPreview}
              onParsed={setCsvPreview}
              onClear={() => setCsvPreview(null)}
            />
          )}

          {step === "recipes" && (
            <StepRecipes
              recipes={WORKFLOW_TEMPLATES}
              selected={selectedRecipeIds}
              onToggle={handleToggleRecipe}
            />
          )}

          {step === "map" && csvPreview && (
            <StepMapColumns
              csvHeaders={csvPreview.headers}
              selectedRecipes={selectedRecipes}
              onMappingChange={handleMappingChange}
            />
          )}

          {step === "run" && csvPreview && (
            <StepProgress
              csvPreview={csvPreview}
              selectedRecipes={selectedRecipes}
              columnMapping={columnMapping}
              onStartOver={handleStartOver}
            />
          )}
        </div>
      </div>

      {/* Bottom navigation bar (hidden during run step) */}
      {step !== "run" && (
        <div className="border-t border-clay-700 bg-clay-800/50 px-6 py-3">
          <div className="max-w-2xl mx-auto flex items-center justify-between">
            <div>
              {stepIdx > 0 && (
                <Button
                  variant="ghost"
                  size="sm"
                  className="text-clay-400 hover:text-clay-200"
                  onClick={goBack}
                >
                  <ArrowLeft className="h-4 w-4 mr-1" />
                  Back
                </Button>
              )}
            </div>

            <Button
              size="sm"
              className={cn(
                "h-9 px-6",
                step === "map"
                  ? "bg-kiln-teal text-black hover:bg-kiln-teal/90"
                  : "bg-clay-600 text-clay-100 hover:bg-clay-500",
              )}
              disabled={!canAdvance[step]}
              onClick={goNext}
            >
              {step === "map" ? (
                <>
                  <Zap className="h-4 w-4 mr-1" />
                  Run Enrichment
                </>
              ) : (
                <>
                  Next
                  <ArrowRight className="h-4 w-4 ml-1" />
                </>
              )}
            </Button>
          </div>
        </div>
      )}
    </div>
  );
}
