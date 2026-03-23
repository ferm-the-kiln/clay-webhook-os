import type {
  AnalysisRequest,
  AnalysisResult,
  ChannelMessage,
  ChannelSession,
  ChannelSessionSummary,
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
  FolderSheetList,
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
  OnboardResult,
  PipelineDefinition,
  PipelineStepConfig,
  PipelineTestResult,
  PlayDefinition,
  PortalAction,
  PortalComment,
  PortalDetail,
  PortalMedia,
  PortalMeta,
  PortalOverview,
  PortalProject,
  ProjectLink,
  PortalSOP,
  PortalSyncStatus,
  PortalUpdate,
  ProjectDetail,
  ProjectPhase,
  ProjectSummary,
  UpdateTemplate,
  PromptPreview,
  PublicPortalView,
  PushResult,
  RunStageRequest,
  ShareToken,
  SheetExportResult,
  SheetsStatus,
  SOPTemplate,
  StageStatus,
  Stats,
  ToolCategory,
  ToolDefinition,
  UsageHealth,
  UsageSummary,
  VariantDef,
  ExecutionRecord,
  StepTrace,
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

export function duplicateFunction(id: string): Promise<FunctionDefinition> {
  return apiFetch(`/functions/${id}/duplicate`, { method: "POST" });
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
  data: Record<string, unknown>,
  signal?: AbortSignal,
): Promise<Record<string, unknown>> {
  return apiFetch("/webhook", {
    method: "POST",
    body: JSON.stringify({ function: functionId, data }),
    signal,
  });
}

// Stream function execution via SSE
export function streamFunctionExecution(
  functionId: string,
  data: Record<string, unknown>,
  onStep: (trace: StepTrace) => void,
  onResult: (result: Record<string, unknown>) => void,
  onError: (error: string) => void,
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${API_URL}/webhook/functions/${functionId}/stream`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": API_KEY,
        },
        body: JSON.stringify({ data }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const text = await res.text();
        onError(`HTTP ${res.status}: ${text}`);
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        onError("No response body");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ") && currentEvent) {
            try {
              const payload = JSON.parse(line.slice(6));
              if (currentEvent === "step") {
                onStep(payload as StepTrace);
              } else if (currentEvent === "result") {
                onResult(payload as Record<string, unknown>);
              } else if (currentEvent === "error") {
                onError(payload.error_message || "Stream error");
              }
            } catch {
              // skip malformed JSON
            }
            currentEvent = "";
          }
        }
      }
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        onError(e instanceof Error ? e.message : "Stream failed");
      }
    }
  })();

  return controller;
}

// Execution history
export function fetchExecutions(
  functionId: string,
  limit?: number,
): Promise<{ executions: ExecutionRecord[]; total: number }> {
  const qs = limit ? `?limit=${limit}` : "";
  return apiFetch(`/functions/${functionId}/executions${qs}`);
}

export function fetchExecution(
  functionId: string,
  execId: string,
): Promise<ExecutionRecord> {
  return apiFetch(`/functions/${functionId}/executions/${execId}`);
}

// AI Function Assembly
export function assembleFunction(body: {
  description: string;
  context?: string;
}): Promise<{
  suggestion: Record<string, unknown>;
  reasoning: Record<string, unknown>;
  raw: string;
  duration_ms: number;
}> {
  return apiFetch("/functions/assemble", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// Function preview (dry run)
export function previewFunction(
  functionId: string,
  data: Record<string, string>
): Promise<{
  function: string;
  function_name: string;
  steps: Array<{
    step_index: number;
    tool: string;
    tool_name: string;
    executor: string;
    resolved_params: Record<string, string>;
    unresolved_variables: string[];
    expected_outputs: string[];
  }>;
  unresolved_variables: string[];
  summary: Record<string, number>;
}> {
  return apiFetch(`/functions/${functionId}/preview`, {
    method: "POST",
    body: JSON.stringify({ data }),
  });
}

// Tool detail
export function fetchToolDetail(toolId: string): Promise<Record<string, unknown>> {
  return apiFetch(`/tools/${encodeURIComponent(toolId)}`);
}

// ── Pattern Mining ──────────────────────────────────────

export function minePatterns(): Promise<{
  patterns: Array<{
    skill: string;
    total_feedback: number;
    approval_rate: number;
    thumbs_up: number;
    thumbs_down: number;
    client_count: number;
    common_issues: string[];
  }>;
  total_feedback: number;
  skills_analyzed: number;
}> {
  return apiFetch("/feedback/patterns/mine", { method: "POST" });
}

export function fetchPatterns(): Promise<{
  patterns: Array<{
    skill: string;
    total_feedback: number;
    approval_rate: number;
    common_issues: string[];
  }>;
  last_run: number;
}> {
  return apiFetch("/feedback/patterns/latest");
}

// ── Skill Generation ────────────────────────────────────

export function generateSkill(description: string, name?: string): Promise<{
  ok?: boolean;
  suggested_name: string;
  content: string;
  model_used: string;
  error?: boolean;
  error_message?: string;
}> {
  return apiFetch("/skills/generate", {
    method: "POST",
    body: JSON.stringify({ description, name }),
  });
}

export function confirmGeneratedSkill(name: string, content: string): Promise<{
  ok?: boolean;
  error?: boolean;
  error_message?: string;
}> {
  return apiFetch("/skills/generate/confirm", {
    method: "POST",
    body: JSON.stringify({ name, content }),
  });
}

// ── Skill Versions ──────────────────────────────────────

export function fetchSkillVersions(name: string): Promise<{
  name: string;
  versions: Array<{ version: number; timestamp: string; size_bytes: number }>;
}> {
  return apiFetch(`/skills/${name}/versions`);
}

export function fetchSkillVersion(name: string, version: number): Promise<{
  name: string;
  version: number;
  content: string;
}> {
  return apiFetch(`/skills/${name}/versions/${version}`);
}

export function rollbackSkillVersion(name: string, version: number): Promise<{
  ok?: boolean;
  error?: boolean;
}> {
  return apiFetch(`/skills/${name}/rollback/${version}`, { method: "POST" });
}

// ── Evals ───────────────────────────────────────────────

export function runEval(skill: string): Promise<Record<string, unknown>> {
  return apiFetch(`/evals/run/${skill}`, { method: "POST" });
}

export function fetchEvalResults(skill: string): Promise<Record<string, unknown>> {
  return apiFetch(`/evals/results/${skill}`);
}

export function fetchEvalHistory(skill: string): Promise<{
  skill: string;
  runs: string[];
}> {
  return apiFetch(`/evals/results/${skill}/history`);
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

// ── Google Sheets Integration ────────────────────────────

export function fetchSheetsStatus(): Promise<SheetsStatus> {
  return apiFetch("/sheets/status");
}

export function exportRunToSheets(
  functionId: string,
  body: {
    inputs: Record<string, unknown>[];
    outputs: Record<string, unknown>[];
    description?: string;
    metadata?: Record<string, unknown>;
  },
): Promise<SheetExportResult> {
  return apiFetch(`/functions/${functionId}/export-sheet`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function exportExecutionToSheets(
  functionId: string,
  execId: string,
): Promise<SheetExportResult> {
  return apiFetch(`/functions/${functionId}/executions/${execId}/export-sheet`, {
    method: "POST",
  });
}

export function listFolderSheets(folderName: string): Promise<FolderSheetList> {
  return apiFetch(`/functions/folders/${encodeURIComponent(folderName)}/sheets`);
}

export function listDriveFolders(): Promise<{
  folders: { name: string; id: string; created_at: string }[];
}> {
  return apiFetch("/sheets/folders");
}

// ── Portal (Client Engagement Hub) ──────────────────────

export function fetchPortals(): Promise<{ portals: PortalOverview[]; total: number }> {
  return apiFetch("/portal");
}

export function fetchPortal(slug: string): Promise<PortalDetail> {
  return apiFetch(`/portal/${slug}`);
}

export function updatePortal(
  slug: string,
  body: { status?: string; notes?: string; slack_webhook_url?: string; notification_emails?: string[] }
): Promise<PortalMeta> {
  return apiFetch(`/portal/${slug}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

// SOPs
export function fetchSOPs(slug: string): Promise<{ sops: PortalSOP[]; total: number }> {
  return apiFetch(`/portal/${slug}/sops`);
}

export function createSOP(
  slug: string,
  body: { title: string; category?: string; content?: string }
): Promise<PortalSOP> {
  return apiFetch(`/portal/${slug}/sops`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchSOP(slug: string, sopId: string): Promise<PortalSOP> {
  return apiFetch(`/portal/${slug}/sops/${sopId}`);
}

export function updateSOP(
  slug: string,
  sopId: string,
  body: { title?: string; category?: string; content?: string }
): Promise<PortalSOP> {
  return apiFetch(`/portal/${slug}/sops/${sopId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function deleteSOP(slug: string, sopId: string): Promise<{ ok: boolean }> {
  return apiFetch(`/portal/${slug}/sops/${sopId}`, { method: "DELETE" });
}

// Updates
export function fetchPortalUpdates(
  slug: string,
  params?: { limit?: number; offset?: number }
): Promise<{ updates: PortalUpdate[]; total: number }> {
  const qs = new URLSearchParams();
  if (params?.limit) qs.set("limit", String(params.limit));
  if (params?.offset) qs.set("offset", String(params.offset));
  const q = qs.toString();
  return apiFetch(`/portal/${slug}/updates${q ? `?${q}` : ""}`);
}

export function createPortalUpdate(
  slug: string,
  body: { type?: string; title: string; body?: string; media_ids?: string[]; create_action?: boolean; author_name?: string; author_org?: string; project_id?: string }
): Promise<PortalUpdate> {
  return apiFetch(`/portal/${slug}/updates`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updatePortalUpdate(
  slug: string,
  updateId: string,
  body: { project_id?: string | null },
): Promise<PortalUpdate> {
  return apiFetch(`/portal/${slug}/updates/${updateId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function toggleUpdatePin(slug: string, updateId: string): Promise<PortalUpdate> {
  return apiFetch(`/portal/${slug}/updates/${updateId}/pin`, { method: "PUT" });
}

export function deletePortalUpdate(slug: string, updateId: string): Promise<{ ok: boolean }> {
  return apiFetch(`/portal/${slug}/updates/${updateId}`, { method: "DELETE" });
}

// Media
export function fetchPortalMedia(slug: string): Promise<{ media: PortalMedia[]; total: number }> {
  return apiFetch(`/portal/${slug}/media`);
}

export function uploadPortalMedia(
  slug: string,
  formData: FormData
): Promise<PortalMedia> {
  return apiFetch(`/portal/${slug}/media`, {
    method: "POST",
    body: formData,
    headers: { "X-API-Key": API_KEY },
  });
}

export function deletePortalMedia(slug: string, mediaId: string): Promise<{ ok: boolean }> {
  return apiFetch(`/portal/${slug}/media/${mediaId}`, { method: "DELETE" });
}

// Actions
export function fetchActions(slug: string): Promise<{ actions: PortalAction[]; total: number }> {
  return apiFetch(`/portal/${slug}/actions`);
}

export function createAction(
  slug: string,
  body: { title: string; description?: string; owner?: string; due_date?: string | null; priority?: string; recurrence?: string; project_id?: string }
): Promise<PortalAction> {
  return apiFetch(`/portal/${slug}/actions`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateAction(
  slug: string,
  actionId: string,
  body: Record<string, unknown>
): Promise<PortalAction> {
  return apiFetch(`/portal/${slug}/actions/${actionId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function toggleAction(slug: string, actionId: string): Promise<PortalAction> {
  return apiFetch(`/portal/${slug}/actions/${actionId}/toggle`, { method: "PUT" });
}

export function deleteAction(slug: string, actionId: string): Promise<{ ok: boolean }> {
  return apiFetch(`/portal/${slug}/actions/${actionId}`, { method: "DELETE" });
}

// Comments
export function fetchComments(
  slug: string,
  updateId: string
): Promise<{ comments: PortalComment[]; total: number }> {
  return apiFetch(`/portal/${slug}/updates/${updateId}/comments`);
}

export function postComment(
  slug: string,
  updateId: string,
  body: { body: string; author: string }
): Promise<PortalComment> {
  return apiFetch(`/portal/${slug}/updates/${updateId}/comments`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function deleteComment(
  slug: string,
  updateId: string,
  commentId: string
): Promise<{ ok: boolean }> {
  return apiFetch(`/portal/${slug}/updates/${updateId}/comments/${commentId}`, {
    method: "DELETE",
  });
}

// SOP Acknowledgment
export function acknowledgeSOP(
  slug: string,
  sopId: string,
  user: string
): Promise<{ sop_id: string; acknowledged_at: number; acknowledged_by: string }> {
  return apiFetch(`/portal/${slug}/sops/${sopId}/acknowledge`, {
    method: "POST",
    body: JSON.stringify({ user }),
  });
}

// Update Templates
export function fetchUpdateTemplates(): Promise<{ templates: UpdateTemplate[]; total: number }> {
  return apiFetch("/portal/templates/updates");
}

// SOP Templates
export function fetchSOPTemplates(): Promise<{ templates: SOPTemplate[]; total: number }> {
  return apiFetch("/portal/templates/sops");
}

export function cloneSOPTemplates(
  slug: string,
  templateIds: string[]
): Promise<{ cloned: number; sops: PortalSOP[] }> {
  return apiFetch(`/portal/${slug}/sops/from-template`, {
    method: "POST",
    body: JSON.stringify({ template_ids: templateIds }),
  });
}

// Onboarding
export function onboardClient(body: { slug: string; name: string }): Promise<OnboardResult> {
  return apiFetch("/portal/onboard", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

// Share Links
export function createShareLink(slug: string): Promise<ShareToken> {
  return apiFetch(`/portal/${slug}/share`, { method: "POST" });
}

export function revokeShareLink(slug: string): Promise<{ ok: boolean }> {
  return apiFetch(`/portal/${slug}/share`, { method: "DELETE" });
}

export async function fetchPublicPortal(slug: string, token: string): Promise<PublicPortalView> {
  const res = await fetch(`${API_URL}/portal/${slug}/view?token=${encodeURIComponent(token)}`);
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.error_message || `HTTP ${res.status}`);
  }
  return res.json();
}

// Notifications
export function testPortalNotification(slug: string): Promise<{ ok: boolean; message: string }> {
  return apiFetch(`/portal/${slug}/notifications/test`, { method: "POST" });
}

// GWS Sync
export function syncPortal(slug: string): Promise<{
  ok: boolean;
  slug: string;
  doc_id: string;
  url: string;
  synced_at: number;
}> {
  return apiFetch(`/portal/${slug}/sync`, { method: "POST" });
}

export function fetchSyncStatus(slug: string): Promise<PortalSyncStatus> {
  return apiFetch(`/portal/${slug}/sync/status`);
}

// ── Projects ────────────────────────────────────────────────────

export function fetchProjects(slug: string): Promise<{ projects: ProjectSummary[]; total: number }> {
  return apiFetch(`/portal/${slug}/projects`);
}

export function createProject(
  slug: string,
  body: { name: string; description?: string; color?: string; phases?: { name: string; order?: number }[]; due_date?: string; links?: { title: string; url: string }[] },
): Promise<PortalProject> {
  return apiFetch(`/portal/${slug}/projects`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchProjectDetail(slug: string, projectId: string): Promise<ProjectDetail> {
  return apiFetch(`/portal/${slug}/projects/${projectId}`);
}

export function updateProject(
  slug: string,
  projectId: string,
  body: { name?: string; description?: string; status?: string; color?: string; current_phase?: string; due_date?: string | null; links?: ProjectLink[] },
): Promise<PortalProject> {
  return apiFetch(`/portal/${slug}/projects/${projectId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function deleteProject(slug: string, projectId: string): Promise<{ ok: boolean }> {
  return apiFetch(`/portal/${slug}/projects/${projectId}`, { method: "DELETE" });
}

export function addProjectPhase(
  slug: string,
  projectId: string,
  body: { name: string; order?: number },
): Promise<ProjectPhase> {
  return apiFetch(`/portal/${slug}/projects/${projectId}/phases`, {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function updateProjectPhase(
  slug: string,
  projectId: string,
  phaseId: string,
  body: { name?: string; status?: string; order?: number },
): Promise<ProjectPhase> {
  return apiFetch(`/portal/${slug}/projects/${projectId}/phases/${phaseId}`, {
    method: "PUT",
    body: JSON.stringify(body),
  });
}

export function deleteProjectPhase(slug: string, projectId: string, phaseId: string): Promise<{ ok: boolean }> {
  return apiFetch(`/portal/${slug}/projects/${projectId}/phases/${phaseId}`, { method: "DELETE" });
}

// ── Channel / Chat API ──────────────────────────────────────────

export function createChannel(body: {
  function_id: string;
  title?: string;
}): Promise<ChannelSession> {
  return apiFetch("/channels", {
    method: "POST",
    body: JSON.stringify(body),
  });
}

export function fetchChannels(): Promise<{ sessions: ChannelSessionSummary[] }> {
  return apiFetch("/channels");
}

export function fetchChannel(sessionId: string): Promise<ChannelSession> {
  return apiFetch(`/channels/${sessionId}`);
}

export function archiveChannel(sessionId: string): Promise<ChannelSession> {
  return apiFetch(`/channels/${sessionId}`, { method: "DELETE" });
}

export function streamChannelMessage(
  sessionId: string,
  content: string,
  data: Record<string, unknown>[],
  onEvent: (eventType: string, payload: Record<string, unknown>) => void,
  onError: (error: string) => void,
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(`${API_URL}/channels/${sessionId}/messages`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": API_KEY,
        },
        body: JSON.stringify({ content, data }),
        signal: controller.signal,
      });

      if (!res.ok) {
        const text = await res.text();
        onError(`HTTP ${res.status}: ${text}`);
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        onError("No response body");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEvent = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEvent = line.slice(7).trim();
          } else if (line.startsWith("data: ") && currentEvent) {
            try {
              const payload = JSON.parse(line.slice(6));
              onEvent(currentEvent, payload);
            } catch {
              // skip malformed JSON
            }
            currentEvent = "";
          }
        }
      }
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        onError(e instanceof Error ? e.message : "Stream failed");
      }
    }
  })();

  return controller;
}

// ── Client-scoped channel endpoints (share token auth) ──

export function createClientChannel(
  slug: string,
  token: string,
  body: { function_id: string; title?: string },
): Promise<ChannelSession> {
  return fetch(`${API_URL}/channels/client/${slug}?token=${encodeURIComponent(token)}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  }).then(async (res) => {
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.error_message || `HTTP ${res.status}`);
    }
    return res.json();
  });
}

export function fetchClientChannels(
  slug: string,
  token: string,
): Promise<{ sessions: ChannelSessionSummary[] }> {
  return fetch(`${API_URL}/channels/client/${slug}?token=${encodeURIComponent(token)}`).then(
    async (res) => {
      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        throw new Error(errBody.error_message || `HTTP ${res.status}`);
      }
      return res.json();
    },
  );
}

export function fetchClientChannel(
  slug: string,
  token: string,
  sessionId: string,
): Promise<ChannelSession> {
  return fetch(
    `${API_URL}/channels/client/${slug}/${sessionId}?token=${encodeURIComponent(token)}`,
  ).then(async (res) => {
    if (!res.ok) {
      const errBody = await res.json().catch(() => ({}));
      throw new Error(errBody.error_message || `HTTP ${res.status}`);
    }
    return res.json();
  });
}

export function streamClientChannelMessage(
  slug: string,
  token: string,
  sessionId: string,
  content: string,
  data: Record<string, unknown>[],
  onEvent: (eventType: string, payload: Record<string, unknown>) => void,
  onError: (error: string) => void,
): AbortController {
  const controller = new AbortController();

  (async () => {
    try {
      const res = await fetch(
        `${API_URL}/channels/client/${slug}/${sessionId}/messages?token=${encodeURIComponent(token)}`,
        {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ content, data }),
          signal: controller.signal,
        },
      );

      if (!res.ok) {
        const errBody = await res.json().catch(() => ({}));
        onError(errBody.error_message || `HTTP ${res.status}`);
        return;
      }

      const reader = res.body?.getReader();
      if (!reader) {
        onError("No response stream");
        return;
      }

      const decoder = new TextDecoder();
      let buffer = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split("\n");
        buffer = lines.pop() || "";

        let currentEventType = "";
        for (const line of lines) {
          if (line.startsWith("event: ")) {
            currentEventType = line.slice(7).trim();
          } else if (line.startsWith("data: ") && currentEventType) {
            try {
              const payload = JSON.parse(line.slice(6));
              onEvent(currentEventType, payload);
            } catch {
              // skip malformed JSON
            }
            currentEventType = "";
          }
        }
      }
    } catch (e) {
      if ((e as Error).name !== "AbortError") {
        onError((e as Error).message || "Stream failed");
      }
    }
  })();

  return controller;
}
