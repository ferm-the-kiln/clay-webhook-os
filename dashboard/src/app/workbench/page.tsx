"use client";

import { Suspense } from "react";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Play } from "lucide-react";
import { useFunctionWorkbench } from "@/hooks/use-function-workbench";
import {
  FunctionSelector,
  FunctionInfoPanel,
  ColumnMappingPanel,
  ResultsPanel,
  CsvUploadZone,
  CsvPreviewTable,
  RunProgress,
} from "@/components/workbench-v2";

export default function WorkbenchPageWrapper() {
  return (
    <Suspense
      fallback={
        <div className="flex flex-col h-full">
          <Header title="Workbench" />
          <div className="flex-1 flex items-center justify-center text-clay-300">
            Loading...
          </div>
        </div>
      }
    >
      <WorkbenchPage />
    </Suspense>
  );
}

function WorkbenchPage() {
  const wb = useFunctionWorkbench();

  return (
    <div className="flex flex-col h-full">
      <Header title="Workbench" />
      <div className="flex-1 overflow-auto p-4 md:p-6 pb-20 md:pb-6">
        {/* Upload / Map phase */}
        {wb.step === "upload" && (
          <div className="space-y-6">
            <FunctionSelector
              functions={wb.functions}
              functionsByFolder={wb.functionsByFolder}
              selectedFunction={wb.selectedFunction}
              onSelect={wb.handleSelectFunction}
            />

            {wb.selectedFunction && (
              <FunctionInfoPanel func={wb.selectedFunction} />
            )}

            <CsvUploadZone
              csvData={wb.csvData}
              fileInputRef={wb.fileInputRef}
              onFileUpload={wb.handleFileUpload}
              onDrop={wb.handleDrop}
              onClear={wb.resetWorkbench}
            />

            {wb.csvData && (
              <CsvPreviewTable
                csvData={wb.csvData}
                detectColumnType={wb.detectColumnType}
              />
            )}

            {wb.csvData && wb.selectedFunction && (
              <ColumnMappingPanel
                func={wb.selectedFunction}
                csvHeaders={wb.csvData.headers}
                mappings={wb.mappings}
                autoMapConfidence={wb.autoMapConfidence}
                onMapColumn={wb.handleMapColumn}
                onClearMapping={wb.handleClearMapping}
              />
            )}

            {wb.canRun && (
              <div className="flex justify-end">
                <Button
                  onClick={wb.handleRun}
                  className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold"
                >
                  <Play className="h-4 w-4 mr-2" />
                  Run ({wb.csvData!.totalRows} rows)
                </Button>
              </div>
            )}
          </div>
        )}

        {/* Running phase */}
        {wb.step === "run" && wb.running && (
          <RunProgress done={wb.progress.done} total={wb.progress.total} />
        )}

        {/* Results phase */}
        {(wb.step === "results" || (wb.step === "run" && !wb.running)) &&
          wb.results.length > 0 &&
          wb.selectedFunction && (
            <ResultsPanel
              results={wb.results}
              displayResults={wb.getDisplayResults()}
              selectedFunction={wb.selectedFunction}
              mappings={wb.mappings}
              running={wb.running}
              statusFilter={wb.statusFilter}
              sortColumn={wb.sortColumn}
              sortDir={wb.sortDir}
              expandedCell={wb.expandedCell}
              expandedError={wb.expandedError}
              successRate={wb.successRate}
              doneCount={wb.doneCount}
              errorCount={wb.errorCount}
              onStatusFilterChange={wb.setStatusFilter}
              onSortColumnChange={wb.setSortColumn}
              onSortDirChange={wb.setSortDir}
              onExpandedCellChange={wb.setExpandedCell}
              onExpandedErrorChange={wb.setExpandedError}
              onRetryFailed={wb.handleRetryFailed}
              onExport={wb.handleExport}
              onNewRun={wb.resetWorkbench}
            />
          )}
      </div>
    </div>
  );
}
