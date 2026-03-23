from pydantic import BaseModel, Field


# ── SOP Models ────────────────────────────────────────────

class CreateSOPRequest(BaseModel):
    title: str = Field(..., description="SOP title")
    category: str = Field("general", description="Category: onboarding, reporting, communication, approval, general")
    content: str = Field("", description="Markdown content")


class UpdateSOPRequest(BaseModel):
    title: str | None = Field(None, description="Updated title")
    category: str | None = Field(None, description="Updated category")
    content: str | None = Field(None, description="Updated content")


class SOPResponse(BaseModel):
    id: str
    title: str
    category: str
    content: str
    created_at: float
    updated_at: float


# ── Update Models ─────────────────────────────────────────

class CreateUpdateRequest(BaseModel):
    type: str = Field("update", description="Type: update, milestone, deliverable, note")
    title: str = Field(..., description="Update title")
    body: str = Field("", description="Markdown body")
    media_ids: list[str] = Field(default_factory=list, description="Attached media IDs")
    create_action: bool = Field(False, description="Auto-create client review action for deliverables")
    author_name: str = Field("", description="Name of the person posting")
    author_org: str = Field("internal", description="Organization: 'internal' or 'client'")
    project_id: str | None = Field(None, description="Link update to a project")


class UpdateResponse(BaseModel):
    id: str
    type: str
    title: str
    body: str
    pinned: bool
    media_ids: list[str]
    created_at: float
    author_name: str = ""
    author_org: str = "internal"


# ── Comment Models ────────────────────────────────────────

class CreateCommentRequest(BaseModel):
    body: str = Field(..., description="Comment body (supports markdown)")
    author: str = Field(..., description="Comment author name")


class PortalComment(BaseModel):
    id: str
    update_id: str
    body: str
    author: str
    created_at: float


# ── Action Item Models ────────────────────────────────────

class CreateActionRequest(BaseModel):
    title: str = Field(..., description="Action item title")
    description: str = Field("", description="Optional details")
    owner: str = Field("internal", description="Owner: internal or client")
    due_date: str | None = Field(None, description="ISO date YYYY-MM-DD")
    priority: str = Field("normal", description="Priority: high, normal, low")
    recurrence: str | None = Field(None, description="Recurrence: none, weekly, biweekly, monthly")
    project_id: str | None = Field(None, description="Link action to a project")


class UpdateActionRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    owner: str | None = None
    due_date: str | None = None
    priority: str | None = None
    status: str | None = None
    recurrence: str | None = None


# ── Media Models ──────────────────────────────────────────

class MediaResponse(BaseModel):
    id: str
    filename: str
    original_name: str
    mime_type: str
    size_bytes: int
    caption: str
    url: str
    created_at: float


# ── View Stats ────────────────────────────────────────────

class ViewStats(BaseModel):
    last_viewed_at: float | None = None
    view_count_7d: int = 0
    view_count_30d: int = 0


# ── SOP Acknowledgment ───────────────────────────────────

class SOPAcknowledgment(BaseModel):
    sop_id: str
    acknowledged_at: float
    acknowledged_by: str


# ── Portal Metadata ───────────────────────────────────────

class UpdatePortalRequest(BaseModel):
    status: str | None = Field(None, description="Client status: active, onboarding, paused, churned")
    notes: str | None = Field(None, description="Internal notes")
    slack_webhook_url: str | None = Field(None, description="Slack incoming webhook URL")
    notification_emails: list[str] | None = Field(None, description="Email addresses for notifications")


class PortalMeta(BaseModel):
    slug: str
    status: str = "active"
    notes: str = ""
    gws_folder_id: str | None = None
    gws_doc_id: str | None = None
    last_synced_at: float | None = None
    share_token: str | None = None
    share_token_created_at: float | None = None
    notification_emails: list[str] = Field(default_factory=list)
    created_at: float = 0.0
    updated_at: float = 0.0


# ── Onboarding ───────────────────────────────────────────

class OnboardRequest(BaseModel):
    slug: str = Field(..., description="URL-safe lowercase slug")
    name: str = Field(..., description="Client display name")


# ── Overview (composite) ─────────────────────────────────

class PortalOverview(BaseModel):
    slug: str
    name: str
    status: str
    sop_count: int
    update_count: int
    media_count: int
    action_count: int = 0
    open_client_actions: int = 0
    last_activity: float | None
    has_gws_sync: bool
    overdue_action_count: int = 0
    days_since_last_update: int | None = None
    last_viewed_at: float | None = None
    unacked_sop_count: int = 0


# ── Project Models ───────────────────────────────────────


class CreateProjectRequest(BaseModel):
    name: str = Field(..., description="Project name")
    description: str = Field("", description="Project description")
    color: str = Field("#6366f1", description="Hex color for visual ID")
    phases: list[dict] | None = Field(None, description="Initial phases [{name, order}]")


class UpdateProjectRequest(BaseModel):
    name: str | None = None
    description: str | None = None
    status: str | None = Field(None, description="active, on_hold, completed, archived")
    color: str | None = None
    current_phase: str | None = None


class CreatePhaseRequest(BaseModel):
    name: str = Field(..., description="Phase name")
    order: int = Field(0, description="Sort order")


class UpdatePhaseRequest(BaseModel):
    name: str | None = None
    status: str | None = Field(None, description="pending, active, completed")
    order: int | None = None
