import time
import uuid
from enum import Enum

from pydantic import BaseModel, Field


class VariantDef(BaseModel):
    id: str = Field(default_factory=lambda: "v_" + uuid.uuid4().hex[:8])
    skill: str
    label: str
    content: str  # markdown
    created_at: float = Field(default_factory=time.time)


class VariantResults(BaseModel):
    variant_id: str
    runs: int = 0
    avg_duration_ms: float = 0
    total_tokens: int = 0
    thumbs_up: int = 0
    thumbs_down: int = 0

    @property
    def approval_rate(self) -> float:
        total = self.thumbs_up + self.thumbs_down
        return round(self.thumbs_up / total, 3) if total > 0 else 0.0


class ExperimentStatus(str, Enum):
    draft = "draft"
    running = "running"
    completed = "completed"


class Experiment(BaseModel):
    id: str = Field(default_factory=lambda: "exp_" + uuid.uuid4().hex[:8])
    skill: str
    name: str
    variant_ids: list[str]  # includes "default" for base skill
    status: ExperimentStatus = ExperimentStatus.draft
    results: dict[str, VariantResults] = {}  # variant_id -> results
    created_at: float = Field(default_factory=time.time)
    completed_at: float | None = None


class CreateVariantRequest(BaseModel):
    label: str
    content: str


class CreateExperimentRequest(BaseModel):
    skill: str
    name: str
    variant_ids: list[str]  # e.g. ["default", "v_abc123"]


class RunExperimentRequest(BaseModel):
    rows: list[dict]
    model: str = "opus"
    instructions: str | None = None


class PromoteVariantRequest(BaseModel):
    variant_id: str
