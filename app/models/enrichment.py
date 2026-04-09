from pydantic import BaseModel, Field, model_validator


class FindEmailRequest(BaseModel):
    name: str | None = Field(None, description="Person's full name (required with domain)")
    domain: str | None = Field(None, description="Company domain (required with name)")
    linkedin_url: str | None = Field(None, description="LinkedIn profile URL (alternative to name+domain)")

    @model_validator(mode="after")
    def validate_name_domain_or_linkedin(self) -> "FindEmailRequest":
        has_name_domain = self.name and self.domain
        has_linkedin = bool(self.linkedin_url)
        if not has_name_domain and not has_linkedin:
            raise ValueError("Provide name+domain or linkedin_url")
        return self


class FindPhoneRequest(BaseModel):
    linkedin_url: str = Field(..., description="LinkedIn profile URL")


class VerifyEmailRequest(BaseModel):
    email: str = Field(..., description="Email address to verify")


class ReverseEmailLookupRequest(BaseModel):
    email: str = Field(..., description="Email address to lookup")
    with_profile: bool = Field(False, description="Include full LinkedIn profile data")


class EnrichCompanyRequest(BaseModel):
    domain: str | None = Field(None, description="Company domain")
    linkedin_url: str | None = Field(None, description="LinkedIn company page URL")
    name: str | None = Field(None, description="Company name")

    @model_validator(mode="after")
    def validate_at_least_one(self) -> "EnrichCompanyRequest":
        if not self.domain and not self.linkedin_url and not self.name:
            raise ValueError("Provide at least one of: domain, linkedin_url, name")
        return self


class GenerateLeadListRequest(BaseModel):
    query: str = Field(..., description="Natural language search query (max 1000 chars)")
    target_job_titles: list[str] | None = Field(None, description="Job titles to target")
    mode: str = Field("broad", description="'broad' or 'targeted'")
    find_contact: bool = Field(True, description="Search for contacts at each company")
    find_email: bool = Field(True, description="Enrich contacts with email")
    find_phone: bool = Field(False, description="Enrich contacts with phone")
    limit: int = Field(100, description="Max results (default 100, max 5000)")


class GetLeadListResultsRequest(BaseModel):
    hash: str = Field(..., description="Hash returned by generate_lead_list")


class SumbleFindPeopleRequest(BaseModel):
    domain: str = Field(..., description="Company domain (e.g. stripe.com)")
    job_functions: list[str] | None = Field(None, description="Job functions to filter (e.g. Engineering, Executive)")
    job_levels: list[str] | None = Field(None, description="Job levels to filter (e.g. VP, Director, C-Level)")
    limit: int = Field(10, description="Max people to return (default 10)")
