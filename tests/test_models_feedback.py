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
