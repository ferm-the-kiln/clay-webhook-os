"use client";

import { useState, useCallback, useEffect } from "react";
import {
  runWebhook,
  fetchSkillContent,
  updateSkillContent,
  fetchVariants,
  forkVariant,
} from "@/lib/api";
import type { VariantDef, WebhookResponse } from "@/lib/types";
import type { Model } from "@/lib/constants";
import {
  SEQUENCE_LAB_TEMPLATES,
  STORAGE_KEY,
  MAX_HISTORY,
  type SequenceLabRun,
  type SequenceLabTemplate,
} from "@/lib/sequence-lab-constants";

export type EditorTab = "data" | "instructions" | "skill";
export type EditorMode = "form" | "json";
export type InstructionMode = "builder" | "freeform";

const SKILL = "sequence-writer" as const;

export interface UseSequenceLabReturn {
  // Template state
  selectedTemplate: SequenceLabTemplate | null;
  selectTemplate: (id: string) => void;

  // Editor state
  dataJson: string;
  setDataJson: (v: string) => void;
  instructions: string;
  setInstructions: (v: string) => void;
  activeTab: EditorTab;
  setActiveTab: (t: EditorTab) => void;

  // Editor mode (form vs json)
  editorMode: EditorMode;
  setEditorMode: (m: EditorMode) => void;

  // Instruction mode (builder vs freeform)
  instructionMode: InstructionMode;
  setInstructionMode: (m: InstructionMode) => void;

  // Skill state (fixed to sequence-writer)
  skillContent: string;
  setSkillContent: (v: string) => void;
  skillLoading: boolean;
  saveSkillContent: () => Promise<void>;

  // Variant state
  selectedVariant: string | null;
  setSelectedVariant: (id: string | null) => void;
  variants: VariantDef[];
  forkCurrentSkill: () => Promise<void>;

  // Model
  selectedModel: Model;
  setSelectedModel: (m: Model) => void;

  // Run state
  result: WebhookResponse | null;
  loading: boolean;
  error: string | null;
  runSequence: () => Promise<void>;

  // History
  history: SequenceLabRun[];
  restoreRun: (run: SequenceLabRun) => void;
  clearHistory: () => void;
}

function loadHistory(): SequenceLabRun[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveHistory(runs: SequenceLabRun[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(runs.slice(0, MAX_HISTORY)));
  } catch {
    // localStorage full — silently ignore
  }
}

export function useSequenceLab(): UseSequenceLabReturn {
  // Template
  const [selectedTemplate, setSelectedTemplate] = useState<SequenceLabTemplate | null>(
    SEQUENCE_LAB_TEMPLATES[0]
  );

  // Editor
  const [dataJson, setDataJson] = useState(
    JSON.stringify(SEQUENCE_LAB_TEMPLATES[0].data, null, 2)
  );
  const [instructions, setInstructions] = useState("");
  const [activeTab, setActiveTab] = useState<EditorTab>("data");

  // Editor mode (form vs json)
  const [editorMode, setEditorMode] = useState<EditorMode>("form");

  // Instruction mode (builder vs freeform)
  const [instructionMode, setInstructionMode] = useState<InstructionMode>("builder");

  // Skill (fixed to sequence-writer)
  const [skillContent, setSkillContent] = useState("");
  const [skillLoading, setSkillLoading] = useState(false);

  // Variants
  const [selectedVariant, setSelectedVariant] = useState<string | null>(null);
  const [variants, setVariants] = useState<VariantDef[]>([]);

  // Model
  const [selectedModel, setSelectedModel] = useState<Model>("sonnet");

  // Run state
  const [result, setResult] = useState<WebhookResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // History
  const [history, setHistory] = useState<SequenceLabRun[]>(loadHistory);

  // Load skill content on mount
  const loadSkillContent = useCallback(async () => {
    setSkillLoading(true);
    try {
      const { content } = await fetchSkillContent(SKILL);
      setSkillContent(content);
    } catch {
      setSkillContent("// Failed to load skill content");
    } finally {
      setSkillLoading(false);
    }
  }, []);

  // Load variants on mount
  const loadVariants = useCallback(async () => {
    try {
      const { variants: v } = await fetchVariants(SKILL);
      setVariants(v);
    } catch {
      setVariants([]);
    }
  }, []);

  useEffect(() => {
    loadSkillContent();
    loadVariants();
  }, [loadSkillContent, loadVariants]);

  // Select template
  const selectTemplate = useCallback((id: string) => {
    const tpl = SEQUENCE_LAB_TEMPLATES.find((t) => t.id === id);
    if (!tpl) return;
    setSelectedTemplate(tpl);
    setDataJson(JSON.stringify(tpl.data, null, 2));
    setResult(null);
    setError(null);
  }, []);

  // Run sequence
  const runSequence = useCallback(async () => {
    setLoading(true);
    setError(null);

    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(dataJson);
    } catch {
      setError("Invalid JSON in data editor");
      setLoading(false);
      return;
    }

    try {
      const body: Parameters<typeof runWebhook>[0] = {
        skill: SKILL,
        data: parsed,
        model: selectedModel,
      };
      if (instructions.trim()) {
        body.instructions = instructions.trim();
      }

      const res = await runWebhook(body);
      setResult(res);

      // Save to history
      const run: SequenceLabRun = {
        id: crypto.randomUUID(),
        templateId: selectedTemplate?.id ?? null,
        model: selectedModel,
        variantId: selectedVariant,
        data: parsed,
        instructions: instructions.trim(),
        result: res as Record<string, unknown>,
        durationMs: res._meta?.duration_ms ?? 0,
        timestamp: Date.now(),
      };
      setHistory((prev) => {
        const next = [run, ...prev].slice(0, MAX_HISTORY);
        saveHistory(next);
        return next;
      });
    } catch (e) {
      setError(e instanceof Error ? e.message : "Unknown error");
    } finally {
      setLoading(false);
    }
  }, [dataJson, selectedModel, instructions, selectedTemplate, selectedVariant]);

  // Save skill content
  const saveSkillContent = useCallback(async () => {
    try {
      await updateSkillContent(SKILL, skillContent);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save skill");
    }
  }, [skillContent]);

  // Fork skill
  const forkCurrentSkill = useCallback(async () => {
    try {
      const variant = await forkVariant(SKILL);
      setVariants((prev) => [...prev, variant]);
      setSelectedVariant(variant.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fork skill");
    }
  }, []);

  // Restore a run from history
  const restoreRun = useCallback((run: SequenceLabRun) => {
    setDataJson(JSON.stringify(run.data, null, 2));
    setInstructions(run.instructions);
    setSelectedModel(run.model as Model);
    setResult(run.result as WebhookResponse);
    setSelectedVariant(run.variantId);
    setSelectedTemplate(
      SEQUENCE_LAB_TEMPLATES.find((t) => t.id === run.templateId) ?? null
    );
  }, []);

  // Clear history
  const clearHistory = useCallback(() => {
    setHistory([]);
    saveHistory([]);
  }, []);

  return {
    selectedTemplate,
    selectTemplate,
    dataJson,
    setDataJson,
    instructions,
    setInstructions,
    activeTab,
    setActiveTab,
    editorMode,
    setEditorMode,
    instructionMode,
    setInstructionMode,
    skillContent,
    setSkillContent,
    skillLoading,
    saveSkillContent,
    selectedVariant,
    setSelectedVariant,
    variants,
    forkCurrentSkill,
    selectedModel,
    setSelectedModel,
    result,
    loading,
    error,
    runSequence,
    history,
    restoreRun,
    clearHistory,
  };
}
