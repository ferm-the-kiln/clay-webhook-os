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
  usage?: {
    subscription_health: string;
    today_requests: number;
    today_tokens: number;
    today_errors: number;
  };
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
  deep_check?: {
    claude_available: boolean;
    latency_ms?: number;
    error?: string;
  };
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
  personas: string;
  battle_cards: string;
  signal_playbook: string;
  proven_responses: string;
  active_campaigns: string;
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

// File Explorer types
export type FileNodeType = "drive" | "folder" | "file";
export type DriveId = "knowledge-base" | "clients" | "skills";

export interface FileNode {
  id: string;
  name: string;
  type: FileNodeType;
  driveId: DriveId;
  parentId: string | null;
  children?: FileNode[];
  content?: string;
  category?: string;
  slug?: string;
  meta?: Record<string, unknown>;
}

export interface SkillFile {
  name: string;
  content: string;
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

export interface QualityAlert {
  skill: string;
  approval_rate: number;
  total_ratings: number;
  thumbs_down: number;
  severity: string;
  recommendation: string;
}

// Pipeline types
export interface PipelineStepConfig {
  skill: string;
  model?: string | null;
  instructions?: string | null;
  condition?: string | null;
  confidence_field?: string | null;
}

export interface PipelineDefinition {
  name: string;
  description: string;
  steps: PipelineStepConfig[];
  confidence_threshold: number;
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

// Usage tracking types
export interface DailyUsage {
  date: string;
  input_tokens: number;
  output_tokens: number;
  total_tokens: number;
  request_count: number;
  errors: number;
  by_model: Record<string, number>;
  by_skill: Record<string, number>;
}

export interface UsageError {
  timestamp: number;
  error_type: string;
  message: string;
  date_key: string;
}

export interface UsageSummary {
  today: DailyUsage;
  week: DailyUsage;
  month: DailyUsage;
  daily_history: DailyUsage[];
  subscription_health: "healthy" | "warning" | "critical" | "exhausted";
  last_error: UsageError | null;
}

export interface UsageHealth {
  status: "healthy" | "warning" | "critical" | "exhausted";
  today_requests: number;
  today_tokens: number;
  today_errors: number;
  last_error: UsageError | null;
}

// Play types
export type PlayCategory = "outbound" | "research" | "meeting-prep" | "nurture" | "competitive" | "custom";

export interface SchemaField {
  name: string;
  type: string;
  required: boolean;
  description: string;
  example?: string | null;
}

export interface PlayDefinition {
  name: string;
  display_name: string;
  description: string;
  category: PlayCategory;
  pipeline: string;
  input_schema: SchemaField[];
  output_schema: SchemaField[];
  when_to_use: string;
  who_its_for: string;
  default_model: string;
  default_confidence_threshold: number;
  default_instructions: string | null;
  tags: string[];
  is_template: boolean;
  forked_from: string | null;
  created_at: number;
}

export interface ClayConfig {
  play: string;
  client_slug: string | null;
  webhook_url: string;
  method: string;
  headers: Record<string, string>;
  body_template: Record<string, unknown>;
  expected_output_columns: { name: string; type: string; description: string }[];
  setup_instructions: string[];
}

export interface WebhookResponse {
  [key: string]: unknown;
  _meta?: {
    skill: string;
    model: string;
    duration_ms: number;
    cached: boolean;
    input_tokens_est?: number;
    output_tokens_est?: number;
    cost_est_usd?: number;
  };
  error?: boolean;
  error_message?: string;
}

// Dataset types
export interface DatasetColumn {
  name: string;
  source: string;
  type: string;
  added_at: number;
}

export interface DatasetSummary {
  id: string;
  name: string;
  row_count: number;
  column_count: number;
  stages_completed: string[];
  created_at: number;
  updated_at: number;
}

export interface Dataset {
  id: string;
  name: string;
  description: string;
  client_slug: string | null;
  columns: DatasetColumn[];
  row_count: number;
  stages_completed: string[];
  created_at: number;
  updated_at: number;
}

export type DatasetRow = Record<string, unknown> & { _row_id: string };

export interface CreateDatasetRequest {
  name: string;
  description?: string;
  client_slug?: string | null;
}

export interface RunStageRequest {
  stage: string;
  row_ids?: string[] | null;
  provider?: string | null;
  config?: Record<string, unknown>;
}

export interface StageStatus {
  batch_id: string;
  stage: string;
  total: number;
  completed: number;
  failed: number;
  status: "running" | "completed" | "failed";
}

export interface ProviderInfo {
  name: string;
  stage: string;
  available: boolean;
}
