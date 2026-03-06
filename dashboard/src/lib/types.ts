export type JobStatus =
  | "queued"
  | "processing"
  | "completed"
  | "failed"
  | "retrying"
  | "dead_letter";

export interface Job {
  id: string;
  skill: string;
  row_id: string | null;
  status: JobStatus;
  duration_ms: number;
  error: string | null;
  result: Record<string, unknown> | null;
  created_at: number;
  completed_at: number | null;
  retry_count?: number;
  priority?: "high" | "normal" | "low";
  input_tokens_est?: number;
  output_tokens_est?: number;
  cost_est_usd?: number;
  feedback?: FeedbackEntry[];
}

export interface JobListItem {
  id: string;
  skill: string;
  row_id: string | null;
  status: JobStatus;
  duration_ms: number;
  created_at: number;
  retry_count?: number;
  priority?: "high" | "normal" | "low";
}

export interface Stats {
  total_processed: number;
  total_completed: number;
  total_failed: number;
  total_retrying: number;
  total_dead_letter: number;
  active_workers: number;
  queue_depth: number;
  avg_duration_ms: number;
  success_rate: number;
  cache_entries: number;
  cache_hits: number;
  cache_misses: number;
  cache_hit_rate: number;
  jobs_by_priority: { high: number; normal: number; low: number };
  tokens?: { total_input_est: number; total_output_est: number; total_est: number };
  cost?: {
    total_equivalent_usd: number;
    subscription_monthly_usd: number;
    total_savings_usd: number;
    cache_savings_usd: number;
  };
  feedback?: FeedbackSummary;
}

export interface HealthResponse {
  status: string;
  engine: string;
  timestamp: string;
  workers_available: number;
  workers_max: number;
  queue_pending: number;
  queue_total: number;
  skills_loaded: string[];
  cache_entries: number;
}

export interface BatchResponse {
  batch_id: string;
  total_rows: number;
  job_ids?: string[];
  scheduled_at?: string;
  status?: string;
}

export interface ScheduledBatch {
  id: string;
  skill: string;
  total_rows: number;
  scheduled_at: number;
  created_at: number;
  status: "scheduled" | "enqueued" | "cancelled";
  job_ids: string[];
}

export type DestinationType = "clay_webhook" | "generic_webhook";

export interface Destination {
  id: string;
  name: string;
  type: DestinationType;
  url: string;
  auth_header_name: string;
  auth_header_value: string;
  client_slug: string | null;
  created_at: number;
  updated_at: number;
}

export interface PushResult {
  destination_id: string;
  destination_name: string;
  total: number;
  success: number;
  failed: number;
  errors: { job_id: string; error: string }[];
}

export interface BatchStatus {
  batch_id: string;
  total_rows: number;
  completed: number;
  failed: number;
  processing: number;
  queued: number;
  done: boolean;
  avg_duration_ms: number;
  tokens: { input_est: number; output_est: number; total_est: number };
  cost: { equivalent_api_usd: number; subscription_usd: number; net_savings_usd: number };
  cache: { hits: number; hit_rate: number };
  jobs: {
    id: string;
    row_id: string | null;
    status: JobStatus;
    duration_ms: number;
    input_tokens_est: number;
    output_tokens_est: number;
    cost_est_usd: number;
  }[];
}

// Context Hub types
export interface CompanyInfo {
  domain: string;
  industry: string;
  size: string;
  stage: string;
  hq: string;
  founded: string;
}

export interface TonePreferences {
  formality: string;
  approach: string;
  avoid: string;
}

export interface ClientProfile {
  slug: string;
  name: string;
  company: CompanyInfo;
  what_they_sell: string;
  icp: string;
  competitive_landscape: string;
  recent_news: string;
  value_proposition: string;
  tone: TonePreferences;
  campaign_angles: string;
  notes: string;
  raw_markdown: string;
}

export interface ClientSummary {
  slug: string;
  name: string;
  industry: string;
  stage: string;
  domain: string;
}

export interface KnowledgeBaseFile {
  path: string;
  category: string;
  name: string;
  content: string;
}

export interface PromptPreview {
  assembled_prompt: string;
  context_files_loaded: string[];
  estimated_tokens: number;
}

// Feedback types
export type FeedbackRating = "thumbs_up" | "thumbs_down";

export interface FeedbackEntry {
  id: string;
  job_id: string;
  skill: string;
  model: string;
  client_slug: string | null;
  rating: FeedbackRating;
  note: string;
  created_at: number;
}

export interface SkillAnalytics {
  skill: string;
  total: number;
  thumbs_up: number;
  thumbs_down: number;
  approval_rate: number;
}

export interface FeedbackSummary {
  total_ratings: number;
  overall_approval_rate: number;
  by_skill: SkillAnalytics[];
  by_client: Record<string, { total: number; thumbs_up: number; approval_rate: number }>;
}

// Experiment / Lab types
export interface VariantDef {
  id: string;
  skill: string;
  label: string;
  content: string;
  created_at: number;
}

export interface VariantResults {
  variant_id: string;
  runs: number;
  avg_duration_ms: number;
  total_tokens: number;
  thumbs_up: number;
  thumbs_down: number;
}

export type ExperimentStatus = "draft" | "running" | "completed";

export interface Experiment {
  id: string;
  skill: string;
  name: string;
  variant_ids: string[];
  status: ExperimentStatus;
  results: Record<string, VariantResults>;
  created_at: number;
  completed_at: number | null;
}

// Pipeline types
export interface PipelineStepConfig {
  skill: string;
  model?: string | null;
  instructions?: string | null;
}

export interface PipelineDefinition {
  name: string;
  description: string;
  steps: PipelineStepConfig[];
}

export interface PipelineTestResult {
  pipeline: string;
  steps: {
    skill: string;
    success: boolean;
    duration_ms: number;
    output?: Record<string, unknown>;
    error?: string;
  }[];
  final_output: Record<string, unknown>;
  total_duration_ms: number;
}

export interface WebhookResponse {
  [key: string]: unknown;
  _meta?: {
    skill: string;
    model: string;
    duration_ms: number;
    cached: boolean;
  };
  error?: boolean;
  error_message?: string;
}
