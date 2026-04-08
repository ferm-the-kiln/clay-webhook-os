"use client";

import { useAnalyzer } from "@/hooks/use-analyzer";
import { Header } from "@/components/layout/header";
import { UploadPhase } from "./upload-phase";
import { ConfigurePhase } from "./configure-phase";
import { ResultsPhase } from "./results-phase";
import { Button } from "@/components/ui/button";
import { RotateCcw } from "lucide-react";

export function AnalyzePage() {
  const analyzer = useAnalyzer();

  return (
    <div className="flex flex-col h-full">
      <Header
        title="Analyze"
        breadcrumbs={[{ label: "Analyze" }]}
      />

      {/* Phase indicator */}
      <div className="flex items-center justify-between px-4 md:px-6 py-3 border-b border-clay-700">
        <div className="flex items-center gap-1">
        {(["upload", "configure", "results"] as const).map((phase, i) => (
          <div key={phase} className="flex items-center gap-1">
            {i > 0 && <span className="text-clay-300 mx-1">/</span>}
            <button
              onClick={() => {
                if (phase === "upload") analyzer.reset();
                else if (phase === "configure" && analyzer.datasetId) analyzer.setPhase("configure");
                else if (phase === "results" && analyzer.currentAnalysis) analyzer.setPhase("results");
              }}
              disabled={
                (phase === "configure" && !analyzer.datasetId) ||
                (phase === "results" && !analyzer.currentAnalysis)
              }
              className={`text-xs px-2 py-1 rounded-md transition-colors ${
                analyzer.phase === phase
                  ? "bg-kiln-amber/10 text-kiln-amber font-medium"
                  : "text-clay-300 hover:text-clay-300 disabled:opacity-50 disabled:cursor-not-allowed"
              }`}
            >
              {phase === "upload" ? "1. Upload" : phase === "configure" ? "2. Configure" : "3. Results"}
            </button>
          </div>
        ))}
        </div>
        {analyzer.phase !== "upload" && (
          <Button variant="ghost" size="sm" onClick={analyzer.reset} className="text-clay-300">
            <RotateCcw className="h-4 w-4 mr-1" /> Start Over
          </Button>
        )}
      </div>

      {/* Phase content */}
      <div className="flex-1 overflow-auto p-4 md:p-6 pb-20 md:pb-6">
        {analyzer.phase === "upload" && (
          <UploadPhase
            datasets={analyzer.datasets}
            onUpload={analyzer.uploadCsv}
            onSelectDataset={analyzer.selectExistingDataset}
            error={analyzer.error}
          />
        )}

        {analyzer.phase === "configure" && (
          <ConfigurePhase
            datasetName={analyzer.datasetName}
            rowCount={analyzer.rowCount}
            columns={analyzer.columns}
            analysisType={analyzer.analysisType}
            outcomeColumn={analyzer.outcomeColumn}
            segmentColumns={analyzer.segmentColumns}
            businessContext={analyzer.businessContext}
            isRunning={analyzer.isRunning}
            analyses={analyzer.analyses}
            onConfigChange={analyzer.setAnalysisConfig}
            onRun={analyzer.runAnalysis}
            onViewAnalysis={analyzer.viewAnalysis}
          />
        )}

        {analyzer.phase === "results" && (
          <ResultsPhase
            analysis={analyzer.currentAnalysis}
            isRunning={analyzer.isRunning}
            onBack={() => analyzer.setPhase("configure")}
          />
        )}
      </div>
    </div>
  );
}
