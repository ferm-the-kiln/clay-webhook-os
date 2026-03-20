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
    folder: str = Field("Uncategorized", description="Folder name for organization")
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
    folder: str = Field("Uncategorized", description="Folder name")
    inputs: list[FunctionInput] = Field(default_factory=list)
    outputs: list[FunctionOutput] = Field(default_factory=list)
    steps: list[FunctionStep] = Field(default_factory=list)
    clay_config: FunctionClayConfig | None = None

    @model_validator(mode="after")
    def validate_name(self) -> "CreateFunctionRequest":
        if not self.name.strip():
            raise ValueError("Function name cannot be empty")
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
