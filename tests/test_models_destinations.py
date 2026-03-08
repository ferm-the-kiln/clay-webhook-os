import pytest
from pydantic import ValidationError

from app.models.destinations import (
    CreateDestinationRequest,
    Destination,
    DestinationType,
    PushDataRequest,
    PushRequest,
    PushResult,
    UpdateDestinationRequest,
)


class TestDestinationType:
    def test_values(self):
        assert DestinationType.clay_webhook == "clay_webhook"
        assert DestinationType.generic_webhook == "generic_webhook"

    def test_invalid(self):
        with pytest.raises(ValueError):
            DestinationType("email")


class TestDestination:
    def test_valid(self):
        d = Destination(
            id="d1", name="Clay", type=DestinationType.clay_webhook,
            url="http://x.com", created_at=1000.0, updated_at=1000.0,
        )
        assert d.id == "d1"
        assert d.auth_header_name == ""
        assert d.client_slug is None

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            Destination(id="d1", name="X")


class TestCreateDestinationRequest:
    def test_valid(self):
        r = CreateDestinationRequest(name="My Hook", type=DestinationType.generic_webhook, url="http://x.com")
        assert r.name == "My Hook"
        assert r.auth_header_name == ""
        assert r.client_slug is None

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            CreateDestinationRequest(name="X")


class TestUpdateDestinationRequest:
    def test_all_none(self):
        r = UpdateDestinationRequest()
        assert r.name is None
        assert r.url is None

    def test_partial(self):
        r = UpdateDestinationRequest(name="New", url="http://new.com")
        assert r.name == "New"
        assert r.auth_header_name is None


class TestPushRequest:
    def test_valid(self):
        r = PushRequest(job_ids=["j1", "j2"])
        assert len(r.job_ids) == 2

    def test_required(self):
        with pytest.raises(ValidationError):
            PushRequest()


class TestPushDataRequest:
    def test_valid(self):
        r = PushDataRequest(data={"key": "val"})
        assert r.data == {"key": "val"}


class TestPushResult:
    def test_valid(self):
        r = PushResult(destination_id="d1", destination_name="My Hook", total=5, success=4, failed=1, errors=[{"msg": "timeout"}])
        assert r.failed == 1
        assert len(r.errors) == 1

    def test_empty_errors(self):
        r = PushResult(destination_id="d1", destination_name="Hook", total=3, success=3, failed=0, errors=[])
        assert r.errors == []
        assert r.failed == 0

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            PushResult(destination_id="d1")


# ---------------------------------------------------------------------------
# Additional coverage
# ---------------------------------------------------------------------------


class TestDestinationAdditional:
    def test_with_auth_headers(self):
        d = Destination(
            id="d1", name="Secure Hook", type=DestinationType.generic_webhook,
            url="http://x.com", auth_header_name="Authorization",
            auth_header_value="Bearer tok123",
            created_at=1000.0, updated_at=1000.0,
        )
        assert d.auth_header_name == "Authorization"
        assert d.auth_header_value == "Bearer tok123"

    def test_with_client_slug(self):
        d = Destination(
            id="d1", name="Hook", type=DestinationType.clay_webhook,
            url="http://x.com", client_slug="acme",
            created_at=1000.0, updated_at=1000.0,
        )
        assert d.client_slug == "acme"

    def test_model_dump_all_fields(self):
        d = Destination(
            id="d1", name="Hook", type=DestinationType.clay_webhook,
            url="http://x.com", created_at=1000.0, updated_at=1000.0,
        )
        keys = set(d.model_dump().keys())
        assert keys == {
            "id", "name", "type", "url", "auth_header_name",
            "auth_header_value", "client_slug", "created_at", "updated_at",
        }

    def test_type_accepts_string(self):
        d = Destination(
            id="d1", name="Hook", type="generic_webhook",
            url="http://x.com", created_at=1000.0, updated_at=1000.0,
        )
        assert d.type == DestinationType.generic_webhook


class TestDestinationTypeAdditional:
    def test_is_str_enum(self):
        """DestinationType values are strings usable as str via .value."""
        assert isinstance(DestinationType.clay_webhook, str)
        assert DestinationType.clay_webhook.value == "clay_webhook"

    def test_all_members(self):
        members = list(DestinationType)
        assert len(members) == 2


class TestCreateDestinationRequestAdditional:
    def test_with_auth_headers(self):
        r = CreateDestinationRequest(
            name="Hook", type=DestinationType.generic_webhook,
            url="http://x.com", auth_header_name="X-Key", auth_header_value="secret",
        )
        assert r.auth_header_name == "X-Key"
        assert r.auth_header_value == "secret"

    def test_invalid_type(self):
        with pytest.raises(ValidationError):
            CreateDestinationRequest(name="X", type="invalid_type", url="http://x.com")


class TestUpdateDestinationRequestAdditional:
    def test_single_field_update(self):
        r = UpdateDestinationRequest(name="NewName")
        assert r.name == "NewName"
        assert r.url is None
        assert r.auth_header_name is None

    def test_model_dump_includes_none(self):
        r = UpdateDestinationRequest(name="X")
        d = r.model_dump()
        assert d["url"] is None
        assert d["name"] == "X"


class TestPushRequestAdditional:
    def test_empty_list(self):
        r = PushRequest(job_ids=[])
        assert r.job_ids == []

    def test_single_id(self):
        r = PushRequest(job_ids=["j1"])
        assert len(r.job_ids) == 1


class TestPushDataRequestAdditional:
    def test_required_data(self):
        with pytest.raises(ValidationError):
            PushDataRequest()

    def test_empty_dict(self):
        r = PushDataRequest(data={})
        assert r.data == {}

    def test_nested_data(self):
        r = PushDataRequest(data={"person": {"name": "Alice", "email": "a@b.com"}})
        assert r.data["person"]["name"] == "Alice"
