"use client";

import { useEffect, useCallback } from "react";
import { useSequenceLab } from "@/hooks/use-sequence-lab";
import { SequenceTemplatePanel } from "./sequence-template-panel";
import { DataEditorPanel } from "@/components/email-lab/data-editor-panel";
import { SequencePreviewPanel } from "./sequence-preview-panel";

export function SequenceLabContent() {
  const lab = useSequenceLab();

  // Global keyboard shortcuts
  const handleKeyDown = useCallback(
    (e: KeyboardEvent) => {
      // Cmd+Enter → Run
      if ((e.metaKey || e.ctrlKey) && e.key === "Enter") {
        e.preventDefault();
        if (!lab.loading) lab.runSequence();
      }
      // Cmd+S → Save skill (when on skill tab)
      if ((e.metaKey || e.ctrlKey) && e.key === "s") {
        if (lab.activeTab === "skill") {
          e.preventDefault();
          lab.saveSkillContent();
        }
      }
    },
    [lab]
  );

  useEffect(() => {
    document.addEventListener("keydown", handleKeyDown);
    return () => document.removeEventListener("keydown", handleKeyDown);
  }, [handleKeyDown]);

  return (
    <div className="flex h-full min-h-0">
      {/* Left panel — Templates & Sequence Type */}
      <div className="w-64 shrink-0 border-r border-clay-700 hidden lg:block">
        <SequenceTemplatePanel
          selectedTemplateId={lab.selectedTemplate?.id ?? null}
          onSelectTemplate={lab.selectTemplate}
          selectedModel={lab.selectedModel}
          onSelectModel={lab.setSelectedModel}
          variants={lab.variants}
          selectedVariant={lab.selectedVariant}
          onSelectVariant={lab.setSelectedVariant}
          onFork={lab.forkCurrentSkill}
          dataJson={lab.dataJson}
          onDataChange={lab.setDataJson}
        />
      </div>

      {/* Center panel — Data Editor (reused from email-lab) */}
      <div className="flex-1 min-w-0 border-r border-clay-700">
        <DataEditorPanel
          activeTab={lab.activeTab}
          onTabChange={lab.setActiveTab}
          dataJson={lab.dataJson}
          onDataChange={lab.setDataJson}
          instructions={lab.instructions}
          onInstructionsChange={lab.setInstructions}
          skillContent={lab.skillContent}
          onSkillContentChange={lab.setSkillContent}
          skillLoading={lab.skillLoading}
          onSaveSkill={lab.saveSkillContent}
          onRun={lab.runSequence}
          loading={lab.loading}
          selectedModel={lab.selectedModel}
        />
      </div>

      {/* Right panel — Sequence Preview */}
      <div className="w-80 xl:w-96 shrink-0 hidden md:block">
        <SequencePreviewPanel
          result={lab.result}
          loading={lab.loading}
          error={lab.error}
          history={lab.history}
          onRestore={lab.restoreRun}
          onClearHistory={lab.clearHistory}
        />
      </div>
    </div>
  );
}
