from pydantic import BaseModel


class CompanyInfo(BaseModel):
    domain: str = ""
    industry: str = ""
    size: str = ""
    stage: str = ""
    hq: str = ""
    founded: str = ""


class TonePreferences(BaseModel):
    formality: str = ""
    approach: str = ""
    avoid: str = ""


class ClientProfile(BaseModel):
    slug: str
    name: str
    company: CompanyInfo = CompanyInfo()
    what_they_sell: str = ""
    icp: str = ""
    competitive_landscape: str = ""
    recent_news: str = ""
    value_proposition: str = ""
    tone: TonePreferences = TonePreferences()
    campaign_angles: str = ""
    notes: str = ""
    personas: str = ""
    battle_cards: str = ""
    signal_playbook: str = ""
    proven_responses: str = ""
    active_campaigns: str = ""
    raw_markdown: str = ""


class ClientSummary(BaseModel):
    slug: str
    name: str
    industry: str = ""
    stage: str = ""
    domain: str = ""


class CreateClientRequest(BaseModel):
    slug: str
    name: str
    company: CompanyInfo = CompanyInfo()
    what_they_sell: str = ""
    icp: str = ""
    competitive_landscape: str = ""
    recent_news: str = ""
    value_proposition: str = ""
    tone: TonePreferences = TonePreferences()
    campaign_angles: str = ""
    notes: str = ""
    personas: str = ""
    battle_cards: str = ""
    signal_playbook: str = ""
    proven_responses: str = ""
    active_campaigns: str = ""


class UpdateClientRequest(BaseModel):
    name: str | None = None
    company: CompanyInfo | None = None
    what_they_sell: str | None = None
    icp: str | None = None
    competitive_landscape: str | None = None
    recent_news: str | None = None
    value_proposition: str | None = None
    tone: TonePreferences | None = None
    campaign_angles: str | None = None
    notes: str | None = None
    personas: str | None = None
    battle_cards: str | None = None
    signal_playbook: str | None = None
    proven_responses: str | None = None
    active_campaigns: str | None = None


class KnowledgeBaseFile(BaseModel):
    path: str
    category: str
    name: str
    content: str


class UpdateKnowledgeBaseRequest(BaseModel):
    content: str


class CreateKnowledgeBaseRequest(BaseModel):
    category: str
    filename: str
    content: str


class PromptPreviewRequest(BaseModel):
    skill: str
    client_slug: str
    sample_data: dict | None = None


class PromptPreviewResponse(BaseModel):
    assembled_prompt: str
    context_files_loaded: list[str]
    estimated_tokens: int
