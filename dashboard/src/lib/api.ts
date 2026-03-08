import type {
  BatchResponse,
  BatchRunResult,
  BatchStatus,
  Campaign,
  ClayConfig,
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
  OutcomeDashboard,
  PipelineDefinition,
  PipelineStepConfig,
  PipelineTestResult,
  PlayDefinition,
  PromptPreview,
  PushResult,
  QualityAlert,
  ReviewItem,
  ReviewStats,
  ScheduledBatch,
  Stats,
  UsageHealth,
  UsageSummary,
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

export function fetchHealthDeep(): Promise<HealthResponse> {
  return apiFetch("/health?deep=true");
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

export function createKnowledgeFile(body: {
  category: string;
  filename: string;
  content: string;
}): Promise<KnowledgeBaseFile> {
  return apiFetch("/knowledge-base", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function deleteKnowledgeFile(
  category: string,
  filename: string
): Promise<{ ok: boolean }> {
  return apiFetch(`/knowledge-base/${category}/${filename}`, {
    method: "DELETE",
  });
}

// Skills CRUD
export function fetchSkillContent(
  name: string
): Promise<{ name: string; content: string }> {
  return apiFetch(`/skills/${name}/content`);
}

export function updateSkillContent(
  name: string,
  content: string
): Promise<{ name: string; content: string }> {
  return apiFetch(`/skills/${name}/content`, {
    method: "PUT",
    body: JSON.stringify({ content }),
  });
}

export function createSkillFile(
  name: string,
  content: string
): Promise<{ name: string; content: string }> {
  return apiFetch("/skills", {
    method: "POST",
    body: JSON.stringify({ name, content }),
  });
}

export function deleteSkillFile(name: string): Promise<{ ok: boolean }> {
  return apiFetch(`/skills/${name}`, { method: "DELETE" });
}

// Knowledge Base Move
export function moveKnowledgeFile(body: {
  source_category: string;
  source_filename: string;
  target_category: string;
}): Promise<KnowledgeBaseFile> {
  return apiFetch("/knowledge-base/move", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchContextUsageMap(): Promise<{
  usage_map: Record<string, string[]>;
}> {
  return apiFetch("/context/usage-map");
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

// Campaigns
export function fetchCampaigns(status?: string): Promise<{ campaigns: Campaign[] }> {
  const qs = status ? `?status=${status}` : "";
  return apiFetch(`/campaigns${qs}`);
}

export function fetchCampaign(id: string): Promise<Campaign> {
  return apiFetch(`/campaigns/${id}`);
}

export function createCampaign(body: {
  name: string;
  description?: string;
  pipeline: string;
  destination_id?: string | null;
  client_slug?: string | null;
  goal?: { description?: string; target_count?: number; metric?: string };
  schedule?: { frequency?: string; batch_size?: number };
  audience?: Record<string, unknown>[];
  confidence_threshold?: number;
  instructions?: string;
  model?: string;
}): Promise<Campaign> {
  return apiFetch("/campaigns", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateCampaign(
  id: string,
  body: Record<string, unknown>
): Promise<Campaign> {
  return apiFetch(`/campaigns/${id}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function deleteCampaign(id: string): Promise<{ ok: boolean }> {
  return apiFetch(`/campaigns/${id}`, { method: "DELETE" });
}

export function addCampaignAudience(
  id: string,
  rows: Record<string, unknown>[]
): Promise<{ ok: boolean; total_audience: number; rows_added: number }> {
  return apiFetch(`/campaigns/${id}/audience`, {
    method: "POST",
    body: JSON.stringify({ rows }),
  });
}

export function activateCampaign(
  id: string
): Promise<{ ok: boolean; status: string }> {
  return apiFetch(`/campaigns/${id}/activate`, { method: "POST" });
}

export function pauseCampaign(
  id: string
): Promise<{ ok: boolean; status: string }> {
  return apiFetch(`/campaigns/${id}/pause`, { method: "POST" });
}

export function runCampaignBatch(id: string): Promise<BatchRunResult> {
  return apiFetch(`/campaigns/${id}/run-batch`, { method: "POST" });
}

export function fetchCampaignProgress(
  id: string
): Promise<{
  campaign_id: string;
  status: string;
  progress: Campaign["progress"];
  audience_total: number;
  audience_cursor: number;
  audience_remaining: number;
  goal: Campaign["goal"];
  review_stats: ReviewStats;
}> {
  return apiFetch(`/campaigns/${id}/progress`);
}

// Review Queue
export function fetchReviewItems(params?: {
  status?: string;
  campaign_id?: string;
  skill?: string;
  limit?: number;
}): Promise<{ items: ReviewItem[]; total: number }> {
  const searchParams = new URLSearchParams();
  if (params?.status) searchParams.set("status", params.status);
  if (params?.campaign_id) searchParams.set("campaign_id", params.campaign_id);
  if (params?.skill) searchParams.set("skill", params.skill);
  if (params?.limit) searchParams.set("limit", String(params.limit));
  const qs = searchParams.toString();
  return apiFetch(`/review${qs ? `?${qs}` : ""}`);
}

export function fetchReviewItem(id: string): Promise<ReviewItem> {
  return apiFetch(`/review/${id}`);
}

export function fetchReviewStats(
  campaignId?: string
): Promise<ReviewStats> {
  const qs = campaignId ? `?campaign_id=${campaignId}` : "";
  return apiFetch(`/review/stats${qs}`);
}

export function reviewAction(
  id: string,
  body: { action: string; note?: string; revised_instructions?: string }
): Promise<{ ok: boolean; status: string; push_result?: unknown; new_output?: Record<string, unknown>; confidence?: number }> {
  return apiFetch(`/review/${id}/action`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function rerunReviewItem(
  id: string
): Promise<{ ok: boolean; output: Record<string, unknown>; confidence: number }> {
  return apiFetch(`/review/${id}/rerun`, { method: "POST" });
}

// Outcomes (Phase 4)
export function fetchOutcomes(): Promise<OutcomeDashboard> {
  return apiFetch("/outcomes");
}

// Quality Alerts (Phase 2)
export function fetchQualityAlerts(
  threshold?: number
): Promise<{ alerts: QualityAlert[]; threshold: number }> {
  const qs = threshold ? `?threshold=${threshold}` : "";
  return apiFetch(`/feedback/alerts${qs}`);
}

// Feedback re-run (Phase 2)
export function rerunWithFeedback(
  jobId: string
): Promise<{ ok: boolean; original_job_id: string; skill: string; result: Record<string, unknown>; duration_ms: number; corrections_applied: number }> {
  return apiFetch(`/feedback/rerun/${jobId}`, { method: "POST" });
}

// Usage tracking
export function fetchUsage(): Promise<UsageSummary> {
  return apiFetch("/usage");
}

export function fetchUsageHealth(): Promise<UsageHealth> {
  return apiFetch("/usage/health");
}

// Plays
export function fetchPlays(category?: string): Promise<{ plays: PlayDefinition[] }> {
  const qs = category ? `?category=${category}` : "";
  return apiFetch(`/plays${qs}`);
}

export function fetchPlay(name: string): Promise<PlayDefinition> {
  return apiFetch(`/plays/${name}`);
}

export function createPlay(body: Record<string, unknown>): Promise<PlayDefinition> {
  return apiFetch("/plays", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updatePlay(
  name: string,
  body: Record<string, unknown>
): Promise<PlayDefinition> {
  return apiFetch(`/plays/${name}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function deletePlay(name: string): Promise<{ ok: boolean }> {
  return apiFetch(`/plays/${name}`, { method: "DELETE" });
}

export function forkPlay(
  name: string,
  body: { new_name: string; display_name: string; client_slug?: string | null; default_model?: string; default_instructions?: string }
): Promise<PlayDefinition> {
  return apiFetch(`/plays/${name}/fork`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function generateClayConfig(
  name: string,
  body: { client_slug?: string | null; api_url?: string; api_key?: string }
): Promise<ClayConfig> {
  return apiFetch(`/plays/${name}/clay-config`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function testPlay(
  name: string,
  body: { data: Record<string, unknown>; model?: string; instructions?: string }
): Promise<Record<string, unknown>> {
  return apiFetch(`/plays/${name}/test`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// System Status
export async function fetchRetries(): Promise<{
  pending: number;
  items: { job_id: string; skill: string; retry_count: number; last_error: string; next_retry_at: number }[];
}> {
  const res = await apiFetch<{ stats: Record<string, unknown>; pending: Array<Record<string, unknown>>; dead_letters: Array<Record<string, unknown>> }>("/retries");
  const pending = res.pending ?? [];
  return {
    pending: pending.length,
    items: pending.map((item) => ({
      job_id: String(item.job_id ?? item.id ?? ""),
      skill: String(item.skill ?? ""),
      retry_count: Number(item.attempt ?? 0),
      last_error: String(item.last_error ?? ""),
      next_retry_at: Number(item.next_retry_at ?? 0),
    })),
  };
}

export function fetchSubscriptions(): Promise<{
  status: string;
  health: string;
  today_requests: number;
  today_tokens: number;
  today_errors: number;
}> {
  return apiFetch("/subscription");
}

export async function fetchDeadLetter(): Promise<{
  count: number;
  items: { job_id: string; skill: string; error: string; failed_at: number }[];
}> {
  const res = await apiFetch<{ jobs: JobListItem[] }>("/jobs?status=dead_letter");
  return {
    count: res.jobs.length,
    items: res.jobs.map((j) => ({
      job_id: j.id,
      skill: j.skill,
      error: "",
      failed_at: j.created_at,
    })),
  };
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
