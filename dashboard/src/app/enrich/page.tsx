"use client";

import { useState, useCallback, useMemo, useEffect } from "react";
import { AnimatePresence, motion } from "framer-motion";
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
  const [direction, setDirection] = useState(0);
  const [csvPreview, setCsvPreview] = useState<CsvPreview | null>(null);
  const [selectedRecipeIds, setSelectedRecipeIds] = useState<Set<string>>(new Set());
  const [columnMapping, setColumnMapping] = useState<Record<string, string>>({});
  const [allRequiredMapped, setAllRequiredMapped] = useState(false);
  const [rowLimit, setRowLimit] = useState<number | undefined>(undefined);

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
    setRowLimit(undefined);
    setStep("upload");
  }, []);

  const canAdvance: Record<Step, boolean> = {
    upload: !!csvPreview,
    recipes: selectedRecipeIds.size > 0,
    map: allRequiredMapped,
    run: false,
  };

  const stepIdx = STEPS.findIndex((s) => s.key === step);

  const goNext = useCallback(() => {
    const next = STEPS[stepIdx + 1];
    if (next) {
      setDirection(1);
      setStep(next.key);
    }
  }, [stepIdx]);

  const goBack = useCallback(() => {
    const prev = STEPS[stepIdx - 1];
    if (prev) {
      setDirection(-1);
      setStep(prev.key);
    }
  }, [stepIdx]);

  // Keyboard navigation
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      const tag = (e.target as HTMLElement)?.tagName;
      if (tag === "INPUT" || tag === "TEXTAREA" || tag === "SELECT") return;

      if (e.key === "Enter" && canAdvance[step]) {
        e.preventDefault();
        goNext();
      }
      if (e.key === "Escape" && stepIdx > 0 && step !== "run") {
        e.preventDefault();
        goBack();
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [canAdvance, step, stepIdx, goNext, goBack]);

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

      {/* Step content with animated transitions */}
      <div className="flex-1 overflow-y-auto py-8 px-6">
        <AnimatePresence mode="wait" initial={false}>
          <motion.div
            key={step}
            initial={{ opacity: 0, x: direction * 30 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: direction * -30 }}
            transition={{ duration: 0.2, ease: "easeInOut" }}
            className="max-w-2xl mx-auto"
          >
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
                csvHeaders={csvPreview?.headers ?? []}
              />
            )}

            {step === "map" && csvPreview && (
              <StepMapColumns
                csvHeaders={csvPreview.headers}
                selectedRecipes={selectedRecipes}
                onMappingChange={handleMappingChange}
                totalRows={csvPreview.totalRows}
                limit={rowLimit}
                onLimitChange={setRowLimit}
              />
            )}

            {step === "run" && csvPreview && (
              <StepProgress
                csvPreview={csvPreview}
                selectedRecipes={selectedRecipes}
                columnMapping={columnMapping}
                onStartOver={handleStartOver}
                rowLimit={rowLimit}
              />
            )}
          </motion.div>
        </AnimatePresence>
      </div>

      {/* Bottom navigation bar */}
      {step !== "run" && (
        <div className="border-t border-clay-700 bg-clay-800/50 px-6 py-3">
          <div className="max-w-2xl mx-auto flex items-center justify-between">
            <div className="flex items-center">
              {stepIdx > 0 && (
                <>
                  <Button
                    variant="ghost"
                    size="sm"
                    className="text-clay-400 hover:text-clay-200"
                    onClick={goBack}
                  >
                    <ArrowLeft className="h-4 w-4 mr-1" />
                    Back
                  </Button>
                  <kbd className="retro-keycap text-[10px] ml-1">esc</kbd>
                </>
              )}
            </div>

            <div className="flex items-center">
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
              <kbd className="retro-keycap text-[10px] ml-2">enter</kbd>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
