import time
import uuid
from enum import Enum
from pydantic import BaseModel, Field


class Rating(str, Enum):
    thumbs_up = "thumbs_up"
    thumbs_down = "thumbs_down"


class FeedbackEntry(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    job_id: str
    skill: str
    model: str = "opus"
    client_slug: str | None = None
    rating: Rating
    note: str = ""
    created_at: float = Field(default_factory=time.time)


class SubmitFeedbackRequest(BaseModel):
    job_id: str
    skill: str | None = None  # auto-populated from job if omitted
    model: str | None = None
    client_slug: str | None = None
    rating: Rating
    note: str = ""


class SkillAnalytics(BaseModel):
    skill: str
    total: int
    thumbs_up: int
    thumbs_down: int
    approval_rate: float


class FeedbackSummary(BaseModel):
    total_ratings: int
    overall_approval_rate: float
    by_skill: list[SkillAnalytics]
    by_client: dict[str, dict] = {}  # client_slug -> {total, thumbs_up, approval_rate}
