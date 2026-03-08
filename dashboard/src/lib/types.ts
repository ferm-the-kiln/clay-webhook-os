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

// Campaign types
export type CampaignStatus = "draft" | "active" | "paused" | "completed";
export type ReviewStatus = "pending" | "approved" | "rejected" | "revised";

export interface CampaignGoal {
  description: string;
  target_count: number;
  metric: string;
}

export interface CampaignSchedule {
  frequency: string;
  batch_size: number;
  next_run_at: number | null;
}

export interface CampaignProgress {
  total_processed: number;
  total_approved: number;
  total_sent: number;
  total_rejected: number;
  total_pending_review: number;
  approval_rate: number;
}

export interface Campaign {
  id: string;
  name: string;
  description: string;
  status: CampaignStatus;
  pipeline: string;
  destination_id: string | null;
  client_slug: string | null;
  goal: CampaignGoal;
  schedule: CampaignSchedule;
  progress: CampaignProgress;
  audience: Record<string, unknown>[];
  audience_cursor: number;
  confidence_threshold: number;
  instructions: string | null;
  model: string;
  created_at: number;
  updated_at: number;
  review_stats?: ReviewStats;
}

export interface ReviewItem {
  id: string;
  job_id: string;
  campaign_id: string | null;
  skill: string;
  model: string;
  client_slug: string | null;
  row_id: string | null;
  input_data: Record<string, unknown>;
  output: Record<string, unknown>;
  confidence_score: number;
  status: ReviewStatus;
  reviewer_note: string;
  revision_job_id: string | null;
  created_at: number;
  reviewed_at: number | null;
}

export interface ReviewStats {
  total: number;
  pending: number;
  approved: number;
  rejected: number;
  revised: number;
  approval_rate: number;
}

export interface OutcomeOverview {
  total_campaigns: number;
  active_campaigns: number;
  completed_campaigns: number;
  total_sent: number;
  total_approved: number;
  total_processed: number;
  overall_approval_rate: number;
}

export interface OutcomeAlert {
  type: string;
  skill?: string;
  campaign_id?: string;
  campaign_name?: string;
  approval_rate?: number;
  message: string;
}

export interface OutcomeRecommendation {
  type: string;
  message: string;
}

export interface OutcomeDashboard {
  overview: OutcomeOverview;
  review_queue: ReviewStats;
  feedback_7d: FeedbackSummary;
  campaigns: {
    id: string;
    name: string;
    status: CampaignStatus;
    pipeline: string;
    progress: CampaignProgress;
    goal: CampaignGoal;
    audience_total: number;
    audience_remaining: number;
  }[];
  alerts: OutcomeAlert[];
  recommendations: OutcomeRecommendation[];
}

export interface QualityAlert {
  skill: string;
  approval_rate: number;
  total_ratings: number;
  thumbs_down: number;
  severity: string;
  recommendation: string;
}

export interface BatchRunResult {
  campaign_id: string;
  batch_size: number;
  auto_sent: number;
  queued_for_review: number;
  results: {
    row_index: number;
    routing: string;
    confidence?: number;
    review_item_id?: string;
    error?: string;
    output?: Record<string, unknown>;
  }[];
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
