"""Tests for app/models/signals.py — BuyingSignal and SignalResearchResult models."""

import pytest
from pydantic import ValidationError

from app.models.signals import BuyingSignal, SignalResearchResult

# ---------------------------------------------------------------------------
# BuyingSignal
# ---------------------------------------------------------------------------


class TestBuyingSignal:
    def _valid_signal(self, **overrides):
        defaults = {
            "signal_type": "funding",
            "headline": "Acme raises $50M Series B",
            "detail": "Acme Corp closed a $50M Series B led by Sequoia. This indicates rapid growth.",
            "effective_score": 8.5,
            "relevance_to_client": "Their growth means more need for our product",
            "recommended_contact": "VP of Engineering",
            "urgency": "high",
        }
        defaults.update(overrides)
        return BuyingSignal(**defaults)

    def test_required_fields(self):
        signal = self._valid_signal()
        assert signal.signal_type == "funding"
        assert signal.headline == "Acme raises $50M Series B"
        assert signal.effective_score == 8.5
        assert signal.urgency == "high"

    def test_optional_source_url_none(self):
        signal = self._valid_signal()
        assert signal.source_url is None

    def test_optional_source_url_set(self):
        signal = self._valid_signal(source_url="https://example.com/news")
        assert signal.source_url == "https://example.com/news"

    def test_optional_days_ago_none(self):
        signal = self._valid_signal()
        assert signal.days_ago is None

    def test_optional_days_ago_set(self):
        signal = self._valid_signal(days_ago=7)
        assert signal.days_ago == 7

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            BuyingSignal(
                signal_type="funding",
                headline="Test",
                # missing detail, effective_score, etc.
            )

    def test_model_dump(self):
        signal = self._valid_signal(source_url="https://x.com", days_ago=3)
        d = signal.model_dump()
        assert d["signal_type"] == "funding"
        assert d["source_url"] == "https://x.com"
        assert d["days_ago"] == 3
        assert d["effective_score"] == 8.5

    def test_all_signal_types(self):
        for st in ("funding", "hiring", "leadership_change", "product_launch",
                    "partnership", "acquisition", "expansion", "tech_stack_change"):
            signal = self._valid_signal(signal_type=st)
            assert signal.signal_type == st

    def test_urgency_values(self):
        for urg in ("high", "medium", "low"):
            signal = self._valid_signal(urgency=urg)
            assert signal.urgency == urg

    def test_effective_score_float(self):
        signal = self._valid_signal(effective_score=0.0)
        assert signal.effective_score == 0.0
        signal2 = self._valid_signal(effective_score=30.0)
        assert signal2.effective_score == 30.0


# ---------------------------------------------------------------------------
# SignalResearchResult
# ---------------------------------------------------------------------------


class TestSignalResearchResult:
    def _valid_signal(self):
        return BuyingSignal(
            signal_type="funding",
            headline="Raised $50M",
            detail="Series B funding round closed.",
            effective_score=8.0,
            relevance_to_client="Growth opportunity",
            recommended_contact="VP Sales",
            urgency="high",
        )

    def _valid_result(self, **overrides):
        defaults = {
            "company_name": "Acme Corp",
            "company_domain": "acme.com",
            "company_summary": "Acme is a B2B SaaS company.",
            "signals": [self._valid_signal()],
            "priority_tier": "tier_1_now",
            "confidence_score": 0.85,
            "recommended_approach": "Reach out to VP Sales about their recent funding.",
        }
        defaults.update(overrides)
        return SignalResearchResult(**defaults)

    def test_required_fields(self):
        result = self._valid_result()
        assert result.company_name == "Acme Corp"
        assert result.company_domain == "acme.com"
        assert result.priority_tier == "tier_1_now"
        assert result.confidence_score == 0.85

    def test_signals_list(self):
        result = self._valid_result()
        assert len(result.signals) == 1
        assert result.signals[0].signal_type == "funding"

    def test_multiple_signals(self):
        signals = [
            self._valid_signal(),
            BuyingSignal(
                signal_type="hiring",
                headline="Hiring 20 engineers",
                detail="Job postings indicate growth.",
                effective_score=6.0,
                relevance_to_client="Team expansion",
                recommended_contact="CTO",
                urgency="medium",
            ),
        ]
        result = self._valid_result(signals=signals)
        assert len(result.signals) == 2

    def test_empty_signals_list(self):
        result = self._valid_result(signals=[])
        assert result.signals == []

    def test_priority_tiers(self):
        for tier in ("tier_1_now", "tier_2_soon", "tier_3_watch", "tier_4_pass"):
            result = self._valid_result(priority_tier=tier)
            assert result.priority_tier == tier

    def test_missing_required_field_raises(self):
        with pytest.raises(ValidationError):
            SignalResearchResult(
                company_name="Acme",
                # missing other required fields
            )

    def test_model_dump(self):
        result = self._valid_result()
        d = result.model_dump()
        assert d["company_name"] == "Acme Corp"
        assert d["company_domain"] == "acme.com"
        assert isinstance(d["signals"], list)
        assert d["signals"][0]["signal_type"] == "funding"

    def test_confidence_score_range(self):
        result = self._valid_result(confidence_score=0.0)
        assert result.confidence_score == 0.0
        result2 = self._valid_result(confidence_score=1.0)
        assert result2.confidence_score == 1.0

    def test_model_dump_nested_signal_fields(self):
        result = self._valid_result()
        d = result.model_dump()
        signal = d["signals"][0]
        assert "headline" in signal
        assert "detail" in signal
        assert "effective_score" in signal
        assert "source_url" in signal
        assert "days_ago" in signal
