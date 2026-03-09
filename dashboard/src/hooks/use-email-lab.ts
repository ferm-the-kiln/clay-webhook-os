"use client";

import { useState, useCallback, useEffect } from "react";
import {
  runWebhook,
  fetchSkillContent,
  updateSkillContent,
  fetchVariants,
  forkVariant,
  previewPrompt,
} from "@/lib/api";
import type { VariantDef, WebhookResponse } from "@/lib/types";
import type { Model } from "@/lib/constants";
import {
  EMAIL_LAB_TEMPLATES,
  STORAGE_KEY,
  CUSTOM_TEMPLATES_KEY,
  MAX_HISTORY,
  type EmailLabSkill,
  type EmailLabRun,
  type EmailLabTemplate,
  type CustomEmailLabTemplate,
} from "@/lib/email-lab-constants";

export type EditorTab = "data" | "instructions" | "skill";
export type EditorMode = "form" | "json";
export type InstructionMode = "builder" | "freeform";

export interface QualityCheckResult {
  passed: boolean;
  issues: { severity: "error" | "warning" | "info"; message: string }[];
}

export interface UseEmailLabReturn {
  // Template state
  selectedTemplate: EmailLabTemplate | null;
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

  // Skill state
  selectedSkill: EmailLabSkill;
  setSelectedSkill: (s: EmailLabSkill) => void;
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
  setResult: (r: WebhookResponse | null) => void;
  loading: boolean;
  error: string | null;
  runEmail: () => Promise<void>;
  currentRunId: string | null;

  // Inline editing
  isEditing: boolean;
  setIsEditing: (v: boolean) => void;
  editedBody: string;
  setEditedBody: (v: string) => void;
  saveEdits: () => void;

  // Quality gate
  autoQualityCheck: boolean;
  setAutoQualityCheck: (v: boolean) => void;
  qualityResult: QualityCheckResult | null;
  qualityLoading: boolean;

  // History
  history: EmailLabRun[];
  restoreRun: (run: EmailLabRun) => void;
  clearHistory: () => void;

  // Custom templates (Feature 4)
  customTemplates: CustomEmailLabTemplate[];
  saveAsTemplate: (name: string) => void;
  deleteCustomTemplate: (id: string) => void;

  // Subject regen (Feature 6)
  subjectAlts: string[];
  regenLoading: boolean;
  regenSubjectLines: () => Promise<void>;
  selectSubjectAlt: (alt: string) => void;
}

function loadHistory(): EmailLabRun[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveHistory(runs: EmailLabRun[]) {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(runs.slice(0, MAX_HISTORY)));
  } catch {
    // localStorage full — silently ignore
  }
}

function loadCustomTemplates(): CustomEmailLabTemplate[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = localStorage.getItem(CUSTOM_TEMPLATES_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}

function saveCustomTemplates(templates: CustomEmailLabTemplate[]) {
  try {
    localStorage.setItem(CUSTOM_TEMPLATES_KEY, JSON.stringify(templates));
  } catch {
    // localStorage full — silently ignore
  }
}

export function useEmailLab(): UseEmailLabReturn {
  // Template
  const [selectedTemplate, setSelectedTemplate] = useState<EmailLabTemplate | null>(
    EMAIL_LAB_TEMPLATES[0]
  );

  // Editor
  const [dataJson, setDataJson] = useState(
    JSON.stringify(EMAIL_LAB_TEMPLATES[0].data, null, 2)
  );
  const [instructions, setInstructions] = useState("");
  const [activeTab, setActiveTab] = useState<EditorTab>("data");

  // Skill
  const [selectedSkill, setSelectedSkillRaw] = useState<EmailLabSkill>("email-gen");
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
  const [history, setHistory] = useState<EmailLabRun[]>(loadHistory);

  // Current run ID (Feature 3 — inline feedback)
  const [currentRunId, setCurrentRunId] = useState<string | null>(null);

  // Custom templates (Feature 4)
  const [customTemplates, setCustomTemplates] = useState<CustomEmailLabTemplate[]>(loadCustomTemplates);

  // Editor mode (form vs json)
  const [editorMode, setEditorMode] = useState<EditorMode>("form");

  // Instruction mode (builder vs freeform)
  const [instructionMode, setInstructionMode] = useState<InstructionMode>("builder");

  // Inline editing
  const [isEditing, setIsEditing] = useState(false);
  const [editedBody, setEditedBody] = useState("");

  // Quality gate
  const [autoQualityCheck, setAutoQualityCheck] = useState(true);
  const [qualityResult, setQualityResult] = useState<QualityCheckResult | null>(null);
  const [qualityLoading, setQualityLoading] = useState(false);

  // Subject regen (Feature 6)
  const [subjectAlts, setSubjectAlts] = useState<string[]>([]);
  const [regenLoading, setRegenLoading] = useState(false);

  // Load skill content when skill changes
  const loadSkillContent = useCallback(async (skill: string) => {
    setSkillLoading(true);
    try {
      const { content } = await fetchSkillContent(skill);
      setSkillContent(content);
    } catch {
      setSkillContent("// Failed to load skill content");
    } finally {
      setSkillLoading(false);
    }
  }, []);

  // Load variants when skill changes
  const loadVariants = useCallback(async (skill: string) => {
    try {
      const { variants: v } = await fetchVariants(skill);
      setVariants(v);
    } catch {
      setVariants([]);
    }
  }, []);

  useEffect(() => {
    loadSkillContent(selectedSkill);
    loadVariants(selectedSkill);
    setSelectedVariant(null);
  }, [selectedSkill, loadSkillContent, loadVariants]);

  // Select template (checks both built-in and custom)
  const selectTemplate = useCallback((id: string) => {
    const tpl =
      EMAIL_LAB_TEMPLATES.find((t) => t.id === id) ??
      customTemplates.find((t) => t.id === id);
    if (!tpl) return;
    setSelectedTemplate(tpl);
    setDataJson(JSON.stringify(tpl.data, null, 2));
    setResult(null);
    setError(null);
  }, [customTemplates]);

  // Change skill (also reset variant)
  const setSelectedSkill = useCallback((s: EmailLabSkill) => {
    setSelectedSkillRaw(s);
    setSelectedVariant(null);
  }, []);

  // Run email
  const runEmail = useCallback(async () => {
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
        skill: selectedSkill,
        data: parsed,
        model: selectedModel,
      };
      if (instructions.trim()) {
        body.instructions = instructions.trim();
      }

      const res = await runWebhook(body);
      setResult(res);
      setSubjectAlts([]);
      setIsEditing(false);
      setQualityResult(null);

      // Auto quality gate check
      if (autoQualityCheck) {
        runQualityCheck(res);
      }

      // Save to history
      const runId = crypto.randomUUID();
      setCurrentRunId(runId);
      const run: EmailLabRun = {
        id: runId,
        templateId: selectedTemplate?.id ?? null,
        skill: selectedSkill,
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
  }, [dataJson, selectedSkill, selectedModel, instructions, selectedTemplate, selectedVariant]);

  // Quality gate check
  const runQualityCheck = useCallback(async (res: WebhookResponse) => {
    const emailBody = (res.body as string) || (res.email_body as string) || (res.email as string) || "";
    const emailSubject = (res.subject as string) || (res.subject_line as string) || "";
    if (!emailBody) return;

    setQualityLoading(true);
    try {
      const qgRes = await runWebhook({
        skill: "quality-gate",
        data: {
          email_subject: emailSubject,
          email_body: emailBody,
          first_name: "Prospect",
          company_name: "Company",
        },
        model: "haiku",
      });

      const issues: QualityCheckResult["issues"] = [];

      // Parse quality gate response
      const suggestions = (qgRes.suggestions ?? qgRes.issues ?? []) as Array<Record<string, string>>;
      if (Array.isArray(suggestions)) {
        for (const s of suggestions) {
          issues.push({
            severity: s.severity === "error" ? "error" : s.severity === "info" ? "info" : "warning",
            message: s.message ?? s.suggestion ?? String(s),
          });
        }
      }

      // Check word count
      const words = emailBody.trim().split(/\s+/).length;
      if (words > 125) {
        issues.push({ severity: "warning", message: `Too long — ${words} words, target 80-125` });
      } else if (words < 50) {
        issues.push({ severity: "warning", message: `Too short — ${words} words, target 50-125` });
      }

      // Check for common AI phrases
      const aiPhrases = ["I hope this finds you well", "I wanted to reach out", "I'd love to connect", "leverage", "synergy"];
      for (const phrase of aiPhrases) {
        if (emailBody.toLowerCase().includes(phrase.toLowerCase())) {
          issues.push({ severity: "warning", message: `Detected AI phrase: "${phrase}"` });
        }
      }

      const passed = qgRes.passed !== false && issues.filter((i) => i.severity === "error").length === 0;
      setQualityResult({ passed, issues });
    } catch {
      // Quality gate failed silently — don't block the user
      setQualityResult(null);
    } finally {
      setQualityLoading(false);
    }
  }, []);

  // Save inline edits
  const saveEdits = useCallback(() => {
    if (!result || !editedBody) return;
    const updated = { ...result, body: editedBody, email_body: editedBody, _edited: true };
    setResult(updated as WebhookResponse);
    setIsEditing(false);
  }, [result, editedBody]);

  // Save skill content
  const saveSkillContent = useCallback(async () => {
    try {
      await updateSkillContent(selectedSkill, skillContent);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to save skill");
    }
  }, [selectedSkill, skillContent]);

  // Fork skill
  const forkCurrentSkill = useCallback(async () => {
    try {
      const variant = await forkVariant(selectedSkill);
      setVariants((prev) => [...prev, variant]);
      setSelectedVariant(variant.id);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to fork skill");
    }
  }, [selectedSkill]);

  // Restore a run from history
  const restoreRun = useCallback((run: EmailLabRun) => {
    setDataJson(JSON.stringify(run.data, null, 2));
    setInstructions(run.instructions);
    setSelectedSkillRaw(run.skill);
    setSelectedModel(run.model as Model);
    setResult(run.result as WebhookResponse);
    setSelectedVariant(run.variantId);
    setSelectedTemplate(
      EMAIL_LAB_TEMPLATES.find((t) => t.id === run.templateId) ?? null
    );
    setCurrentRunId(run.id);
    setSubjectAlts([]);
  }, []);

  // Clear history
  const clearHistory = useCallback(() => {
    setHistory([]);
    saveHistory([]);
  }, []);

  // Save as custom template (Feature 4)
  const saveAsTemplate = useCallback(
    (name: string) => {
      let parsed: Record<string, unknown>;
      try {
        parsed = JSON.parse(dataJson);
      } catch {
        return;
      }
      const tpl: CustomEmailLabTemplate = {
        id: `custom-${crypto.randomUUID()}`,
        name,
        description: `Saved from ${selectedSkill}`,
        signalType: (parsed.signal_type as string) || "custom",
        data: parsed,
        isCustom: true,
        createdAt: Date.now(),
      };
      setCustomTemplates((prev) => {
        const next = [tpl, ...prev];
        saveCustomTemplates(next);
        return next;
      });
    },
    [dataJson, selectedSkill]
  );

  // Delete custom template (Feature 4)
  const deleteCustomTemplate = useCallback((id: string) => {
    setCustomTemplates((prev) => {
      const next = prev.filter((t) => t.id !== id);
      saveCustomTemplates(next);
      return next;
    });
  }, []);

  // Regen subject lines (Feature 6)
  const regenSubjectLines = useCallback(async () => {
    if (!result) return;
    setRegenLoading(true);
    setSubjectAlts([]);

    let parsed: Record<string, unknown>;
    try {
      parsed = JSON.parse(dataJson);
    } catch {
      setRegenLoading(false);
      return;
    }

    try {
      const res = await runWebhook({
        skill: selectedSkill,
        data: parsed,
        model: selectedModel,
        instructions:
          "Generate exactly 3 alternative subject lines for this email. Return JSON with keys: subject_line_1, subject_line_2, subject_line_3. Each should be a different angle or style. Nothing else.",
      });
      const alts: string[] = [];
      for (let i = 1; i <= 3; i++) {
        const key = `subject_line_${i}`;
        if (res[key]) alts.push(res[key] as string);
      }
      // Fallback: if the response has a subject, include it
      if (alts.length === 0 && res.subject) alts.push(res.subject as string);
      setSubjectAlts(alts);
    } catch {
      // silently fail
    } finally {
      setRegenLoading(false);
    }
  }, [result, dataJson, selectedSkill, selectedModel]);

  // Select a subject alt (Feature 6)
  const selectSubjectAlt = useCallback(
    (alt: string) => {
      if (!result) return;
      // Update result with new subject
      const updated = { ...result, subject: alt, subject_line: alt };
      setResult(updated as WebhookResponse);
      setSubjectAlts([]);
    },
    [result]
  );

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
    selectedSkill,
    setSelectedSkill,
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
    setResult,
    loading,
    error,
    runEmail,
    currentRunId,
    isEditing,
    setIsEditing,
    editedBody,
    setEditedBody,
    saveEdits,
    autoQualityCheck,
    setAutoQualityCheck,
    qualityResult,
    qualityLoading,
    history,
    restoreRun,
    clearHistory,
    customTemplates,
    saveAsTemplate,
    deleteCustomTemplate,
    subjectAlts,
    regenLoading,
    regenSubjectLines,
    selectSubjectAlt,
  };
}
