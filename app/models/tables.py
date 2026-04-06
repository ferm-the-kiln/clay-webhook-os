from enum import Enum

from pydantic import BaseModel, Field


class CellState(str, Enum):
    EMPTY = "empty"
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    SKIPPED = "skipped"
    FILTERED = "filtered"


# --- Column config sub-models ---

class ErrorHandlingConfig(BaseModel):
    on_error: str = Field("skip", description="skip | fallback | stop")
    fallback_value: str | None = Field(None, description="Value to write when on_error=fallback")
    max_retries: int = Field(0, description="Retry count before applying on_error policy")
    retry_delay_ms: int = Field(1000, description="Base delay between retries in ms")
    retry_backoff: str = Field("exponential", description="exponential | linear | fixed")


class RateLimitConfig(BaseModel):
    requests_per_minute: int = Field(60, description="Max requests per minute for this column")
    delay_between_ms: int = Field(0, description="Minimum delay between requests in ms")


class HttpColumnConfig(BaseModel):
    method: str = Field("GET", description="HTTP method: GET | POST | PUT | PATCH | DELETE")
    url: str = Field(..., description="URL with {{column_id}} template references")
    headers: dict[str, str] = Field(default_factory=dict, description="Headers with template refs")
    body: dict | str | None = Field(None, description="Request body (JSON or template string)")
    extract: str = Field("$", description="JSONPath expression to extract from response")
    if_empty: str | None = Field(None, description="Fallback value when extract returns nothing")


class WaterfallProvider(BaseModel):
    tool: str = Field(..., description="Provider tool ID, skill:*, function:*, or http:{url}")
    name: str = Field("", description="Display name")
    params: dict[str, str] = Field(default_factory=dict, description="Params with template refs")
    timeout: int = Field(30, description="Per-provider timeout in seconds")


class WaterfallColumnConfig(BaseModel):
    providers: list[WaterfallProvider] = Field(default_factory=list, description="Ordered provider list")


class LookupColumnConfig(BaseModel):
    source_table_id: str = Field(..., description="Table ID to search in")
    match_column: str = Field(..., description="Column ID in source table to match against")
    match_value: str = Field(..., description="Template ref e.g. '{{company_domain}}'")
    match_operator: str = Field("equals", description="equals | contains")
    return_column: str | None = Field(None, description="Column ID to return (default: match_column)")
    return_type: str = Field("value", description="value | boolean | count | rows")
    match_mode: str = Field("first", description="first | all")


class ScriptColumnConfig(BaseModel):
    language: str = Field("python", description="python | bash | node")
    code: str = Field("", description="Inline code (ignored if script_name is set)")
    script_name: str | None = Field(None, description="Named script reference from script store")
    extract: str | None = Field(None, description="JSONPath on stdout JSON")
    timeout: int = Field(30, description="Execution timeout in seconds")


class WriteColumnConfig(BaseModel):
    dest_table_id: str = Field(..., description="Destination table ID")
    column_mapping: dict[str, str] = Field(default_factory=dict, description="dest_col_id → {{source_col}} template")
    mode: str = Field("append", description="append | upsert")
    upsert_match_key: str | None = Field(None, description="Column ID to match on for upsert")
    expand_column: str | None = Field(None, description="Source column with array values to expand into rows")


class TableColumn(BaseModel):
    id: str = Field(..., description="Slug identifier, e.g. 'company_domain'")
    name: str = Field(..., description="Display name")
    column_type: str = Field(
        ...,
        description="input | enrichment | ai | formula | gate | static | http | waterfall | lookup | script | write",
    )
    position: int = Field(..., description="Left-to-right order (0-based)")
    width: int = Field(180, description="Pixel width for UI")
    frozen: bool = Field(False, description="Pinned to left edge")
    color: str | None = Field(None, description="Header color override")
    hidden: bool = Field(False, description="Hidden from grid")

    # Enrichment config
    tool: str | None = Field(None, description="Provider from tool catalog, skill:*, or function:*")
    params: dict[str, str] = Field(default_factory=dict, description="Params with {{column_id}} references")
    output_key: str | None = Field(None, description="Which result key to display in this column")

    # AI column config
    ai_prompt: str | None = Field(None, description="Natural language prompt for AI columns")
    ai_model: str = Field("sonnet", description="Model for AI columns")

    # Formula config
    formula: str | None = Field(None, description="Template string e.g. '{{first_name}} {{last_name}}'")

    # Gate config
    condition: str | None = Field(None, description="Filter condition e.g. 'employee_count >= 50'")
    condition_label: str | None = Field(None, description="Human-readable condition label")

    # Parent-child
    parent_column_id: str | None = Field(None, description="Parent column ID for child extraction")
    extract_path: str | None = Field(None, description="JSON path to extract from parent e.g. 'funding.total_raised'")

    # Dependencies (auto-computed from params/formula)
    depends_on: list[str] = Field(default_factory=list, description="Column IDs this column depends on")

    # --- New column type configs ---
    http_config: HttpColumnConfig | None = Field(None, description="Config for HTTP column type")
    waterfall_config: WaterfallColumnConfig | None = Field(None, description="Config for waterfall column type")
    lookup_config: LookupColumnConfig | None = Field(None, description="Config for lookup column type")
    script_config: ScriptColumnConfig | None = Field(None, description="Config for script column type")
    write_config: WriteColumnConfig | None = Field(None, description="Config for write column type")

    # --- Resilience configs (apply to enrichment, ai, http, waterfall, script) ---
    error_handling: ErrorHandlingConfig | None = Field(None, description="Per-column error handling policy")
    rate_limit: RateLimitConfig | None = Field(None, description="Per-column rate limiting")


class TableSource(BaseModel):
    id: str = Field(..., description="Unique source ID")
    name: str = Field("", description="Display name")
    source_type: str = Field(..., description="http | webhook | script")
    # HTTP source
    method: str = Field("GET", description="HTTP method")
    url: str = Field("", description="URL to fetch from")
    headers: dict[str, str] = Field(default_factory=dict)
    body: dict | None = Field(None)
    extract: str = Field("$", description="JSONPath to extract array from response")
    # Script source
    script_name: str | None = Field(None)
    code: str = Field("")
    language: str = Field("python")
    # Common
    column_mapping: dict[str, str] = Field(default_factory=dict, description="col_id → JSONPath or field name")
    dedup_column: str | None = Field(None, description="Column to deduplicate on")
    update_existing: bool = Field(False, description="Update matched rows on dedup")
    schedule: str = Field("manual", description="manual | hourly | daily | cron expression")
    last_run_at: float | None = Field(None)


class TableDefinition(BaseModel):
    id: str
    name: str
    description: str = ""
    columns: list[TableColumn] = []
    sources: list[TableSource] = Field(default_factory=list, description="Data sources for auto-populating rows")
    row_count: int = 0
    created_at: float
    updated_at: float
    source_function_id: str | None = None
    linked_sheet_id: str | None = Field(None, description="Google Sheets ID for sync")
    sync_direction: str = Field("none", description="none | pull | push | both")


class TableSummary(BaseModel):
    id: str
    name: str
    description: str = ""
    row_count: int = 0
    column_count: int = 0
    created_at: float
    updated_at: float


# --- Request / Response models ---

class CreateTableRequest(BaseModel):
    name: str = Field(..., description="Table name")
    description: str = Field("", description="Optional description")


class UpdateTableRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class AddColumnRequest(BaseModel):
    name: str = Field(..., description="Display name")
    column_type: str = Field(
        ...,
        description="input | enrichment | ai | formula | gate | static | http | waterfall | lookup | script | write",
    )
    position: int | None = Field(None, description="Position (null = append to end)")
    width: int = Field(180, description="Pixel width")
    frozen: bool = False
    color: str | None = None

    # Enrichment
    tool: str | None = None
    params: dict[str, str] = Field(default_factory=dict)
    output_key: str | None = None

    # AI
    ai_prompt: str | None = None
    ai_model: str = "sonnet"

    # Formula
    formula: str | None = None

    # Gate
    condition: str | None = None
    condition_label: str | None = None

    # Parent-child
    parent_column_id: str | None = None
    extract_path: str | None = None

    # New column type configs
    http_config: HttpColumnConfig | None = None
    waterfall_config: WaterfallColumnConfig | None = None
    lookup_config: LookupColumnConfig | None = None
    script_config: ScriptColumnConfig | None = None
    write_config: WriteColumnConfig | None = None

    # Resilience
    error_handling: ErrorHandlingConfig | None = None
    rate_limit: RateLimitConfig | None = None


class UpdateColumnRequest(BaseModel):
    name: str | None = None
    position: int | None = None
    width: int | None = None
    frozen: bool | None = None
    color: str | None = None
    hidden: bool | None = None
    tool: str | None = None
    params: dict[str, str] | None = None
    output_key: str | None = None
    ai_prompt: str | None = None
    ai_model: str | None = None
    formula: str | None = None
    condition: str | None = None
    condition_label: str | None = None
    parent_column_id: str | None = None
    extract_path: str | None = None

    # New column type configs
    http_config: HttpColumnConfig | None = None
    waterfall_config: WaterfallColumnConfig | None = None
    lookup_config: LookupColumnConfig | None = None
    script_config: ScriptColumnConfig | None = None
    write_config: WriteColumnConfig | None = None

    # Resilience
    error_handling: ErrorHandlingConfig | None = None
    rate_limit: RateLimitConfig | None = None


class ReorderColumnsRequest(BaseModel):
    column_ids: list[str] = Field(..., description="Ordered list of column IDs")


class ImportRowsRequest(BaseModel):
    rows: list[dict] = Field(..., description="List of row objects")


class DeleteRowsRequest(BaseModel):
    row_ids: list[str] = Field(..., description="Row IDs to delete")


class ExecuteTableRequest(BaseModel):
    row_ids: list[str] | None = Field(None, description="Row IDs to execute (null = all)")
    column_ids: list[str] | None = Field(None, description="Column IDs to execute (null = all enrichment columns)")
    model: str = Field("sonnet", description="Model override")
    limit: int | None = Field(None, description="Limit rows to process (e.g. 10 for 'Save & Run 10')")


class UpsertRowsRequest(BaseModel):
    rows: list[dict] = Field(..., description="Row data to upsert")
    match_key: str = Field(..., description="Column ID to match on for upsert")


class ExpandColumnRequest(BaseModel):
    source_column_id: str = Field(..., description="Column ID containing array values to expand")


class ValidateTableResponse(BaseModel):
    valid: bool = Field(..., description="True if no blocking errors")
    errors: list[str] = Field(default_factory=list, description="Blocking issues")
    warnings: list[str] = Field(default_factory=list, description="Non-blocking notices")
