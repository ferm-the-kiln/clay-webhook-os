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
  claude_user?: {
    logged_in: boolean;
    email: string | null;
    auth_method: string | null;
    subscription_type: string | null;
    org_name: string | null;
  };
  daemon?: {
    running: boolean;
    last_heartbeat_sec?: number;
    pid?: number | null;
    stale?: boolean;
    reason?: string;
  };
  backend_host?: string;
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

// Workbench types
export type WorkbenchPhase = "source" | "research" | "enrich";

export interface GenerateLeadsRequest {
  query: string;
  job_titles?: string[];
  limit?: number;
  company_domains?: string[];
}

export interface LeadListResult {
  request_id: string;
  status: "pending" | "processing" | "completed" | "failed";
  leads?: Record<string, unknown>[];
  total?: number;
  error?: string;
}

// Analysis types
// Function types
export interface FunctionInput {
  name: string;
  type: string;
  required: boolean;
  description: string;
}

export interface FunctionOutput {
  key: string;
  type: string;
  description: string;
}

export interface FunctionStep {
  tool: string;
  params: Record<string, string>;
}

export interface FunctionClayConfig {
  webhook_path: string;
  method: string;
  headers: Record<string, string>;
  body_template: Record<string, string>;
}

export interface FunctionDefinition {
  id: string;
  name: string;
  description: string;
  folder: string;
  inputs: FunctionInput[];
  outputs: FunctionOutput[];
  steps: FunctionStep[];
  clay_config: FunctionClayConfig | null;
  created_at: number;
  updated_at: number;
}

export interface FolderDefinition {
  name: string;
  description: string;
  order: number;
  function_count?: number;
}

export interface FunctionTemplate {
  id: string;
  name: string;
  description: string;
  category: string;
  inputs: FunctionInput[];
  outputs: FunctionOutput[];
  steps: FunctionStep[];
}

export interface ToolDefinition {
  id: string;
  name: string;
  category: string;
  description: string;
  source: "deepline" | "skill" | "function";
  inputs: { name: string; type: string }[];
  outputs: { key: string; type: string; description?: string }[];
  input_schema?: {
    fields: Array<{
      name: string;
      type: string;
      required: boolean;
      description?: string;
    }>;
  };
  model_tier?: string;
  execution_mode?: string;
  speed?: "fast" | "medium" | "slow" | "instant";
  cost?: "low" | "medium" | "high" | "free";
  has_native_api?: boolean;
  native_api_provider?: string;
  ai_fallback_description?: string;
  alias_of?: string;
}

export interface StepTrace {
  step_index: number;
  tool: string;
  tool_name: string;
  executor: "native_api" | "skill" | "call_ai" | "ai_agent" | "ai_fallback" | "gate" | "function" | "unknown";
  status: "success" | "error" | "skipped" | "gated_out";
  duration_ms: number;
  resolved_params: Record<string, string>;
  output_keys: string[];
  error_message?: string;
  ai_prompt?: string;
  ai_raw_response?: string;
  parse_error?: boolean;
}

export interface ExecutionRecord {
  id: string;
  function_id: string;
  timestamp: number;
  inputs: Record<string, unknown>;
  outputs: Record<string, unknown>;
  trace: StepTrace[];
  duration_ms: number;
  status: "success" | "error" | "partial";
  warnings: string[];
  step_count: number;
  sheet_url?: string;
}

// Batch pipeline / funnel types
export interface FunnelStage {
  step_index: number;
  name: string;
  step_type: string;
  rows_in: number;
  rows_out: number;
  pass_rate: number;
  duration_ms: number;
}

export interface BatchPipelineResult {
  funnel: FunnelStage[];
  total_rows_input: number;
  total_rows_output: number;
  total_duration_ms: number;
  rows: Record<string, unknown>[];
}

// Google Sheets integration types
export interface SheetExportResult {
  spreadsheet_id: string;
  url: string;
  title: string;
}

export interface SheetInfo {
  id: string;
  title: string;
  created_at: string;
  url: string;
}

export interface FolderSheetList {
  folder: string;
  sheets: SheetInfo[];
  total: number;
}

export interface SheetsStatus {
  available: boolean;
}

export interface AssemblyReasoning {
  thought_process?: string;
  tools_considered?: { tool_id: string; name: string; why: string; selected: boolean }[];
  confidence?: number;
}

export interface PreviewStep {
  step_index: number;
  tool: string;
  tool_name: string;
  executor: string;
  resolved_params: Record<string, string>;
  unresolved_variables: string[];
  expected_outputs: string[];
}

export interface FunctionPreview {
  function: string;
  function_name: string;
  steps: PreviewStep[];
  unresolved_variables: string[];
  summary: Record<string, number>;
}

export interface ToolCategory {
  category: string;
  tools: ToolDefinition[];
}

// Analysis types
export type AnalysisType = "icp" | "win-loss" | "churn" | "usage" | "sequence-performance" | "expansion";

export interface AnalysisRequest {
  analysis_type: AnalysisType;
  business_context?: string;
  outcome_column?: string | null;
  segment_columns?: string[] | null;
}

export interface AnalysisResult {
  analysis_id: string;
  dataset_id: string;
  analysis_type: AnalysisType;
  status: "processing" | "completed" | "failed";
  business_context: string;
  outcome_column: string | null;
  segment_columns: string[] | null;
  preprocessed_summary: {
    row_count: number;
    column_count: number;
    cross_tab_count: number;
    sample_row_count: number;
  } | null;
  results: Record<string, unknown> | null;
  error_message: string | null;
  created_at: number;
  completed_at: number | null;
}

// ── Portal types ─────────────────────────────────────────

export interface PortalOverview {
  slug: string;
  name: string;
  status: string;
  sop_count: number;
  update_count: number;
  media_count: number;
  action_count: number;
  open_client_actions: number;
  last_activity: number | null;
  has_gws_sync: boolean;
  overdue_action_count: number;
  days_since_last_update: number | null;
  last_viewed_at: number | null;
  unacked_sop_count: number;
}

export interface PortalMeta {
  slug: string;
  status: string;
  notes: string;
  gws_folder_id: string | null;
  gws_doc_id: string | null;
  last_synced_at: number | null;
  share_token: string | null;
  share_token_created_at: number | null;
  slack_webhook_url: string | null;
  notification_emails: string[];
  created_at: number;
  updated_at: number;
}

export interface PortalSOP {
  id: string;
  title: string;
  category: string;
  content: string;
  created_at: number;
  updated_at: number;
  acknowledged_at?: number;
  acknowledged_by?: string;
}

export type ApprovalStatus = "pending_review" | "approved" | "revision_requested" | "resubmitted";

export interface ApprovalHistoryEntry {
  action: string;
  actor_name: string;
  actor_org: string;
  notes: string;
  timestamp: number;
}

export interface PortalUpdate {
  id: string;
  type: string;
  title: string;
  body: string;
  pinned: boolean;
  media_ids: string[];
  created_at: number;
  google_doc_url?: string;
  author_name?: string;
  author_org?: string;
  project_id?: string | null;
  // Approval fields (deliverables only)
  approval_status?: ApprovalStatus | null;
  approval_history?: ApprovalHistoryEntry[];
  approved_by?: string | null;
  approved_at?: number | null;
  revision_notes?: string | null;
  revision_count?: number;
  linked_action_id?: string | null;
}

export interface PortalMedia {
  id: string;
  filename: string;
  original_name: string;
  mime_type: string;
  size_bytes: number;
  caption: string;
  url: string;
  created_at: number;
  drive_file_id?: string;
  project_id?: string | null;
}

export interface ViewStats {
  last_viewed_at: number | null;
  view_count_7d: number;
  view_count_30d: number;
}

export interface PortalComment {
  id: string;
  update_id: string;
  body: string;
  author: string;
  created_at: number;
}

export interface UpdateTemplate {
  id: string;
  title: string;
  type: string;
  body: string;
}

export interface PortalDetail {
  slug: string;
  name: string;
  meta: PortalMeta;
  sops: PortalSOP[];
  recent_updates: PortalUpdate[];
  media: PortalMedia[];
  actions: PortalAction[];
  view_stats: ViewStats;
  sop_acks: Record<string, { acknowledged_at: number; acknowledged_by: string }>;
  projects: ProjectSummary[];
}

// Action Items
export type ActionOwner = "internal" | "client";
export type ActionStatus = "open" | "in_progress" | "done";
export type ActionPriority = "high" | "normal" | "low";

export type ActionRecurrence = "none" | "weekly" | "biweekly" | "monthly";

export interface PortalAction {
  id: string;
  title: string;
  description: string;
  owner: ActionOwner;
  due_date: string | null;
  status: ActionStatus;
  priority: ActionPriority;
  recurrence: ActionRecurrence | null;
  project_id?: string | null;
  blocked_by_client?: boolean;
  blocked_reason?: string;
  blocked_at?: number | null;
  created_at: number;
  updated_at: number;
}

// Reactions
export type ReactionType = "thumbs_up" | "fire" | "eyes" | "check" | "question";

export interface ReactionEntry {
  user: string;
  created_at: number;
}

export type ReactionsMap = Record<string, ReactionEntry[]>;

// SOP Templates
export interface SOPTemplate {
  id: string;
  title: string;
  category: string;
  content: string;
  is_template: boolean;
}

export interface OnboardResult {
  slug: string;
  name: string;
  status: string;
  sops_created: number;
  sop_ids: string[];
}

// Projects
export type ProjectStatus = "active" | "on_hold" | "completed" | "archived";

export interface ProjectPhase {
  id: string;
  name: string;
  status: "pending" | "active" | "completed";
  order: number;
  completed_at: number | null;
}

export interface ProjectLink {
  id: string;
  title: string;
  url: string;
}

export interface PortalProject {
  id: string;
  name: string;
  description: string;
  status: ProjectStatus;
  color: string;
  phases: ProjectPhase[];
  current_phase: string | null;
  due_date?: string | null;
  links?: ProjectLink[];
  drive_folder_id?: string | null;
  drive_folder_url?: string | null;
  created_at: number;
  updated_at: number;
}

export interface ProjectSummary {
  id: string;
  name: string;
  description: string;
  status: ProjectStatus;
  color: string;
  phases: ProjectPhase[];
  current_phase: string | null;
  current_phase_name: string | null;
  due_date?: string | null;
  links?: ProjectLink[];
  drive_folder_url?: string | null;
  update_count: number;
  media_count: number;
  action_count: number;
  last_activity: number | null;
  created_at: number;
  updated_at: number;
}

export interface ProjectDetail {
  project: PortalProject;
  updates: PortalUpdate[];
  media: PortalMedia[];
  actions: PortalAction[];
  stats: {
    update_count: number;
    media_count: number;
    action_count: number;
    open_actions: number;
    completion_pct: number;
  };
}

// Discussion Threads
export interface ThreadMessage {
  id: string;
  body: string;
  author: string;
  author_org: string;
  created_at: number;
}

export interface PortalThread {
  id: string;
  project_id: string;
  title: string;
  status: string;
  created_at: number;
  updated_at: number;
  created_by: string;
  message_count: number;
  last_message_preview: string;
  last_message_author: string;
}

export interface ThreadDetail {
  id: string;
  project_id: string;
  title: string;
  status: string;
  created_at: number;
  updated_at: number;
  created_by: string;
  messages: ThreadMessage[];
}

// Share Links
export interface ShareToken {
  token: string;
  url: string;
  created_at: number;
}

export interface PublicPortalView {
  slug: string;
  name: string;
  status: string;
  brand_color?: string;
  sops: PortalSOP[];
  recent_updates: PortalUpdate[];
  actions: PortalAction[];
  sop_acks?: Record<string, { acknowledged_at: number; acknowledged_by: string }>;
}

export interface PortalSyncStatus {
  slug: string;
  synced: boolean;
  available: boolean;
  last_synced_at: number | null;
  doc_id: string | null;
  url: string | null;
}

// Channel / Chat types
export interface ChannelMessage {
  role: "user" | "assistant";
  content: string;
  timestamp: number;
  data: Record<string, unknown>[] | null;
  results: Record<string, unknown>[] | null;
  execution_id: string | null;
  mode?: "function" | "free_chat";
}

export interface ChannelSession {
  id: string;
  function_id: string | null;
  title: string;
  messages: ChannelMessage[];
  created_at: number;
  updated_at: number;
  status: "active" | "archived";
  client_slug?: string | null;
}

export interface ChannelSessionSummary {
  id: string;
  function_id: string | null;
  function_name: string;
  title: string;
  message_count: number;
  created_at: number;
  updated_at: number;
  status: "active" | "archived";
  client_slug?: string | null;
}

// Local execution (CLI runner / MCP server)
export interface LocalJob {
  id: string;
  function_id: string;
  function_name: string;
  prompt: string;
  model: string;
  output_keys: string[];
  task_keys: string[];
  native_results: Record<string, unknown>;
  status: "pending" | "running" | "completed" | "failed";
  queued_at: number;
  data: Record<string, unknown>;
  instructions?: string | null;
  exec_id?: string;
  logs?: LogEntry[];
}

export interface LogEntry {
  elapsed_ms: number;
  type: "init" | "tool_use" | "tool_result" | "text" | "result" | "error";
  message: string;
}

export interface LocalJobSummary {
  id: string;
  function_id: string;
  function_name: string;
  model: string;
  status: string;
  queued_at: number;
  prompt_chars: number;
  output_keys: string[];
}

// --- Table Builder ---

export type CellState =
  | "empty"
  | "pending"
  | "running"
  | "done"
  | "error"
  | "skipped"
  | "filtered";

export type TableColumnType =
  | "input"
  | "enrichment"
  | "ai"
  | "formula"
  | "gate"
  | "static"
  | "http"
  | "waterfall"
  | "lookup"
  | "script"
  | "write";

// --- Column config sub-types ---

export interface ErrorHandlingConfig {
  on_error: "skip" | "fallback" | "stop";
  fallback_value: string | null;
  max_retries: number;
  retry_delay_ms: number;
  retry_backoff: "exponential" | "linear" | "fixed";
}

export interface RateLimitConfig {
  requests_per_minute: number;
  delay_between_ms: number;
}

export interface HttpColumnConfig {
  method: "GET" | "POST" | "PUT" | "PATCH" | "DELETE";
  url: string;
  headers: Record<string, string>;
  body: Record<string, unknown> | string | null;
  extract: string;
  if_empty: string | null;
}

export interface WaterfallProvider {
  tool: string;
  name: string;
  params: Record<string, string>;
  timeout: number;
}

export interface WaterfallColumnConfig {
  providers: WaterfallProvider[];
}

export interface LookupColumnConfig {
  source_table_id: string;
  match_column: string;
  match_value: string;
  match_operator: "equals" | "contains";
  return_column: string | null;
  return_type: "value" | "boolean" | "count" | "rows";
  match_mode: "first" | "all";
}

export interface ScriptColumnConfig {
  language: "python" | "bash" | "node";
  code: string;
  script_name: string | null;
  extract: string | null;
  timeout: number;
}

export interface WriteColumnConfig {
  dest_table_id: string;
  column_mapping: Record<string, string>;
  mode: "append" | "upsert";
  upsert_match_key: string | null;
  expand_column: string | null;
}

export interface ValidateTableResponse {
  valid: boolean;
  errors: string[];
  warnings: string[];
}

export interface TableColumn {
  id: string;
  name: string;
  column_type: TableColumnType;
  position: number;
  width: number;
  frozen: boolean;
  color: string | null;
  hidden: boolean;
  // Enrichment
  tool: string | null;
  params: Record<string, string>;
  output_key: string | null;
  // AI
  ai_prompt: string | null;
  ai_model: string;
  // Formula
  formula: string | null;
  // Gate
  condition: string | null;
  condition_label: string | null;
  // Parent-child
  parent_column_id: string | null;
  extract_path: string | null;
  // Dependencies
  depends_on: string[];
  // New column type configs
  http_config: HttpColumnConfig | null;
  waterfall_config: WaterfallColumnConfig | null;
  lookup_config: LookupColumnConfig | null;
  script_config: ScriptColumnConfig | null;
  write_config: WriteColumnConfig | null;
  // Resilience
  error_handling: ErrorHandlingConfig | null;
  rate_limit: RateLimitConfig | null;
}

export interface TableDefinition {
  id: string;
  name: string;
  description: string;
  columns: TableColumn[];
  row_count: number;
  created_at: number;
  updated_at: number;
  source_function_id: string | null;
}

export interface TableSummary {
  id: string;
  name: string;
  description: string;
  row_count: number;
  column_count: number;
  created_at: number;
  updated_at: number;
}

// --- Workflow Templates (pre-built table configs for reps) ---

export type WorkflowCategory = "enrichment" | "research" | "scoring" | "outbound";

export interface WorkflowTemplateColumn {
  name: string;
  column_type: TableColumnType;
  tool?: string;
  params?: Record<string, string>;
  ai_prompt?: string;
  ai_model?: string;
  output_key?: string;
  depends_on_name?: string; // references another column by name
}

export interface WorkflowTemplate {
  id: string;
  name: string;
  description: string;
  category: WorkflowCategory;
  icon: string; // lucide icon name
  expected_inputs: { name: string; description: string; required?: boolean }[];
  produced_outputs: { name: string; description: string }[];
  columns: WorkflowTemplateColumn[];
}

export interface TableRow {
  _row_id: string;
  [key: string]: unknown;
}

export interface TableCellUpdate {
  type: "cell_update";
  row_id: string;
  column_id: string;
  status: CellState;
  value?: unknown;
  error?: string;
  duration_ms?: number;
  skip_reason?: "upstream_error";
  upstream_column_id?: string;
  fallback?: boolean;
  provider?: string;
}

export interface TableColumnProgress {
  type: "column_progress";
  column_id: string;
  done: number;
  total: number;
  errors: number;
  percent: number;
}

export type TableExecutionEvent =
  | { type: "execute_start"; total_rows: number; total_columns: number; waves: number }
  | { type: "column_start"; column_id: string; column_name: string; wave: number; rows_to_process: number }
  | TableCellUpdate
  | TableColumnProgress
  | { type: "column_complete"; column_id: string; done: number; errors: number; avg_duration_ms: number }
  | { type: "gate_result"; column_id: string; passed: number; filtered: number; total: number }
  | { type: "execute_complete"; total_duration_ms: number; cells_done: number; cells_errored: number; halted?: boolean }
  | { type: "retry"; column_id: string; row_id?: string; attempt: number; max_retries: number; delay_ms: number; error?: string }
  | { type: "waterfall_fallback"; column_id: string; row_id: string; provider: string; reason: string }
  | { type: "execution_halted"; column_id: string; reason: string };

// Pipeline flow strip types
export interface ExecutionWave {
  index: number;
  columns: TableColumn[];
}

export interface WaveEdge {
  from: string; // column_id
  to: string; // column_id
  type: "data" | "gate";
  condition?: string;
}

// --- Bridge (synchronous webhook bridge) ---

export interface BridgeStats {
  pending: number;
  max_pending: number;
  timeout_s: number;
  recently_resolved: number;
  total_created: number;
  total_resolved: number;
  total_timed_out: number;
  total_duplicates: number;
}

// --- Research (entity lookup) ---

export interface MemoryEntryResponse {
  skill: string;
  timestamp: number;
  summary: string;
  key_fields: Record<string, unknown>;
  ttl: number;
}

export interface ResearchMemoryResponse {
  entity_type: string | null;
  entity_id: string | null;
  entries: MemoryEntryResponse[];
  found?: boolean;
}
