export type PrepSkillKey =
  | "meeting-prep"
  | "discovery-questions"
  | "competitive-response"
  | "account-researcher"
  | "champion-enabler";

export const PREP_SKILLS: PrepSkillKey[] = [
  "meeting-prep",
  "discovery-questions",
  "competitive-response",
  "account-researcher",
  "champion-enabler",
];

export const PREP_SKILL_LABELS: Record<PrepSkillKey, string> = {
  "meeting-prep": "Meeting Prep",
  "discovery-questions": "Questions",
  "competitive-response": "Competitive",
  "account-researcher": "Research",
  "champion-enabler": "Champion",
};

export interface PrepInputs {
  companyName: string;
  contactName: string;
  contactTitle: string;
  clientSlug: string;
}

export interface SkillResultState {
  status: "pending" | "running" | "complete" | "error";
  data: Record<string, unknown> | null;
  error: string | null;
  startedAt: number | null;
  completedAt: number | null;
}

export interface PrepHistoryEntry {
  id: string;
  inputs: PrepInputs;
  results: Record<string, Record<string, unknown> | null>;
  timestamp: number;
  oneLiner?: string;
}

const HISTORY_KEY = "kiln_prep_history";
const MAX_HISTORY = 20;

export function savePrepHistory(entry: PrepHistoryEntry) {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    const history: PrepHistoryEntry[] = raw ? JSON.parse(raw) : [];
    history.unshift(entry);
    localStorage.setItem(
      HISTORY_KEY,
      JSON.stringify(history.slice(0, MAX_HISTORY))
    );
  } catch {
    // localStorage unavailable
  }
}

export function getPrepHistory(): PrepHistoryEntry[] {
  try {
    const raw = localStorage.getItem(HISTORY_KEY);
    return raw ? JSON.parse(raw) : [];
  } catch {
    return [];
  }
}
