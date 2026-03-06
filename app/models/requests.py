from pydantic import BaseModel, Field


class WebhookRequest(BaseModel):
    skill: str = Field(..., description="Skill name (e.g. 'email-gen')")
    data: dict = Field(..., description="Row data from Clay")
    instructions: str | None = Field(None, description="Optional campaign instructions")
    model: str | None = Field(None, description="Model override: opus, sonnet, haiku")
    callback_url: str | None = Field(None, description="URL to POST results to (enables async mode)")
    row_id: str | None = Field(None, description="Row identifier for matching callback results")


class BatchRequest(BaseModel):
    skill: str = Field(..., description="Skill name to run on all rows")
    rows: list[dict] = Field(..., description="Array of row data objects")
    model: str | None = Field(None, description="Model override: opus, sonnet, haiku")
    instructions: str | None = Field(None, description="Optional instructions for all rows")


class PipelineStep(BaseModel):
    skill: str
    filter: str | None = Field(None, description="JSONPath expression to check before running")


class PipelineRequest(BaseModel):
    pipeline: str = Field(..., description="Pipeline name (e.g. 'full-outbound')")
    data: dict = Field(..., description="Initial row data")
    instructions: str | None = None
    model: str | None = None
