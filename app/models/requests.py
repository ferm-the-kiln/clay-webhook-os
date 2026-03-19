from pydantic import BaseModel, Field, model_validator


class WebhookRequest(BaseModel):
    skill: str | None = Field(None, description="Skill name (e.g. 'email-gen')")
    skills: list[str] | None = Field(None, description="Skill chain (e.g. ['account-researcher', 'qualifier'])")
    function: str | None = Field(None, description="Function ID — loads function YAML, validates inputs, runs steps")
    data: dict = Field(..., description="Row data from Clay")
    instructions: str | None = Field(None, description="Optional campaign instructions")
    model: str | None = Field(None, description="Model override: opus, sonnet, haiku")
    output_format: str | None = Field(None, description="Output format: json, text, markdown, html (default: json)")
    callback_url: str | None = Field(None, description="URL to POST results to (enables async mode)")
    row_id: str | None = Field(None, description="Row identifier for matching callback results")
    max_retries: int | None = Field(None, description="Max retry attempts (default 3)")
    priority: str | None = Field(None, description="Job priority: high, normal, low")

    @model_validator(mode="after")
    def validate_skill_or_skills(self) -> "WebhookRequest":
        # function parameter is an alternative to skill/skills
        if self.function:
            return self
        if not self.skill and not self.skills:
            raise ValueError("Either 'skill', 'skills', or 'function' must be provided")
        if self.skill and self.skills:
            # Allow skill="auto" alongside skills list (skills is ignored in auto mode)
            if self.skill != "auto":
                raise ValueError("Provide 'skill' or 'skills', not both")
        return self


class BatchRequest(BaseModel):
    skill: str | None = Field(None, description="Skill name to run on all rows")
    pipeline: str | None = Field(None, description="Pipeline name to run per row (alternative to skill)")
    rows: list[dict] = Field(..., description="Array of row data objects")
    model: str | None = Field(None, description="Model override: opus, sonnet, haiku")
    instructions: str | None = Field(None, description="Optional instructions for all rows")
    priority: str | None = Field(None, description="Job priority: high, normal, low")
    scheduled_at: str | None = Field(None, description="ISO timestamp to schedule batch (future time)")
    deduplicate: bool = Field(True, description="Group rows by company_domain for dedup")

    @model_validator(mode="after")
    def validate_skill_or_pipeline(self) -> "BatchRequest":
        if not self.skill and not self.pipeline:
            raise ValueError("Either 'skill' or 'pipeline' must be provided")
        if self.skill and self.pipeline:
            raise ValueError("Provide 'skill' or 'pipeline', not both")
        return self


class PipelineStep(BaseModel):
    skill: str
    filter: str | None = Field(None, description="JSONPath expression to check before running")


class PipelineRequest(BaseModel):
    pipeline: str = Field(..., description="Pipeline name (e.g. 'full-outbound')")
    data: dict = Field(..., description="Initial row data")
    instructions: str | None = None
    model: str | None = None
