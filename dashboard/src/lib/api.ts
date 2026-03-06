import type {
  BatchResponse,
  BatchStatus,
  ClientProfile,
  ClientSummary,
  Destination,
  Experiment,
  FeedbackEntry,
  FeedbackSummary,
  HealthResponse,
  Job,
  JobListItem,
  KnowledgeBaseFile,
  PipelineDefinition,
  PipelineStepConfig,
  PipelineTestResult,
  PromptPreview,
  PushResult,
  ScheduledBatch,
  Stats,
  VariantDef,
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

export function pushDataToDestination(
  id: string,
  data: Record<string, unknown>
): Promise<{ ok: boolean; destination_name: string; status_code?: number; error?: string }> {
  return apiFetch(`/destinations/${id}/push-data`, {
    method: "POST",
    body: JSON.stringify({ data }),
  });
}

export function testDestination(
  id: string
): Promise<{ ok: boolean; status_code?: number; error?: string }> {
  return apiFetch(`/destinations/${id}/test`, { method: "POST" });
}

// Context Hub
export function fetchClients(): Promise<{ clients: ClientSummary[] }> {
  return apiFetch("/clients");
}

export function fetchClient(slug: string): Promise<ClientProfile> {
  return apiFetch(`/clients/${slug}`);
}

export function createClient(
  body: Record<string, unknown>
): Promise<ClientProfile> {
  return apiFetch("/clients", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateClient(
  slug: string,
  body: Record<string, unknown>
): Promise<ClientProfile> {
  return apiFetch(`/clients/${slug}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function deleteClient(slug: string): Promise<{ ok: boolean }> {
  return apiFetch(`/clients/${slug}`, { method: "DELETE" });
}

export function fetchClientMarkdown(
  slug: string
): Promise<{ slug: string; markdown: string }> {
  return apiFetch(`/clients/${slug}/markdown`);
}

export function fetchKnowledgeBase(): Promise<{
  knowledge_base: Record<string, KnowledgeBaseFile[]>;
}> {
  return apiFetch("/knowledge-base");
}

export function fetchKnowledgeFile(
  category: string,
  filename: string
): Promise<KnowledgeBaseFile> {
  return apiFetch(`/knowledge-base/${category}/${filename}`);
}

export function updateKnowledgeFile(
  category: string,
  filename: string,
  content: string
): Promise<KnowledgeBaseFile> {
  return apiFetch(`/knowledge-base/${category}/${filename}`, {
    method: "PUT",
    body: JSON.stringify({ content }),
  });
}

export function previewPrompt(body: {
  skill: string;
  client_slug: string;
  sample_data?: Record<string, unknown>;
}): Promise<PromptPreview> {
  return apiFetch("/context/preview", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// Experiments / Lab
export function fetchVariants(
  skill: string
): Promise<{ skill: string; variants: VariantDef[] }> {
  return apiFetch(`/skills/${skill}/variants`);
}

export function createVariant(
  skill: string,
  body: { label: string; content: string }
): Promise<VariantDef> {
  return apiFetch(`/skills/${skill}/variants`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function forkVariant(skill: string): Promise<VariantDef> {
  return apiFetch(`/skills/${skill}/variants/fork`, { method: "POST" });
}

export function getVariant(
  skill: string,
  variantId: string
): Promise<VariantDef> {
  return apiFetch(`/skills/${skill}/variants/${variantId}`);
}

export function updateVariant(
  skill: string,
  variantId: string,
  body: { label: string; content: string }
): Promise<VariantDef> {
  return apiFetch(`/skills/${skill}/variants/${variantId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function deleteVariant(
  skill: string,
  variantId: string
): Promise<{ ok: boolean }> {
  return apiFetch(`/skills/${skill}/variants/${variantId}`, {
    method: "DELETE",
  });
}

export function fetchExperiments(): Promise<{ experiments: Experiment[] }> {
  return apiFetch("/experiments");
}

export function createExperiment(body: {
  skill: string;
  name: string;
  variant_ids: string[];
}): Promise<Experiment> {
  return apiFetch("/experiments", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getExperiment(expId: string): Promise<Experiment> {
  return apiFetch(`/experiments/${expId}`);
}

export function deleteExperiment(expId: string): Promise<{ ok: boolean }> {
  return apiFetch(`/experiments/${expId}`, { method: "DELETE" });
}

export function runExperiment(
  expId: string,
  body: {
    rows: Record<string, unknown>[];
    model?: string;
    instructions?: string;
  }
): Promise<{
  experiment_id: string;
  total_rows: number;
  distribution: { job_id: string; variant_id: string }[];
}> {
  return apiFetch(`/experiments/${expId}/run`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function promoteVariant(
  expId: string,
  variantId: string
): Promise<{ ok: boolean; promoted: string; skill: string }> {
  return apiFetch(`/experiments/${expId}/promote`, {
    method: "POST",
    body: JSON.stringify({ variant_id: variantId }),
  });
}

// Pipelines
export function fetchPipelines(): Promise<{ pipelines: PipelineDefinition[] }> {
  return apiFetch("/pipelines");
}

export function fetchPipeline(name: string): Promise<PipelineDefinition> {
  return apiFetch(`/pipelines/${name}`);
}

export function createPipeline(body: {
  name: string;
  description?: string;
  steps: PipelineStepConfig[];
}): Promise<PipelineDefinition> {
  return apiFetch("/pipelines", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updatePipeline(
  name: string,
  body: { description?: string; steps?: PipelineStepConfig[] }
): Promise<PipelineDefinition> {
  return apiFetch(`/pipelines/${name}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function deletePipeline(name: string): Promise<{ ok: boolean }> {
  return apiFetch(`/pipelines/${name}`, { method: "DELETE" });
}

export function testPipeline(
  name: string,
  body: { data: Record<string, unknown>; model?: string; instructions?: string }
): Promise<PipelineTestResult> {
  return apiFetch(`/pipelines/${name}/test`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// Feedback
export function submitFeedback(body: {
  job_id: string;
  skill?: string;
  model?: string;
  client_slug?: string | null;
  rating: "thumbs_up" | "thumbs_down";
  note?: string;
}): Promise<FeedbackEntry> {
  return apiFetch("/feedback", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchJobFeedback(
  jobId: string
): Promise<{ job_id: string; feedback: FeedbackEntry[] }> {
  return apiFetch(`/feedback/${jobId}`);
}

export function fetchFeedbackAnalytics(params?: {
  skill?: string;
  client_slug?: string;
  days?: number;
}): Promise<FeedbackSummary> {
  const searchParams = new URLSearchParams();
  if (params?.skill) searchParams.set("skill", params.skill);
  if (params?.client_slug) searchParams.set("client_slug", params.client_slug);
  if (params?.days) searchParams.set("days", String(params.days));
  const qs = searchParams.toString();
  return apiFetch(`/feedback/analytics/summary${qs ? `?${qs}` : ""}`);
}

export function deleteFeedback(feedbackId: string): Promise<{ ok: boolean }> {
  return apiFetch(`/feedback/${feedbackId}`, { method: "DELETE" });
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
