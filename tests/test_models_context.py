import pytest
from pydantic import ValidationError

from app.models.context import (
    ClientProfile,
    ClientSummary,
    CompanyInfo,
    CreateClientRequest,
    CreateKnowledgeBaseRequest,
    KnowledgeBaseFile,
    PromptPreviewRequest,
    PromptPreviewResponse,
    TonePreferences,
    UpdateClientRequest,
    UpdateKnowledgeBaseRequest,
)


class TestCompanyInfo:
    def test_defaults(self):
        c = CompanyInfo()
        assert c.domain == ""
        assert c.industry == ""
        assert c.size == ""
        assert c.stage == ""
        assert c.hq == ""
        assert c.founded == ""

    def test_all_fields(self):
        c = CompanyInfo(domain="acme.com", industry="SaaS", size="50-200", stage="Series B", hq="NYC", founded="2020")
        assert c.domain == "acme.com"


class TestTonePreferences:
    def test_defaults(self):
        t = TonePreferences()
        assert t.formality == ""
        assert t.approach == ""
        assert t.avoid == ""


class TestClientProfile:
    def test_required_fields(self):
        p = ClientProfile(slug="acme", name="Acme Corp")
        assert p.slug == "acme"
        assert p.name == "Acme Corp"

    def test_missing_slug_raises(self):
        with pytest.raises(ValidationError):
            ClientProfile(name="Acme")

    def test_missing_name_raises(self):
        with pytest.raises(ValidationError):
            ClientProfile(slug="acme")

    def test_defaults(self):
        p = ClientProfile(slug="x", name="X")
        assert isinstance(p.company, CompanyInfo)
        assert p.what_they_sell == ""
        assert p.icp == ""
        assert p.raw_markdown == ""
        assert p.personas == ""
        assert p.battle_cards == ""

    def test_nested_company(self):
        p = ClientProfile(slug="x", name="X", company=CompanyInfo(domain="x.com"))
        assert p.company.domain == "x.com"


class TestClientSummary:
    def test_required_fields(self):
        s = ClientSummary(slug="acme", name="Acme")
        assert s.industry == ""

    def test_optional_fields(self):
        s = ClientSummary(slug="x", name="X", industry="Tech", stage="Seed", domain="x.com")
        assert s.stage == "Seed"


class TestCreateClientRequest:
    def test_required_fields(self):
        r = CreateClientRequest(slug="acme", name="Acme Corp")
        assert r.slug == "acme"

    def test_defaults_match_profile(self):
        r = CreateClientRequest(slug="x", name="X")
        assert r.what_they_sell == ""
        assert isinstance(r.company, CompanyInfo)
        assert isinstance(r.tone, TonePreferences)


class TestUpdateClientRequest:
    def test_all_none_by_default(self):
        r = UpdateClientRequest()
        assert r.name is None
        assert r.company is None
        assert r.what_they_sell is None
        assert r.icp is None
        assert r.tone is None

    def test_partial_update(self):
        r = UpdateClientRequest(name="New Name", icp="Enterprise")
        assert r.name == "New Name"
        assert r.icp == "Enterprise"
        assert r.company is None


class TestKnowledgeBaseFile:
    def test_valid(self):
        f = KnowledgeBaseFile(path="voice/default.md", category="voice", name="default.md", content="# Voice")
        assert f.path == "voice/default.md"

    def test_required_fields(self):
        with pytest.raises(ValidationError):
            KnowledgeBaseFile(path="x", category="y")


class TestUpdateKnowledgeBaseRequest:
    def test_valid(self):
        r = UpdateKnowledgeBaseRequest(content="Updated content")
        assert r.content == "Updated content"

    def test_content_required(self):
        with pytest.raises(ValidationError):
            UpdateKnowledgeBaseRequest()


class TestCreateKnowledgeBaseRequest:
    def test_valid(self):
        r = CreateKnowledgeBaseRequest(category="voice", filename="casual.md", content="# Casual")
        assert r.category == "voice"

    def test_all_required(self):
        with pytest.raises(ValidationError):
            CreateKnowledgeBaseRequest(category="x")


class TestPromptPreviewRequest:
    def test_valid(self):
        r = PromptPreviewRequest(skill="email-gen", client_slug="acme")
        assert r.sample_data is None

    def test_with_sample_data(self):
        r = PromptPreviewRequest(skill="x", client_slug="y", sample_data={"name": "Alice"})
        assert r.sample_data == {"name": "Alice"}


class TestPromptPreviewResponse:
    def test_valid(self):
        r = PromptPreviewResponse(
            assembled_prompt="Hello", context_files_loaded=["a.md", "b.md"], estimated_tokens=150
        )
        assert r.estimated_tokens == 150
        assert len(r.context_files_loaded) == 2
