from pydantic import BaseModel, Field


class PipelineStepConfig(BaseModel):
    skill: str
    model: str | None = None
    instructions: str | None = None
    condition: str | None = None  # e.g. "icp_score >= 50"
    confidence_field: str | None = None  # field name in output to use as confidence score


class PipelineDefinition(BaseModel):
    name: str
    description: str = ""
    steps: list[PipelineStepConfig]
    confidence_threshold: float = 0.8  # default threshold for review routing


class CreatePipelineRequest(BaseModel):
    name: str = Field(..., pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    description: str = ""
    steps: list[PipelineStepConfig]
    confidence_threshold: float = 0.8


class UpdatePipelineRequest(BaseModel):
    description: str | None = None
    steps: list[PipelineStepConfig] | None = None
    confidence_threshold: float | None = None


class PipelineTestRequest(BaseModel):
    data: dict
    model: str = "opus"
    instructions: str | None = None
