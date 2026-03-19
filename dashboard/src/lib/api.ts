import type {
  AnalysisRequest,
  AnalysisResult,
  BatchResponse,
  BatchStatus,
  ClayConfig,
  ClientProfile,
  ClientSummary,
  CreateDatasetRequest,
  Dataset,
  DatasetRow,
  DatasetSummary,
  Destination,
  Experiment,
  FeedbackEntry,
  FeedbackSummary,
  FolderDefinition,
  FunctionDefinition,
  FunctionInput,
  FunctionOutput,
  FunctionStep,
  FunctionClayConfig,
  GenerateLeadsRequest,
  HealthResponse,
  Job,
  JobListItem,
  KnowledgeBaseFile,
  LeadListResult,
  PipelineDefinition,
  PipelineStepConfig,
  PipelineTestResult,
  PlayDefinition,
  PromptPreview,
  PushResult,
  QualityAlert,
  RunStageRequest,
  ScheduledBatch,
  StageStatus,
  Stats,
  ToolCategory,
  ToolDefinition,
  UsageHealth,
  UsageSummary,
  VariantDef,
  WebhookResponse,
} from "./types";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "https://clay.nomynoms.com";
const API_KEY = process.env.NEXT_PUBLIC_API_KEY || "";

export class NetworkError extends Error {
  constructor(url: string) {
    super(`Backend unreachable at ${url}. Check that the server is running and NEXT_PUBLIC_API_URL is correct.`);
    this.name = "NetworkError";
  }
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    const isFormData = init?.body instanceof FormData;
    res = await fetch(`${API_URL}${path}`, {
      ...init,
      headers: {
        ...(isFormData ? {} : { "Content-Type": "application/json" }),
        "X-API-Key": API_KEY,
        ...init?.headers,
      },
    });
  } catch (e) {
    if (e instanceof TypeError) {
      throw new NetworkError(API_URL);
    }
    throw e;
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      if (body.error_message) detail = body.error_message;
      else if (body.detail) detail = typeof body.detail === "string" ? body.detail : JSON.stringify(body.detail);
    } catch {
      // response body wasn't JSON — keep statusText
    }
    throw new Error(`API ${res.status}: ${detail}`);
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

export interface BatchSummary {
  batch_id: string;
  skill: string;
  total_rows: number;
  completed: number;
  failed: number;
  done: boolean;
  created_at: number;
}

export function fetchBatches(): Promise<{ batches: BatchSummary[] }> {
  return apiFetch("/batches");
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

// Quality Alerts
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

// Datasets
export function fetchDatasets(): Promise<{ datasets: DatasetSummary[] }> {
  return apiFetch("/datasets");
}

export function fetchDataset(id: string): Promise<Dataset> {
  return apiFetch(`/datasets/${id}`);
}

export function createDataset(body: CreateDatasetRequest): Promise<Dataset> {
  return apiFetch("/datasets", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function deleteDataset(id: string): Promise<{ ok: boolean }> {
  return apiFetch(`/datasets/${id}`, { method: "DELETE" });
}

export function importDatasetCsv(
  id: string,
  formData: FormData
): Promise<{ rows_added: number }> {
  return apiFetch(`/datasets/${id}/import`, {
    method: "POST",
    body: formData,
    headers: { "X-API-Key": API_KEY },
  });
}

export function importDatasetJson(
  id: string,
  rows: Record<string, unknown>[]
): Promise<{ rows_added: number }> {
  return apiFetch(`/datasets/${id}/import-json`, {
    method: "POST",
    body: JSON.stringify({ rows }),
  });
}

export function fetchDatasetRows(
  id: string,
  params?: { offset?: number; limit?: number }
): Promise<{ rows: DatasetRow[]; total: number; offset: number; limit: number }> {
  const qs = new URLSearchParams();
  if (params?.offset) qs.set("offset", String(params.offset));
  if (params?.limit) qs.set("limit", String(params.limit));
  const q = qs.toString();
  return apiFetch(`/datasets/${id}/rows${q ? `?${q}` : ""}`);
}

export function runDatasetStage(
  id: string,
  body: RunStageRequest
): Promise<{ batch_id: string; total_rows: number; stage: string }> {
  return apiFetch(`/datasets/${id}/run-stage`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchStageStatus(
  id: string,
  batchId: string
): Promise<StageStatus> {
  return apiFetch(`/datasets/${id}/stage-status/${batchId}`);
}

export async function exportDataset(id: string): Promise<Blob> {
  const res = await fetch(`${API_URL}/datasets/${id}/export`, {
    method: "POST",
    headers: { "X-API-Key": API_KEY },
  });
  if (!res.ok) throw new Error(`Export failed: ${res.statusText}`);
  return res.blob();
}

// Lead generation (Findymail)
export function generateLeads(
  datasetId: string,
  body: GenerateLeadsRequest
): Promise<{ request_id: string; status: string }> {
  return apiFetch(`/datasets/${datasetId}/generate-leads`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function getLeadResults(
  datasetId: string,
  requestId: string
): Promise<LeadListResult> {
  return apiFetch(`/datasets/${datasetId}/lead-results/${requestId}`);
}

// Dataset Analysis
export function analyzeDataset(
  id: string,
  body: AnalysisRequest
): Promise<{ analysis_id: string; status: string; analysis_type: string }> {
  return apiFetch(`/datasets/${id}/analyze`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchAnalyses(
  id: string
): Promise<{ analyses: AnalysisResult[] }> {
  return apiFetch(`/datasets/${id}/analyses`);
}

export function fetchAnalysis(
  id: string,
  analysisId: string
): Promise<AnalysisResult> {
  return apiFetch(`/datasets/${id}/analyses/${analysisId}`);
}

// Functions
export function fetchFunctions(params?: {
  folder?: string;
  q?: string;
}): Promise<{ functions: FunctionDefinition[]; by_folder: Record<string, FunctionDefinition[]>; total: number }> {
  const qs = new URLSearchParams();
  if (params?.folder) qs.set("folder", params.folder);
  if (params?.q) qs.set("q", params.q);
  const q = qs.toString();
  return apiFetch(`/functions${q ? `?${q}` : ""}`);
}

export function fetchFunction(id: string): Promise<FunctionDefinition> {
  return apiFetch(`/functions/${id}`);
}

export function createFunction(body: {
  name: string;
  description?: string;
  folder?: string;
  inputs?: FunctionInput[];
  outputs?: FunctionOutput[];
  steps?: FunctionStep[];
  clay_config?: FunctionClayConfig | null;
}): Promise<FunctionDefinition> {
  return apiFetch("/functions", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateFunction(
  id: string,
  body: Partial<Omit<FunctionDefinition, "id" | "created_at" | "updated_at">>
): Promise<FunctionDefinition> {
  return apiFetch(`/functions/${id}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function deleteFunction(id: string): Promise<{ ok: boolean }> {
  return apiFetch(`/functions/${id}`, { method: "DELETE" });
}

export function moveFunction(
  id: string,
  folder: string
): Promise<FunctionDefinition> {
  return apiFetch(`/functions/${id}/move`, {
    method: "POST",
    body: JSON.stringify({ folder }),
  });
}

// Folders
export function fetchFolders(): Promise<{ folders: FolderDefinition[] }> {
  return apiFetch("/functions/folders/list");
}

export function createFolder(body: {
  name: string;
  description?: string;
}): Promise<FolderDefinition> {
  return apiFetch("/functions/folders", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function renameFolder(
  name: string,
  newName: string
): Promise<FolderDefinition> {
  return apiFetch(`/functions/folders/${encodeURIComponent(name)}`, {
    method: "PUT",
    body: JSON.stringify({ new_name: newName }),
  });
}

export function deleteFolder(name: string): Promise<{ ok: boolean }> {
  return apiFetch(`/functions/folders/${encodeURIComponent(name)}`, {
    method: "DELETE",
  });
}

// Tool Catalog
export function fetchTools(category?: string): Promise<{ tools: ToolDefinition[]; total: number }> {
  const qs = category ? `?category=${encodeURIComponent(category)}` : "";
  return apiFetch(`/tools${qs}`);
}

export function fetchToolCategories(): Promise<{ categories: ToolCategory[] }> {
  return apiFetch("/tools/categories");
}

// Run function via webhook
export function runFunction(
  functionId: string,
  data: Record<string, unknown>
): Promise<Record<string, unknown>> {
  return apiFetch("/webhook", {
    method: "POST",
    body: JSON.stringify({ function: functionId, data }),
  });
}

// AI Function Assembly
export function assembleFunction(body: {
  description: string;
  context?: string;
}): Promise<{ suggestion: Record<string, unknown>; raw: string; duration_ms: number }> {
  return apiFetch("/functions/assemble", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// Clay Config Generation
export function generateFunctionClayConfig(
  funcId: string,
  body?: { api_url?: string; api_key?: string }
): Promise<Record<string, unknown>> {
  return apiFetch(`/functions/${funcId}/clay-config`, {
    method: "POST",
    body: JSON.stringify(body || {}),
  });
}
