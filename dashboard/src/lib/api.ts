const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://clay.nomynoms.com";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      "X-API-Key": API_KEY,
      ...init?.headers,
    },
  });
  if (!res.ok) {
    throw new Error(`API ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

import type {
  BatchResponse,
  HealthResponse,
  Job,
  JobListItem,
  Stats,
  WebhookResponse,
} from "./types";

export function fetchHealth(): Promise<HealthResponse> {
  return apiFetch("/health");
}

export function fetchStats(): Promise<Stats> {
  return apiFetch("/stats");
}

export function fetchJobs(): Promise<{
  pending: number;
  total: number;
  jobs: JobListItem[];
}> {
  return apiFetch("/jobs");
}

export function fetchJob(id: string): Promise<Job> {
  return apiFetch(`/jobs/${id}`);
}

export function fetchSkills(): Promise<{ skills: string[] }> {
  return apiFetch("/skills");
}

export function runWebhook(body: {
  skill: string;
  data: Record<string, unknown>;
  model?: string;
  instructions?: string;
}): Promise<WebhookResponse> {
  return apiFetch("/webhook", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function runBatch(body: {
  skill: string;
  rows: Record<string, unknown>[];
  model?: string;
  instructions?: string;
}): Promise<BatchResponse> {
  return apiFetch("/batch", {
    method: "POST",
    body: JSON.stringify(body),
  });
}
