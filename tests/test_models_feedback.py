import time

import pytest
from pydantic import ValidationError

from app.models.feedback import (
    FeedbackEntry,
    FeedbackSummary,
    Rating,
    SkillAnalytics,
    SubmitFeedbackRequest,
)


class TestRating:
    def test_values(self):
        assert Rating.thumbs_up == "thumbs_up"
        assert Rating.thumbs_down == "thumbs_down"

    def test_invalid_rating(self):
        with pytest.raises(ValueError):
            Rating("neutral")


class TestFeedbackEntry:
    def test_auto_id(self):
        e = FeedbackEntry(job_id="j1", skill="email-gen", rating=Rating.thumbs_up)
        assert len(e.id) == 12

    def test_auto_created_at(self):
        before = time.time()
        e = FeedbackEntry(job_id="j1", skill="x", rating=Rating.thumbs_up)
        assert e.created_at >= before

    def test_defaults(self):
        e = FeedbackEntry(job_id="j1", skill="x", rating=Rating.thumbs_down)
        assert e.model == "opus"
        assert e.client_slug is None
        assert e.note == ""

    def test_all_fields(self):
        e = FeedbackEntry(
            job_id="j1", skill="x", model="haiku",
            client_slug="acme", rating=Rating.thumbs_up, note="Great output"
        )
        assert e.model == "haiku"
        assert e.client_slug == "acme"
        assert e.note == "Great output"


class TestSubmitFeedbackRequest:
    def test_minimal(self):
        r = SubmitFeedbackRequest(job_id="j1", rating=Rating.thumbs_up)
        assert r.skill is None
        assert r.note == ""

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            SubmitFeedbackRequest(rating=Rating.thumbs_up)

    def test_rating_required(self):
        with pytest.raises(ValidationError):
            SubmitFeedbackRequest(job_id="j1")


class TestSkillAnalytics:
    def test_valid(self):
        a = SkillAnalytics(skill="x", total=10, thumbs_up=8, thumbs_down=2, approval_rate=0.8)
        assert a.approval_rate == 0.8


class TestFeedbackSummary:
    def test_defaults(self):
        s = FeedbackSummary(total_ratings=0, overall_approval_rate=0.0, by_skill=[])
        assert s.by_client == {}

    def test_with_skills(self):
        s = FeedbackSummary(
            total_ratings=5,
            overall_approval_rate=0.8,
            by_skill=[SkillAnalytics(skill="x", total=5, thumbs_up=4, thumbs_down=1, approval_rate=0.8)],
        )
        assert len(s.by_skill) == 1


# ---------------------------------------------------------------------------
# Rating — enum edges
# ---------------------------------------------------------------------------


class TestRatingEdges:
    def test_from_string(self):
        assert Rating("thumbs_up") is Rating.thumbs_up
        assert Rating("thumbs_down") is Rating.thumbs_down

    def test_is_string_type(self):
        assert isinstance(Rating.thumbs_up, str)
        assert Rating.thumbs_up == "thumbs_up"

    def test_all_values(self):
        values = {r.value for r in Rating}
        assert values == {"thumbs_up", "thumbs_down"}


# ---------------------------------------------------------------------------
# FeedbackEntry — edges
# ---------------------------------------------------------------------------


class TestFeedbackEntryEdges:
    def test_unique_ids(self):
        e1 = FeedbackEntry(job_id="j1", skill="x", rating=Rating.thumbs_up)
        e2 = FeedbackEntry(job_id="j1", skill="x", rating=Rating.thumbs_up)
        assert e1.id != e2.id

    def test_explicit_id_override(self):
        e = FeedbackEntry(id="custom-id", job_id="j1", skill="x", rating=Rating.thumbs_up)
        assert e.id == "custom-id"

    def test_explicit_created_at(self):
        e = FeedbackEntry(job_id="j1", skill="x", rating=Rating.thumbs_up, created_at=1000.0)
        assert e.created_at == 1000.0

    def test_model_dump_all_fields(self):
        e = FeedbackEntry(
            id="abc", job_id="j1", skill="email-gen", model="sonnet",
            client_slug="acme", rating=Rating.thumbs_down, note="Bad",
            created_at=1234.0,
        )
        d = e.model_dump()
        assert d["id"] == "abc"
        assert d["job_id"] == "j1"
        assert d["skill"] == "email-gen"
        assert d["model"] == "sonnet"
        assert d["client_slug"] == "acme"
        assert d["rating"] == "thumbs_down"
        assert d["note"] == "Bad"
        assert d["created_at"] == 1234.0

    def test_missing_required_job_id(self):
        with pytest.raises(ValidationError):
            FeedbackEntry(skill="x", rating=Rating.thumbs_up)

    def test_missing_required_skill(self):
        with pytest.raises(ValidationError):
            FeedbackEntry(job_id="j1", rating=Rating.thumbs_up)

    def test_missing_required_rating(self):
        with pytest.raises(ValidationError):
            FeedbackEntry(job_id="j1", skill="x")

    def test_invalid_rating_value(self):
        with pytest.raises(ValidationError):
            FeedbackEntry(job_id="j1", skill="x", rating="stars_5")


# ---------------------------------------------------------------------------
# SubmitFeedbackRequest — edges
# ---------------------------------------------------------------------------


class TestSubmitFeedbackRequestEdges:
    def test_all_fields(self):
        r = SubmitFeedbackRequest(
            job_id="j1", skill="email-gen", model="opus",
            client_slug="acme", rating=Rating.thumbs_down, note="Needs work",
        )
        assert r.skill == "email-gen"
        assert r.model == "opus"
        assert r.client_slug == "acme"
        assert r.note == "Needs work"

    def test_model_dump(self):
        r = SubmitFeedbackRequest(job_id="j1", rating=Rating.thumbs_up)
        d = r.model_dump()
        assert d["job_id"] == "j1"
        assert d["rating"] == "thumbs_up"
        assert d["skill"] is None
        assert d["model"] is None
        assert d["note"] == ""

    def test_rating_as_string(self):
        r = SubmitFeedbackRequest(job_id="j1", rating="thumbs_down")
        assert r.rating == Rating.thumbs_down

    def test_invalid_rating_string(self):
        with pytest.raises(ValidationError):
            SubmitFeedbackRequest(job_id="j1", rating="invalid")


# ---------------------------------------------------------------------------
# SkillAnalytics — edges
# ---------------------------------------------------------------------------


class TestSkillAnalyticsEdges:
    def test_model_dump(self):
        a = SkillAnalytics(skill="scorer", total=20, thumbs_up=15, thumbs_down=5, approval_rate=0.75)
        d = a.model_dump()
        assert d == {"skill": "scorer", "total": 20, "thumbs_up": 15, "thumbs_down": 5, "approval_rate": 0.75}

    def test_missing_required(self):
        with pytest.raises(ValidationError):
            SkillAnalytics(skill="x", total=10)

    def test_zero_totals(self):
        a = SkillAnalytics(skill="x", total=0, thumbs_up=0, thumbs_down=0, approval_rate=0.0)
        assert a.total == 0
        assert a.approval_rate == 0.0

    def test_100_percent_approval(self):
        a = SkillAnalytics(skill="x", total=50, thumbs_up=50, thumbs_down=0, approval_rate=1.0)
        assert a.approval_rate == 1.0


# ---------------------------------------------------------------------------
# FeedbackSummary — edges
# ---------------------------------------------------------------------------


class TestFeedbackSummaryEdges:
    def test_with_by_client(self):
        s = FeedbackSummary(
            total_ratings=10,
            overall_approval_rate=0.7,
            by_skill=[],
            by_client={
                "acme": {"total": 5, "thumbs_up": 4, "approval_rate": 0.8},
                "beta": {"total": 5, "thumbs_up": 3, "approval_rate": 0.6},
            },
        )
        assert len(s.by_client) == 2
        assert s.by_client["acme"]["approval_rate"] == 0.8

    def test_multiple_skills(self):
        s = FeedbackSummary(
            total_ratings=30,
            overall_approval_rate=0.73,
            by_skill=[
                SkillAnalytics(skill="email-gen", total=15, thumbs_up=12, thumbs_down=3, approval_rate=0.8),
                SkillAnalytics(skill="scorer", total=15, thumbs_up=10, thumbs_down=5, approval_rate=0.667),
            ],
        )
        assert len(s.by_skill) == 2
        skills = [a.skill for a in s.by_skill]
        assert "email-gen" in skills
        assert "scorer" in skills

    def test_model_dump(self):
        s = FeedbackSummary(
            total_ratings=5,
            overall_approval_rate=1.0,
            by_skill=[SkillAnalytics(skill="x", total=5, thumbs_up=5, thumbs_down=0, approval_rate=1.0)],
            by_client={"acme": {"total": 5, "thumbs_up": 5}},
        )
        d = s.model_dump()
        assert d["total_ratings"] == 5
        assert d["overall_approval_rate"] == 1.0
        assert isinstance(d["by_skill"], list)
        assert d["by_skill"][0]["skill"] == "x"
        assert d["by_client"]["acme"]["total"] == 5

    def test_missing_required(self):
        with pytest.raises(ValidationError):
            FeedbackSummary(total_ratings=0)
