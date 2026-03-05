from pydantic import BaseModel


class Meta(BaseModel):
    skill: str
    model: str
    duration_ms: int
    cached: bool


class WebhookResponse(BaseModel):
    """Flexible response — skill output keys + _meta."""
    pass


class ErrorResponse(BaseModel):
    error: bool = True
    error_message: str
    skill: str = "unknown"


class HealthResponse(BaseModel):
    status: str
    engine: str
    workers_available: int
    workers_max: int
    skills_loaded: list[str]
    cache_entries: int


class PipelineStepResult(BaseModel):
    skill: str
    success: bool
    duration_ms: int
    output: dict | None = None
    error: str | None = None


class PipelineResponse(BaseModel):
    pipeline: str
    steps: list[PipelineStepResult]
    final_output: dict
    total_duration_ms: int
