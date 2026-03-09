"use client";

import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { EditorPane } from "@/components/editor/editor-pane";
import { Play, Loader2, Save, Cpu, Code, FormInput } from "lucide-react";
import type { EditorTab, EditorMode, InstructionMode } from "@/hooks/use-email-lab";
import { INSTRUCTION_PRESETS } from "@/lib/email-lab-constants";
import { FormEditor } from "@/components/shared/form-editor";
import { InstructionBuilder } from "@/components/shared/instruction-builder";
import { PromptPreviewButton } from "@/components/shared/prompt-preview-modal";

const TABS: { id: EditorTab; label: string }[] = [
  { id: "data", label: "Data" },
  { id: "instructions", label: "Instructions" },
  { id: "skill", label: "Skill Prompt" },
];

export function DataEditorPanel({
  activeTab,
  onTabChange,
  dataJson,
  onDataChange,
  instructions,
  onInstructionsChange,
  skillContent,
  onSkillContentChange,
  skillLoading,
  onSaveSkill,
  onRun,
  loading,
  selectedModel,
  editorMode = "form",
  onEditorModeChange,
  instructionMode = "builder",
  onInstructionModeChange,
  skill = "email-gen",
  isSequenceLab = false,
}: {
  activeTab: EditorTab;
  onTabChange: (t: EditorTab) => void;
  dataJson: string;
  onDataChange: (v: string) => void;
  instructions: string;
  onInstructionsChange: (v: string) => void;
  skillContent: string;
  onSkillContentChange: (v: string) => void;
  skillLoading: boolean;
  onSaveSkill: () => void;
  onRun: () => void;
  loading: boolean;
  selectedModel: string;
  editorMode?: EditorMode;
  onEditorModeChange?: (m: EditorMode) => void;
  instructionMode?: InstructionMode;
  onInstructionModeChange?: (m: InstructionMode) => void;
  skill?: string;
  isSequenceLab?: boolean;
}) {
  // Validate JSON for visual feedback
  let jsonValid = true;
  try {
    JSON.parse(dataJson);
  } catch {
    jsonValid = false;
  }

  return (
    <div className="flex flex-col h-full">
      {/* Tab bar */}
      <div className="flex items-center gap-1 px-3 pt-3 pb-2 border-b border-clay-700">
        {TABS.map((tab) => (
          <button
            key={tab.id}
            onClick={() => onTabChange(tab.id)}
            className={cn(
              "px-3 py-1.5 text-xs font-medium rounded-md transition-colors",
              activeTab === tab.id
                ? "bg-clay-700 text-clay-100"
                : "text-clay-300 hover:text-clay-200 hover:bg-clay-800"
            )}
          >
            {tab.label}
          </button>
        ))}

        {/* Save button for skill tab */}
        {activeTab === "skill" && (
          <div className="ml-auto flex items-center gap-1">
            <PromptPreviewButton skill={skill} dataJson={dataJson} />
            <Button
              variant="ghost"
              size="sm"
              onClick={onSaveSkill}
              className="text-xs text-clay-300 hover:text-kiln-teal h-7"
            >
              <Save className="h-3.5 w-3.5 mr-1" />
              Save
              <kbd className="ml-1.5 text-[10px] text-clay-300 bg-clay-800 px-1 rounded">
                {"\u2318"}S
              </kbd>
            </Button>
          </div>
        )}

        {/* Data tab: Form/JSON toggle + validity */}
        {activeTab === "data" && (
          <div className="ml-auto flex items-center gap-2">
            {onEditorModeChange && (
              <div className="flex items-center bg-clay-800 rounded-md p-0.5">
                <button
                  onClick={() => onEditorModeChange("form")}
                  className={cn(
                    "flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium transition-colors",
                    editorMode === "form"
                      ? "bg-clay-700 text-clay-100"
                      : "text-clay-400 hover:text-clay-200"
                  )}
                >
                  <FormInput className="h-3 w-3" />
                  Form
                </button>
                <button
                  onClick={() => onEditorModeChange("json")}
                  className={cn(
                    "flex items-center gap-1 px-2 py-1 rounded text-[10px] font-medium transition-colors",
                    editorMode === "json"
                      ? "bg-clay-700 text-clay-100"
                      : "text-clay-400 hover:text-clay-200"
                  )}
                >
                  <Code className="h-3 w-3" />
                  JSON
                </button>
              </div>
            )}
            {editorMode === "json" && (
              <div className="flex items-center gap-1.5">
                <span
                  className={cn(
                    "h-1.5 w-1.5 rounded-full",
                    jsonValid ? "bg-emerald-400" : "bg-red-400"
                  )}
                />
                <span className="text-[10px] text-clay-300">
                  {jsonValid ? "Valid JSON" : "Invalid JSON"}
                </span>
              </div>
            )}
          </div>
        )}

        {/* Instructions tab: Builder/Freeform toggle */}
        {activeTab === "instructions" && onInstructionModeChange && (
          <div className="ml-auto flex items-center gap-2">
            <div className="flex items-center bg-clay-800 rounded-md p-0.5">
              <button
                onClick={() => onInstructionModeChange("builder")}
                className={cn(
                  "px-2 py-1 rounded text-[10px] font-medium transition-colors",
                  instructionMode === "builder"
                    ? "bg-clay-700 text-clay-100"
                    : "text-clay-400 hover:text-clay-200"
                )}
              >
                Builder
              </button>
              <button
                onClick={() => onInstructionModeChange("freeform")}
                className={cn(
                  "px-2 py-1 rounded text-[10px] font-medium transition-colors",
                  instructionMode === "freeform"
                    ? "bg-clay-700 text-clay-100"
                    : "text-clay-400 hover:text-clay-200"
                )}
              >
                Freeform
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Editor area */}
      <div className="flex-1 overflow-hidden p-3">
        {activeTab === "data" && editorMode === "form" && (
          <FormEditor
            dataJson={dataJson}
            onDataChange={onDataChange}
            skill={skill}
            isSequenceLab={isSequenceLab}
          />
        )}

        {activeTab === "data" && editorMode === "json" && (
          <div className="h-full">
            <textarea
              value={dataJson}
              onChange={(e) => onDataChange(e.target.value)}
              spellCheck={false}
              className={cn(
                "w-full h-full resize-none bg-clay-950 border rounded-lg p-4 text-sm text-clay-200 font-[family-name:var(--font-mono)] leading-relaxed outline-none",
                jsonValid
                  ? "border-clay-700 focus:border-kiln-teal/50"
                  : "border-red-500/50 focus:border-red-400"
              )}
              placeholder='{\n  "first_name": "...",\n  "company_name": "..."\n}'
            />
          </div>
        )}

        {activeTab === "instructions" && instructionMode === "builder" && (
          <InstructionBuilder
            instructions={instructions}
            onInstructionsChange={onInstructionsChange}
          />
        )}

        {activeTab === "instructions" && instructionMode === "freeform" && (
          <div className="flex flex-col h-full gap-2">
            {/* Instruction preset chips */}
            <div className="flex flex-wrap gap-1.5 shrink-0">
              {INSTRUCTION_PRESETS.map((preset) => (
                <button
                  key={preset.label}
                  onClick={() => {
                    const sep = instructions.trim() ? "\n" : "";
                    onInstructionsChange(instructions.trim() + sep + preset.text);
                  }}
                  className="text-[11px] px-2.5 py-1 rounded-full border border-clay-600 text-clay-300 hover:text-kiln-teal hover:border-kiln-teal/30 transition-colors"
                >
                  {preset.label}
                </button>
              ))}
            </div>
            <textarea
              value={instructions}
              onChange={(e) => onInstructionsChange(e.target.value)}
              spellCheck={false}
              className="w-full flex-1 resize-none bg-clay-950 border border-clay-700 rounded-lg p-4 text-sm text-clay-200 leading-relaxed outline-none focus:border-kiln-teal/50"
              placeholder="Optional campaign overrides... e.g. 'Keep under 80 words, focus on the funding signal, use a question-based opener'"
            />
          </div>
        )}

        {activeTab === "skill" && (
          <div className="h-full">
            {skillLoading ? (
              <div className="h-full flex items-center justify-center text-clay-300">
                <Loader2 className="h-5 w-5 animate-spin" />
              </div>
            ) : (
              <EditorPane
                content={skillContent}
                onChange={onSkillContentChange}
              />
            )}
          </div>
        )}
      </div>

      {/* Run button */}
      <div className="px-3 pb-3 pt-1">
        <Button
          onClick={onRun}
          disabled={loading || (activeTab === "data" && editorMode === "json" && !jsonValid)}
          className="w-full bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light font-semibold h-10 disabled:opacity-50"
        >
          {loading ? (
            <>
              <Loader2 className="h-4 w-4 mr-2 animate-spin" />
              Running...
            </>
          ) : (
            <>
              <Play className="h-4 w-4 mr-2" />
              Run
              <span className="ml-2 flex items-center gap-1 text-clay-950/60">
                <Cpu className="h-3 w-3" />
                {selectedModel}
              </span>
              <kbd className="ml-2 text-[10px] bg-clay-950/20 px-1.5 py-0.5 rounded">
                {"\u2318\u21A9"}
              </kbd>
            </>
          )}
        </Button>
      </div>
    </div>
  );
}
