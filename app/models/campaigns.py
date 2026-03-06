import time
import uuid
from enum import Enum
from pydantic import BaseModel, Field


class CampaignStatus(str, Enum):
    draft = "draft"
    active = "active"
    paused = "paused"
    completed = "completed"


class ReviewStatus(str, Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"
    revised = "revised"


class CampaignGoal(BaseModel):
    description: str = ""
    target_count: int = 0
    metric: str = "emails_sent"  # emails_sent, meetings_booked, replies


class CampaignSchedule(BaseModel):
    frequency: str = "daily"  # daily, weekly, manual
    batch_size: int = 10
    next_run_at: float | None = None


class CampaignProgress(BaseModel):
    total_processed: int = 0
    total_approved: int = 0
    total_sent: int = 0
    total_rejected: int = 0
    total_pending_review: int = 0
    approval_rate: float = 0.0


class Campaign(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    name: str
    description: str = ""
    status: CampaignStatus = CampaignStatus.draft
    pipeline: str  # pipeline name to run
    destination_id: str | None = None
    client_slug: str | None = None
    goal: CampaignGoal = Field(default_factory=CampaignGoal)
    schedule: CampaignSchedule = Field(default_factory=CampaignSchedule)
    progress: CampaignProgress = Field(default_factory=CampaignProgress)
    audience: list[dict] = []  # rows to process
    audience_cursor: int = 0  # index of next row to process
    confidence_threshold: float = 0.8  # above = auto-send, below = review
    instructions: str | None = None
    model: str = "opus"
    created_at: float = Field(default_factory=time.time)
    updated_at: float = Field(default_factory=time.time)


class CreateCampaignRequest(BaseModel):
    name: str
    description: str = ""
    pipeline: str
    destination_id: str | None = None
    client_slug: str | None = None
    goal: CampaignGoal | None = None
    schedule: CampaignSchedule | None = None
    audience: list[dict] = []
    confidence_threshold: float = 0.8
    instructions: str | None = None
    model: str = "opus"


class UpdateCampaignRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    status: CampaignStatus | None = None
    pipeline: str | None = None
    destination_id: str | None = None
    client_slug: str | None = None
    goal: CampaignGoal | None = None
    schedule: CampaignSchedule | None = None
    audience: list[dict] | None = None
    confidence_threshold: float | None = None
    instructions: str | None = None
    model: str | None = None


class AddAudienceRequest(BaseModel):
    rows: list[dict]


class ReviewItem(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    job_id: str
    campaign_id: str | None = None
    skill: str
    model: str = "opus"
    client_slug: str | None = None
    row_id: str | None = None
    input_data: dict = {}
    output: dict = {}
    confidence_score: float = 0.0
    status: ReviewStatus = ReviewStatus.pending
    reviewer_note: str = ""
    revision_job_id: str | None = None
    created_at: float = Field(default_factory=time.time)
    reviewed_at: float | None = None


class ReviewActionRequest(BaseModel):
    action: str  # approve, reject, revise
    note: str = ""
    revised_instructions: str | None = None
