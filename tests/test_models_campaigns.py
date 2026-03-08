"""Tests for app/models/campaigns.py — Pydantic model validation, defaults, serialization."""

import pytest
from pydantic import ValidationError

from app.models.campaigns import (
    AddAudienceRequest,
    Campaign,
    CampaignGoal,
    CampaignProgress,
    CampaignSchedule,
    CampaignStatus,
    CreateCampaignRequest,
    ReviewActionRequest,
    ReviewItem,
    ReviewStatus,
    UpdateCampaignRequest,
)


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------


class TestCampaignStatus:
    def test_values(self):
        assert CampaignStatus.draft == "draft"
        assert CampaignStatus.active == "active"
        assert CampaignStatus.paused == "paused"
        assert CampaignStatus.completed == "completed"

    def test_all_values(self):
        assert set(CampaignStatus) == {
            CampaignStatus.draft,
            CampaignStatus.active,
            CampaignStatus.paused,
            CampaignStatus.completed,
        }

    def test_string_coercion(self):
        assert CampaignStatus("active") == CampaignStatus.active


class TestReviewStatus:
    def test_values(self):
        assert ReviewStatus.pending == "pending"
        assert ReviewStatus.approved == "approved"
        assert ReviewStatus.rejected == "rejected"
        assert ReviewStatus.revised == "revised"


# ---------------------------------------------------------------------------
# Nested models — defaults
# ---------------------------------------------------------------------------


class TestCampaignGoal:
    def test_defaults(self):
        g = CampaignGoal()
        assert g.description == ""
        assert g.target_count == 0
        assert g.metric == "emails_sent"

    def test_custom(self):
        g = CampaignGoal(description="Send 100", target_count=100, metric="meetings_booked")
        assert g.target_count == 100
        assert g.metric == "meetings_booked"

    def test_serialization(self):
        g = CampaignGoal(description="Goal", target_count=50)
        d = g.model_dump()
        assert d == {"description": "Goal", "target_count": 50, "metric": "emails_sent"}


class TestCampaignSchedule:
    def test_defaults(self):
        s = CampaignSchedule()
        assert s.frequency == "daily"
        assert s.batch_size == 10
        assert s.next_run_at is None

    def test_custom(self):
        s = CampaignSchedule(frequency="weekly", batch_size=25, next_run_at=1000.0)
        assert s.frequency == "weekly"
        assert s.next_run_at == 1000.0


class TestCampaignProgress:
    def test_defaults(self):
        p = CampaignProgress()
        assert p.total_processed == 0
        assert p.total_approved == 0
        assert p.total_sent == 0
        assert p.total_rejected == 0
        assert p.total_pending_review == 0
        assert p.approval_rate == 0.0


# ---------------------------------------------------------------------------
# Campaign model
# ---------------------------------------------------------------------------


class TestCampaign:
    def test_required_fields(self):
        c = Campaign(name="Test", pipeline="full-outbound")
        assert c.name == "Test"
        assert c.pipeline == "full-outbound"

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            Campaign()  # missing name and pipeline

    def test_defaults(self):
        c = Campaign(name="Test", pipeline="p")
        assert c.status == CampaignStatus.draft
        assert c.description == ""
        assert c.destination_id is None
        assert c.client_slug is None
        assert c.audience == []
        assert c.audience_cursor == 0
        assert c.confidence_threshold == 0.8
        assert c.instructions is None
        assert c.model == "opus"
        assert isinstance(c.goal, CampaignGoal)
        assert isinstance(c.schedule, CampaignSchedule)
        assert isinstance(c.progress, CampaignProgress)

    def test_auto_generated_id(self):
        c1 = Campaign(name="A", pipeline="p")
        c2 = Campaign(name="B", pipeline="p")
        assert len(c1.id) == 12
        assert c1.id != c2.id

    def test_timestamps_auto_set(self):
        c = Campaign(name="Test", pipeline="p")
        assert c.created_at > 0
        assert c.updated_at > 0

    def test_status_enum_validation(self):
        c = Campaign(name="Test", pipeline="p", status="active")
        assert c.status == CampaignStatus.active

    def test_invalid_status_raises(self):
        with pytest.raises(ValidationError):
            Campaign(name="Test", pipeline="p", status="invalid")

    def test_serialization_roundtrip(self):
        c = Campaign(name="Test", pipeline="p", audience=[{"n": 1}])
        d = c.model_dump()
        c2 = Campaign(**d)
        assert c2.name == c.name
        assert c2.pipeline == c.pipeline
        assert c2.audience == [{"n": 1}]

    def test_nested_goal_in_dump(self):
        c = Campaign(name="T", pipeline="p", goal=CampaignGoal(target_count=50))
        d = c.model_dump()
        assert d["goal"]["target_count"] == 50


# ---------------------------------------------------------------------------
# Request models
# ---------------------------------------------------------------------------


class TestCreateCampaignRequest:
    def test_minimal(self):
        r = CreateCampaignRequest(name="Test", pipeline="p")
        assert r.name == "Test"
        assert r.pipeline == "p"
        assert r.audience == []
        assert r.model == "opus"

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            CreateCampaignRequest(pipeline="p")

    def test_missing_pipeline_raises(self):
        with pytest.raises(ValidationError):
            CreateCampaignRequest(name="T")

    def test_full_fields(self):
        r = CreateCampaignRequest(
            name="T", pipeline="p", description="D",
            destination_id="d1", client_slug="acme",
            goal=CampaignGoal(target_count=10),
            schedule=CampaignSchedule(frequency="manual"),
            audience=[{"a": 1}],
            confidence_threshold=0.9,
            instructions="Be concise",
            model="sonnet",
        )
        assert r.client_slug == "acme"
        assert r.goal.target_count == 10
        assert r.schedule.frequency == "manual"


class TestUpdateCampaignRequest:
    def test_all_optional(self):
        r = UpdateCampaignRequest()
        assert r.name is None
        assert r.pipeline is None
        assert r.status is None

    def test_partial_update(self):
        r = UpdateCampaignRequest(name="New Name", status="active")
        assert r.name == "New Name"
        assert r.status == CampaignStatus.active
        assert r.pipeline is None


class TestAddAudienceRequest:
    def test_valid(self):
        r = AddAudienceRequest(rows=[{"name": "Alice"}, {"name": "Bob"}])
        assert len(r.rows) == 2

    def test_missing_rows_raises(self):
        with pytest.raises(ValidationError):
            AddAudienceRequest()


# ---------------------------------------------------------------------------
# ReviewItem
# ---------------------------------------------------------------------------


class TestReviewItem:
    def test_required_fields(self):
        r = ReviewItem(job_id="j1", skill="email-gen")
        assert r.job_id == "j1"
        assert r.skill == "email-gen"

    def test_defaults(self):
        r = ReviewItem(job_id="j1", skill="s")
        assert r.status == ReviewStatus.pending
        assert r.campaign_id is None
        assert r.model == "opus"
        assert r.confidence_score == 0.0
        assert r.input_data == {}
        assert r.output == {}
        assert r.reviewer_note == ""
        assert r.revision_job_id is None
        assert r.reviewed_at is None

    def test_auto_id(self):
        r1 = ReviewItem(job_id="j1", skill="s")
        r2 = ReviewItem(job_id="j2", skill="s")
        assert len(r1.id) == 12
        assert r1.id != r2.id

    def test_status_serialization(self):
        r = ReviewItem(job_id="j1", skill="s", status="approved")
        assert r.status == ReviewStatus.approved
        d = r.model_dump()
        assert d["status"] == "approved"

    def test_missing_required_raises(self):
        with pytest.raises(ValidationError):
            ReviewItem()  # missing job_id and skill


# ---------------------------------------------------------------------------
# ReviewActionRequest
# ---------------------------------------------------------------------------


class TestReviewActionRequest:
    def test_approve(self):
        r = ReviewActionRequest(action="approve")
        assert r.action == "approve"
        assert r.note == ""
        assert r.revised_instructions is None

    def test_revise_with_instructions(self):
        r = ReviewActionRequest(
            action="revise",
            note="Too formal",
            revised_instructions="Be casual",
        )
        assert r.revised_instructions == "Be casual"

    def test_missing_action_raises(self):
        with pytest.raises(ValidationError):
            ReviewActionRequest()
