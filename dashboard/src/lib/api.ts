import type {
  BatchResponse,
  BatchStatus,
  Destination,
  HealthResponse,
  Job,
  JobListItem,
  PushResult,
  ScheduledBatch,
  Stats,
  WebhookResponse,
} from "./types";

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
  skill?: string;
  skills?: string[];
  data: Record<string, unknown>;
  model?: string;
  instructions?: string;
  priority?: "high" | "normal" | "low";
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
  priority?: "high" | "normal" | "low";
  scheduled_at?: string;
}): Promise<BatchResponse> {
  return apiFetch("/batch", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchBatchStatus(batchId: string): Promise<BatchStatus> {
  return apiFetch(`/batch/${batchId}`);
}

export function fetchScheduledBatches(): Promise<{
  batches: ScheduledBatch[];
}> {
  return apiFetch("/scheduled");
}

// Destinations
export function fetchDestinations(): Promise<{ destinations: Destination[] }> {
  return apiFetch("/destinations");
}

export function createDestination(body: {
  name: string;
  type: string;
  url: string;
  auth_header_name?: string;
  auth_header_value?: string;
  client_slug?: string | null;
}): Promise<Destination> {
  return apiFetch("/destinations", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateDestination(
  id: string,
  body: Record<string, unknown>
): Promise<Destination> {
  return apiFetch(`/destinations/${id}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function deleteDestination(id: string): Promise<{ ok: boolean }> {
  return apiFetch(`/destinations/${id}`, { method: "DELETE" });
}

export function pushToDestination(
  id: string,
  jobIds: string[]
): Promise<PushResult> {
  return apiFetch(`/destinations/${id}/push`, {
    method: "POST",
    body: JSON.stringify({ job_ids: jobIds }),
  });
}

export function testDestination(
  id: string
): Promise<{ ok: boolean; status_code?: number; error?: string }> {
  return apiFetch(`/destinations/${id}/test`, { method: "POST" });
}

export function createJobStream(
  onEvent: (eventType: string, data: Record<string, unknown>) => void
): EventSource {
  const es = new EventSource(`${API_URL}/jobs/stream`);
  es.addEventListener("job_created", (e) => {
    onEvent("job_created", JSON.parse(e.data));
  });
  es.addEventListener("job_updated", (e) => {
    onEvent("job_updated", JSON.parse(e.data));
  });
  return es;
}
