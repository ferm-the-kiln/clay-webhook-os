from pydantic import BaseModel, Field, model_validator


class PipelineStepConfig(BaseModel):
    skill: str
    model: str | None = None
    instructions: str | None = None
    condition: str | None = None  # e.g. "icp_score >= 50"
    confidence_field: str | None = None  # field name in output to use as confidence score
    executor: str | None = None  # "agent" for agentic skills


class ParallelStepConfig(BaseModel):
    """A step that runs multiple sub-steps concurrently."""
    parallel: list[PipelineStepConfig]
    merge: str = "deep"  # "deep" (deep merge) or "namespace" (prefix keys with skill name)

    @model_validator(mode="after")
    def validate_parallel_not_empty(self) -> "ParallelStepConfig":
        if not self.parallel:
            raise ValueError("Parallel step must have at least one sub-step")
        return self


# Union type for pipeline steps — either a single step or a parallel group
PipelineStep = PipelineStepConfig | ParallelStepConfig


class PipelineDefinition(BaseModel):
    name: str
    description: str = ""
    steps: list[PipelineStep]
    confidence_threshold: float = 0.8  # default threshold for review routing


class CreatePipelineRequest(BaseModel):
    name: str = Field(..., pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    description: str = ""
    steps: list[PipelineStep]
    confidence_threshold: float = 0.8


class UpdatePipelineRequest(BaseModel):
    description: str | None = None
    steps: list[PipelineStep] | None = None
    confidence_threshold: float | None = None


class PipelineTestRequest(BaseModel):
    data: dict
    model: str = "opus"
    instructions: str | None = None
