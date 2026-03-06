from pydantic import BaseModel, Field


class PipelineStepConfig(BaseModel):
    skill: str
    model: str | None = None
    instructions: str | None = None


class PipelineDefinition(BaseModel):
    name: str
    description: str = ""
    steps: list[PipelineStepConfig]


class CreatePipelineRequest(BaseModel):
    name: str = Field(..., pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    description: str = ""
    steps: list[PipelineStepConfig]


class UpdatePipelineRequest(BaseModel):
    description: str | None = None
    steps: list[PipelineStepConfig] | None = None


class PipelineTestRequest(BaseModel):
    data: dict
    model: str = "opus"
    instructions: str | None = None
