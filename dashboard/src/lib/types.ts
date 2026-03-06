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
