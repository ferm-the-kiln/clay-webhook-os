import time
import uuid

from pydantic import BaseModel, Field


class UsageEntry(BaseModel):
    id: str = Field(default_factory=lambda: uuid.uuid4().hex[:12])
    job_id: str = ""
    skill: str = ""
    model: str = "opus"
    input_tokens: int = 0
    output_tokens: int = 0
    is_actual: bool = False  # True if from CLI usage envelope, False if estimated
    timestamp: float = Field(default_factory=time.time)
    date_key: str = Field(default_factory=lambda: time.strftime("%Y-%m-%d"))


class UsageError(BaseModel):
    timestamp: float = Field(default_factory=time.time)
    error_type: str = ""  # "subscription_limit", "timeout", "other"
    message: str = ""
    date_key: str = Field(default_factory=lambda: time.strftime("%Y-%m-%d"))


class DailyUsage(BaseModel):
    date: str
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0
    request_count: int = 0
    errors: int = 0
    by_model: dict[str, int] = {}  # model -> total_tokens
    by_skill: dict[str, int] = {}  # skill -> total_tokens


class UsageSummary(BaseModel):
    today: DailyUsage
    week: DailyUsage
    month: DailyUsage
    daily_history: list[DailyUsage] = []
    subscription_health: str = "healthy"  # healthy, warning, critical, exhausted
    last_error: UsageError | None = None
