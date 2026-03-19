from pydantic import BaseModel, Field


class DatasetColumn(BaseModel):
    name: str = Field(..., description="Column name")
    source: str = Field(..., description="Stage that added this column: import, find-email, classify, email-gen, etc.")
    type: str = Field("string", description="Column type: string, number, email, json, confidence")
    added_at: float = Field(..., description="Timestamp when column was added")


class DatasetSummary(BaseModel):
    id: str
    name: str
    row_count: int
    column_count: int
    stages_completed: list[str] = []
    created_at: float
    updated_at: float


class Dataset(BaseModel):
    id: str
    name: str
    description: str = ""
    client_slug: str | None = None
    columns: list[DatasetColumn] = []
    row_count: int = 0
    stages_completed: list[str] = []
    created_at: float
    updated_at: float


class CreateDatasetRequest(BaseModel):
    name: str = Field(..., description="Dataset name")
    description: str = Field("", description="Optional description")
    client_slug: str | None = Field(None, description="Associated client slug")


class RunStageRequest(BaseModel):
    stage: str = Field(..., description="Stage to execute: find-email, research, score, email-gen, etc.")
    row_ids: list[str] | None = Field(None, description="Row IDs to process (null = all rows)")
    condition: str | None = Field(None, description="Only process rows matching this condition (e.g., 'seniority_normalized == VP')")
    provider: str | None = Field(None, description="Provider override for this stage")
    config: dict = Field(default_factory=dict, description="Stage-specific settings")


class ComputeColumnRequest(BaseModel):
    column_name: str = Field(..., description="Name of the new column to create")
    formula: str = Field(..., description="Template string (e.g. '{{first_name}} {{last_name}}') or function (e.g. 'UPPER(company)')")
    row_ids: list[str] | None = Field(None, description="Row IDs to process (null = all rows)")


class StageStatus(BaseModel):
    batch_id: str
    stage: str
    total: int
    completed: int = 0
    failed: int = 0
    status: str = Field("running", description="running, completed, or failed")


class AnalysisRequest(BaseModel):
    analysis_type: str = Field(..., description="Type: icp, win-loss, churn, usage, sequence-performance, expansion")
    business_context: str = Field("", description="What does your company sell, who is your ICP")
    outcome_column: str | None = Field(None, description="Column name for won/lost/churned outcome")
    segment_columns: list[str] | None = Field(None, description="Columns to segment by")


class AnalysisResult(BaseModel):
    analysis_id: str
    dataset_id: str
    analysis_type: str
    status: str = Field("processing", description="processing, completed, or failed")
    business_context: str = ""
    outcome_column: str | None = None
    segment_columns: list[str] | None = None
    preprocessed_summary: dict | None = None
    results: dict | None = None
    error_message: str | None = None
    created_at: float
    completed_at: float | None = None
