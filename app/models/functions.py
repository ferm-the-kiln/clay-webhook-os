from pydantic import BaseModel, Field, model_validator


class FunctionInput(BaseModel):
    name: str = Field(..., description="Input field name")
    type: str = Field("string", description="Data type: string, number, url, email, boolean")
    required: bool = Field(True, description="Whether this input is required")
    description: str = Field("", description="Human-readable description")


class FunctionOutput(BaseModel):
    key: str = Field(..., description="Output field key")
    type: str = Field("string", description="Data type: string, number, boolean, json")
    description: str = Field("", description="Human-readable description")


class FunctionStep(BaseModel):
    tool: str = Field(..., description="Tool identifier: skill name or Deepline provider")
    params: dict[str, str] = Field(default_factory=dict, description="Tool parameters — values can reference inputs via {{input_name}}")


class FunctionClayConfig(BaseModel):
    webhook_path: str = Field("/webhook", description="Webhook endpoint path")
    method: str = Field("POST", description="HTTP method")
    headers: dict[str, str] = Field(default_factory=dict)
    body_template: dict[str, str] = Field(default_factory=dict, description="Body template with {{Column Name}} placeholders")


class FunctionDefinition(BaseModel):
    id: str = Field(..., description="Unique function ID (slug)")
    name: str = Field(..., description="Human-readable function name")
    description: str = Field("", description="What this function does")
    folder: str = Field("", description="Folder name for organization")
    inputs: list[FunctionInput] = Field(default_factory=list)
    outputs: list[FunctionOutput] = Field(default_factory=list)
    steps: list[FunctionStep] = Field(default_factory=list)
    clay_config: FunctionClayConfig | None = None
    created_at: float = 0
    updated_at: float = 0


class FolderDefinition(BaseModel):
    name: str = Field(..., description="Folder display name")
    description: str = Field("", description="Optional folder description")
    order: int = Field(0, description="Sort order")


class CreateFunctionRequest(BaseModel):
    name: str = Field(..., description="Human-readable function name")
    description: str = Field("", description="What this function does")
    folder: str = Field(..., description="Folder name (required)")
    inputs: list[FunctionInput] = Field(default_factory=list)
    outputs: list[FunctionOutput] = Field(default_factory=list)
    steps: list[FunctionStep] = Field(default_factory=list)
    clay_config: FunctionClayConfig | None = None

    @model_validator(mode="after")
    def validate_fields(self) -> "CreateFunctionRequest":
        if not self.name.strip():
            raise ValueError("Function name cannot be empty")
        if not self.folder.strip():
            raise ValueError("Folder is required — select a folder for this function")
        return self


class UpdateFunctionRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    folder: str | None = None
    inputs: list[FunctionInput] | None = None
    outputs: list[FunctionOutput] | None = None
    steps: list[FunctionStep] | None = None
    clay_config: FunctionClayConfig | None = None


class CreateFolderRequest(BaseModel):
    name: str = Field(..., description="Folder display name")
    description: str = Field("", description="Optional folder description")

    @model_validator(mode="after")
    def validate_name(self) -> "CreateFolderRequest":
        if not self.name.strip():
            raise ValueError("Folder name cannot be empty")
        return self


class RenameFolderRequest(BaseModel):
    new_name: str = Field(..., description="New folder name")

    @model_validator(mode="after")
    def validate_name(self) -> "RenameFolderRequest":
        if not self.new_name.strip():
            raise ValueError("Folder name cannot be empty")
        return self


class MoveFunctionRequest(BaseModel):
    folder: str = Field(..., description="Target folder name")


class StepTrace(BaseModel):
    step_index: int = Field(..., description="Zero-based step index")
    tool: str = Field(..., description="Tool identifier")
    tool_name: str = Field("", description="Human-readable tool name")
    executor: str = Field("unknown", description="Executor type: native_api, skill, call_ai, ai_agent, ai_fallback")
    status: str = Field("success", description="Step status: success, error, skipped")
    duration_ms: int = Field(0, description="Step execution time in milliseconds")
    resolved_params: dict[str, str] = Field(default_factory=dict, description="Parameters after template resolution")
    output_keys: list[str] = Field(default_factory=list, description="Output keys produced by this step")
    error_message: str | None = Field(None, description="Error message if step failed")
    ai_prompt: str | None = Field(None, description="AI prompt used for fallback/agent steps")


class PreviewStep(BaseModel):
    step_index: int = Field(..., description="Zero-based step index")
    tool: str = Field(..., description="Tool identifier")
    tool_name: str = Field("", description="Human-readable tool name")
    executor: str = Field("unknown", description="Expected executor type")
    resolved_params: dict[str, str] = Field(default_factory=dict)
    unresolved_variables: list[str] = Field(default_factory=list)
    expected_outputs: list[str] = Field(default_factory=list)


class PreviewRequest(BaseModel):
    data: dict[str, str] = Field(default_factory=dict, description="Test data for variable resolution")


class AssembleFunctionRequest(BaseModel):
    description: str = Field(..., description="Natural language description of desired function")
    context: str = Field("", description="Additional context about the use case")


# ── Prompt preparation models (local SDK execution) ─────


class PrepareRequest(BaseModel):
    data: dict = Field(default_factory=dict, description="Input data for the function")
    rows: list[dict] | None = Field(None, description="Multiple rows for batch execution (overrides data)")
    instructions: str | None = Field(None, description="Optional campaign instructions")
    model: str | None = Field(None, description="Model override (opus/sonnet/haiku)")


class PreparedStep(BaseModel):
    step_index: int = Field(..., description="Zero-based step index")
    tool: str = Field(..., description="Tool identifier")
    tool_name: str = Field("", description="Human-readable tool name")
    executor_type: str = Field(..., description="ai, native_api, or agent")
    prompt: str | None = Field(None, description="Assembled prompt for AI steps")
    model: str = Field("sonnet", description="Model to use for this step")
    output_keys: list[str] = Field(default_factory=list, description="Expected output keys")
    depends_on_outputs: list[str] = Field(default_factory=list, description="Output keys from prior steps injected into this prompt")
    native_config: dict | None = Field(None, description="Config for native API steps (tool_id, params)")


class PreparedFunction(BaseModel):
    function_id: str = Field(..., description="Function ID")
    function_name: str = Field("", description="Function display name")
    steps: list[PreparedStep] = Field(default_factory=list)
    model: str = Field("sonnet", description="Resolved model for the function")


class StepExecutionRequest(BaseModel):
    step_index: int = Field(..., description="Which step to execute")
    data: dict = Field(default_factory=dict, description="Input data including accumulated outputs")


class ConsolidatedPrompt(BaseModel):
    function_id: str = Field(..., description="Function ID")
    function_name: str = Field("", description="Function display name")
    prompt: str = Field(..., description="Single mega-prompt combining all AI steps")
    model: str = Field("sonnet", description="Model for execution")
    task_keys: list[str] = Field(default_factory=list, description="Ordered task keys in the output (task_1, task_2, ...)")
    output_keys: list[str] = Field(default_factory=list, description="Final output keys to extract")
    has_native_steps: bool = Field(False, description="Whether any steps require native API execution")
    native_steps: list[PreparedStep] = Field(default_factory=list, description="Native steps that must execute via backend")


# ── Local execution models (CLI runner + MCP server) ─────


class QueueLocalRequest(BaseModel):
    data: dict = Field(default_factory=dict, description="Input data for the function")
    rows: list[dict] | None = Field(None, description="Multiple rows for batch execution")
    instructions: str | None = Field(None, description="Optional campaign instructions")
    model: str | None = Field(None, description="Model override (opus/sonnet/haiku)")


class SubmitResultRequest(BaseModel):
    job_id: str = Field(..., description="Job ID from queue-local")
    result: dict = Field(..., description="JSON result from Claude Code execution")
    duration_ms: int | None = Field(None, description="Execution time in milliseconds")


class LocalJob(BaseModel):
    id: str = Field(..., description="Job ID")
    function_id: str = Field(..., description="Function ID")
    function_name: str = Field("", description="Function display name")
    prompt: str = Field(..., description="Assembled prompt for Claude")
    model: str = Field("sonnet", description="Model for execution")
    output_keys: list[str] = Field(default_factory=list, description="Expected output keys")
    task_keys: list[str] = Field(default_factory=list, description="Task keys in the prompt")
    native_results: dict = Field(default_factory=dict, description="Results from server-side native API steps")
    status: str = Field("pending", description="Job status: pending, running, completed, failed")
    queued_at: float = Field(0, description="Timestamp when job was queued")
    data: dict = Field(default_factory=dict, description="Original input data")
    instructions: str | None = Field(None, description="Campaign instructions if provided")


class UpdateJobStatusRequest(BaseModel):
    status: str = Field(..., description="New status: running, completed, failed")


# ── Batch pipeline execution models ─────


class BatchExecutionRequest(BaseModel):
    rows: list[dict] = Field(..., description="Rows to process through the function pipeline")
    instructions: str | None = Field(None, description="Optional campaign instructions")
    model: str | None = Field(None, description="Model override (opus/sonnet/haiku)")
    chunk_size: int = Field(5, description="Number of rows per AI call")


class FunnelStage(BaseModel):
    step_index: int = Field(..., description="Function step index")
    name: str = Field(..., description="Step name or label")
    step_type: str = Field(..., description="gate, function, skill, call_ai, etc.")
    rows_in: int = Field(..., description="Rows entering this stage")
    rows_out: int = Field(..., description="Rows exiting this stage")
    pass_rate: float = Field(..., description="Fraction of rows that passed (0.0-1.0)")
    duration_ms: int = Field(0, description="Stage execution time")
