"use client";

import { useState, useCallback, useRef } from "react";
import { searchResearchMemory, runWebhook } from "@/lib/api";
import type { MemoryEntryResponse, WebhookResponse } from "@/lib/types";

export type EntityType = "company" | "person";
export type SkillStatus = "idle" | "loading" | "done" | "error";
export type ResearchPhase = "idle" | "loading" | "cached" | "results" | "error";

interface SkillState {
  status: SkillStatus;
  data: WebhookResponse | null;
  error: string | null;
}

const COMPANY_SKILLS = [
  "company-research",
  "people-research",
  "account-researcher",
  "company-qualifier",
] as const;

const PERSON_SKILLS = ["people-research", "account-researcher"] as const;

const HISTORY_KEY = "kiln_research_history";
const MAX_HISTORY = 10;

export interface ResearchHistoryEntry {
  query: string;
  entityType: EntityType;
  timestamp: number;
}

function detectEntityType(query: string): EntityType {
  const trimmed = query.trim();
  if (trimmed.includes("@")) return "person";
  if (trimmed.includes(".") && !trimmed.includes(" ")) return "company";
  // Two words with no dots = likely a person name
  const words = trimmed.split(/\s+/);
  if (words.length === 2 && !trimmed.includes(".")) return "person";
  return "company";
}

function buildSkillData(
  query: string,
  entityType: EntityType
): Record<string, unknown> {
  const trimmed = query.trim();
  if (entityType === "person") {
    if (trimmed.includes("@")) {
      return { email: trimmed };
    }
    const parts = trimmed.split(/\s+/);
    return {
      first_name: parts[0],
      last_name: parts.slice(1).join(" "),
    };
  }
  // Company
  if (trimmed.includes(".") && !trimmed.includes(" ")) {
    return { company_domain: trimmed, company_name: trimmed.split(".")[0] };
  }
  return { company_name: trimmed };
}

export function useResearch() {
  const [query, setQuery] = useState("");
  const [entityType, setEntityType] = useState<EntityType | null>(null);
  const [phase, setPhase] = useState<ResearchPhase>("idle");
  const [cachedEntries, setCachedEntries] = useState<MemoryEntryResponse[]>([]);
  const [cacheAge, setCacheAge] = useState<number | null>(null);
  const [skillStates, setSkillStates] = useState<Record<string, SkillState>>({});
  const [globalError, setGlobalError] = useState<string | null>(null);
  const abortRef = useRef<AbortController | null>(null);

  const updateSkill = useCallback(
    (skill: string, update: Partial<SkillState>) => {
      setSkillStates((prev) => ({
        ...prev,
        [skill]: { ...prev[skill], ...update },
      }));
    },
    []
  );

  const runSkills = useCallback(
    async (searchQuery: string, detected: EntityType) => {
      const skills =
        detected === "company" ? COMPANY_SKILLS : PERSON_SKILLS;
      const data = buildSkillData(searchQuery, detected);

      // Initialize skill states
      const initial: Record<string, SkillState> = {};
      for (const s of skills) {
        initial[s] = { status: "loading", data: null, error: null };
      }
      setSkillStates(initial);
      setPhase("loading");

      const controller = new AbortController();
      abortRef.current = controller;

      const promises = skills.map(async (skill) => {
        try {
          const result = await runWebhook({
            skill,
            data,
            priority: "high",
          });
          if (!controller.signal.aborted) {
            updateSkill(skill, { status: "done", data: result });
          }
        } catch (e) {
          if (!controller.signal.aborted) {
            updateSkill(skill, {
              status: "error",
              error: e instanceof Error ? e.message : "Failed",
            });
          }
        }
      });

      await Promise.allSettled(promises);
      if (!controller.signal.aborted) {
        setPhase("results");
      }
      abortRef.current = null;
    },
    [updateSkill]
  );

  const search = useCallback(
    async (searchQuery: string) => {
      const trimmed = searchQuery.trim();
      if (!trimmed) return;

      // Cancel any in-flight requests
      abortRef.current?.abort();

      setQuery(trimmed);
      setGlobalError(null);
      setCachedEntries([]);
      setCacheAge(null);

      const detected = detectEntityType(trimmed);
      setEntityType(detected);
      setPhase("loading");

      // Check cache first
      try {
        const cached = await searchResearchMemory(trimmed);
        if (cached.found && cached.entries.length > 0) {
          setCachedEntries(cached.entries);
          const newest = Math.max(...cached.entries.map((e) => e.timestamp));
          setCacheAge(Date.now() - newest * 1000);
          setPhase("cached");
          // Still save to history
          saveHistory(trimmed, detected);
          return;
        }
      } catch {
        // Cache miss or error — proceed to run skills
      }

      saveHistory(trimmed, detected);
      await runSkills(trimmed, detected);
    },
    [runSkills]
  );

  const refresh = useCallback(async () => {
    if (!query || !entityType) return;
    setCachedEntries([]);
    setCacheAge(null);
    await runSkills(query, entityType);
  }, [query, entityType, runSkills]);

  const retrySingle = useCallback(
    async (skill: string) => {
      if (!query || !entityType) return;
      const data = buildSkillData(query, entityType);
      updateSkill(skill, { status: "loading", error: null });
      try {
        const result = await runWebhook({ skill, data, priority: "high" });
        updateSkill(skill, { status: "done", data: result });
      } catch (e) {
        updateSkill(skill, {
          status: "error",
          error: e instanceof Error ? e.message : "Failed",
        });
      }
    },
    [query, entityType, updateSkill]
  );

  const clear = useCallback(() => {
    abortRef.current?.abort();
    setQuery("");
    setEntityType(null);
    setPhase("idle");
    setCachedEntries([]);
    setCacheAge(null);
    setSkillStates({});
    setGlobalError(null);
  }, []);

  return {
    query,
    entityType,
    phase,
    cachedEntries,
    cacheAge,
    skillStates,
    globalError,
    search,
    refresh,
    retrySingle,
    clear,
    detectEntityType,
  };
}

function saveHistory(query: string, entityType: EntityType) {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    const history: ResearchHistoryEntry[] = raw ? JSON.parse(raw) : [];
    const filtered = history.filter(
      (h) => h.query.toLowerCase() !== query.toLowerCase()
    );
    filtered.unshift({ query, entityType, timestamp: Date.now() });
    localStorage.setItem(
      HISTORY_KEY,
      JSON.stringify(filtered.slice(0, MAX_HISTORY))
    );
  } catch {
    // localStorage unavailable
  }
}

export function getResearchHistory(): ResearchHistoryEntry[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}
