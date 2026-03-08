from pydantic import BaseModel, Field


class BuyingSignal(BaseModel):
    signal_type: str = Field(..., description="Signal category: funding, hiring, leadership_change, product_launch, partnership, acquisition, expansion, tech_stack_change")
    headline: str = Field(..., description="One-line signal summary")
    detail: str = Field(..., description="2-3 sentence explanation with specifics")
    source_url: str | None = Field(None, description="URL where this signal was found")
    days_ago: int | None = Field(None, description="Approximate days since the signal occurred")
    effective_score: float = Field(..., description="base_score * decay_multiplier (0.0-30.0)")
    relevance_to_client: str = Field(..., description="Why this signal matters for the client's product")
    recommended_contact: str = Field(..., description="Title of the person to reach out to")
    urgency: str = Field(..., description="high, medium, or low")


class SignalResearchResult(BaseModel):
    company_name: str = Field(..., description="Company researched")
    company_domain: str = Field(..., description="Company domain")
    company_summary: str = Field(..., description="1-2 sentence company description based on research")
    signals: list[BuyingSignal] = Field(..., description="Top 3 buying signals ranked by effective_score")
    priority_tier: str = Field(..., description="tier_1_now, tier_2_soon, tier_3_watch, or tier_4_pass")
    confidence_score: float = Field(..., description="0.0-1.0 confidence in the research quality")
    recommended_approach: str = Field(..., description="2-3 sentence outreach strategy based on signals found")
