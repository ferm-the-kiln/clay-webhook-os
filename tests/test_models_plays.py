"""Tests for app/models/plays.py — PlayDefinition, request models, name patterns, enums."""

import pytest
from pydantic import ValidationError

from app.models.plays import (
    ClayConfigRequest,
    CreatePlayRequest,
    ForkPlayRequest,
    PlayCategory,
    PlayDefinition,
    PlayTestRequest,
    SchemaField,
    UpdatePlayRequest,
)


# ---------------------------------------------------------------------------
# PlayCategory enum
# ---------------------------------------------------------------------------


class TestPlayCategory:
    def test_all_values(self):
        expected = {"outbound", "research", "meeting-prep", "nurture", "competitive", "custom"}
        assert {c.value for c in PlayCategory} == expected

    def test_string_coercion(self):
        assert PlayCategory("outbound") == PlayCategory.outbound
        assert PlayCategory("meeting-prep") == PlayCategory.meeting_prep


# ---------------------------------------------------------------------------
# SchemaField
# ---------------------------------------------------------------------------


class TestSchemaField:
    def test_defaults(self):
        f = SchemaField(name="email")
        assert f.name == "email"
        assert f.type == "string"
        assert f.required is False
        assert f.description == ""
        assert f.example is None

    def test_full(self):
        f = SchemaField(
            name="score",
            type="number",
            required=True,
            description="ICP score",
            example="85",
        )
        assert f.type == "number"
        assert f.required is True


# ---------------------------------------------------------------------------
# PlayDefinition
# ---------------------------------------------------------------------------


class TestPlayDefinition:
    def test_minimal(self):
        p = PlayDefinition(
            name="cold-outbound",
            display_name="Cold Outbound",
            category=PlayCategory.outbound,
            pipeline="full-outbound",
        )
        assert p.name == "cold-outbound"
        assert p.description == ""
        assert p.default_model == "opus"
        assert p.default_confidence_threshold == 0.8
        assert p.tags == []
        assert p.is_template is True
        assert p.forked_from is None

    def test_with_schemas(self):
        p = PlayDefinition(
            name="p",
            display_name="P",
            category=PlayCategory.research,
            pipeline="pipe",
            input_schema=[SchemaField(name="company_name")],
            output_schema=[SchemaField(name="report", type="object")],
        )
        assert len(p.input_schema) == 1
        assert len(p.output_schema) == 1

    def test_serialization(self):
        p = PlayDefinition(
            name="p",
            display_name="P",
            category="outbound",
            pipeline="pipe",
            tags=["sales", "email"],
        )
        d = p.model_dump()
        assert d["category"] == "outbound"
        assert d["tags"] == ["sales", "email"]
        p2 = PlayDefinition(**d)
        assert p2.category == PlayCategory.outbound


# ---------------------------------------------------------------------------
# CreatePlayRequest — name validation
# ---------------------------------------------------------------------------


class TestCreatePlayRequest:
    def test_valid(self):
        r = CreatePlayRequest(
            name="cold-outbound",
            display_name="Cold Outbound",
            category="outbound",
            pipeline="full-outbound",
        )
        assert r.name == "cold-outbound"

    def test_invalid_name_uppercase(self):
        with pytest.raises(ValidationError):
            CreatePlayRequest(
                name="ColdOutbound",
                display_name="X",
                category="outbound",
                pipeline="p",
            )

    def test_invalid_name_spaces(self):
        with pytest.raises(ValidationError):
            CreatePlayRequest(
                name="cold outbound",
                display_name="X",
                category="outbound",
                pipeline="p",
            )

    def test_invalid_name_trailing_dash(self):
        with pytest.raises(ValidationError):
            CreatePlayRequest(
                name="cold-",
                display_name="X",
                category="outbound",
                pipeline="p",
            )

    def test_missing_display_name_raises(self):
        with pytest.raises(ValidationError):
            CreatePlayRequest(name="ab", category="outbound", pipeline="p")

    def test_invalid_category_raises(self):
        with pytest.raises(ValidationError):
            CreatePlayRequest(
                name="ab",
                display_name="X",
                category="invalid",
                pipeline="p",
            )

    def test_defaults(self):
        r = CreatePlayRequest(
            name="ab",
            display_name="X",
            category="custom",
            pipeline="p",
        )
        assert r.default_model == "opus"
        assert r.default_confidence_threshold == 0.8
        assert r.tags == []


# ---------------------------------------------------------------------------
# UpdatePlayRequest
# ---------------------------------------------------------------------------


class TestUpdatePlayRequest:
    def test_all_optional(self):
        r = UpdatePlayRequest()
        for field_name in UpdatePlayRequest.model_fields:
            assert getattr(r, field_name) is None

    def test_partial(self):
        r = UpdatePlayRequest(display_name="New Name", tags=["new"])
        assert r.display_name == "New Name"
        assert r.tags == ["new"]
        assert r.pipeline is None


# ---------------------------------------------------------------------------
# ForkPlayRequest
# ---------------------------------------------------------------------------


class TestForkPlayRequest:
    def test_valid(self):
        r = ForkPlayRequest(new_name="forked-play", display_name="Forked Play")
        assert r.new_name == "forked-play"
        assert r.client_slug is None
        assert r.default_model is None

    def test_invalid_name(self):
        with pytest.raises(ValidationError):
            ForkPlayRequest(new_name="Bad Name!", display_name="X")

    def test_missing_display_name_raises(self):
        with pytest.raises(ValidationError):
            ForkPlayRequest(new_name="ab")


# ---------------------------------------------------------------------------
# ClayConfigRequest
# ---------------------------------------------------------------------------


class TestClayConfigRequest:
    def test_defaults(self):
        r = ClayConfigRequest()
        assert r.client_slug is None
        assert r.api_url == "https://clay.nomynoms.com"
        assert r.api_key == "{{your-api-key}}"

    def test_custom(self):
        r = ClayConfigRequest(client_slug="acme", api_key="key-123")
        assert r.client_slug == "acme"
        assert r.api_key == "key-123"


# ---------------------------------------------------------------------------
# PlayTestRequest
# ---------------------------------------------------------------------------


class TestPlayTestRequest:
    def test_defaults(self):
        r = PlayTestRequest(data={"name": "Alice"})
        assert r.model == "opus"
        assert r.instructions is None

    def test_missing_data_raises(self):
        with pytest.raises(ValidationError):
            PlayTestRequest()
