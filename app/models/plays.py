from enum import Enum

from pydantic import BaseModel, Field


class PlayCategory(str, Enum):
    outbound = "outbound"
    research = "research"
    meeting_prep = "meeting-prep"
    nurture = "nurture"
    competitive = "competitive"
    custom = "custom"


class SchemaField(BaseModel):
    name: str
    type: str = "string"
    required: bool = False
    description: str = ""
    example: str | None = None


class PlayDefinition(BaseModel):
    name: str
    display_name: str
    description: str = ""
    category: PlayCategory
    pipeline: str
    input_schema: list[SchemaField] = []
    output_schema: list[SchemaField] = []
    when_to_use: str = ""
    who_its_for: str = ""
    default_model: str = "opus"
    default_confidence_threshold: float = 0.8
    default_instructions: str | None = None
    tags: list[str] = []
    is_template: bool = True
    forked_from: str | None = None
    created_at: float = 0.0


class CreatePlayRequest(BaseModel):
    name: str = Field(..., pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    display_name: str
    description: str = ""
    category: PlayCategory
    pipeline: str
    input_schema: list[SchemaField] = []
    output_schema: list[SchemaField] = []
    when_to_use: str = ""
    who_its_for: str = ""
    default_model: str = "opus"
    default_confidence_threshold: float = 0.8
    default_instructions: str | None = None
    tags: list[str] = []


class UpdatePlayRequest(BaseModel):
    display_name: str | None = None
    description: str | None = None
    category: PlayCategory | None = None
    pipeline: str | None = None
    input_schema: list[SchemaField] | None = None
    output_schema: list[SchemaField] | None = None
    when_to_use: str | None = None
    who_its_for: str | None = None
    default_model: str | None = None
    default_confidence_threshold: float | None = None
    default_instructions: str | None = None
    tags: list[str] | None = None


class ForkPlayRequest(BaseModel):
    new_name: str = Field(..., pattern=r"^[a-z0-9][a-z0-9-]*[a-z0-9]$")
    display_name: str
    client_slug: str | None = None
    default_model: str | None = None
    default_confidence_threshold: float | None = None
    default_instructions: str | None = None


class ClayConfigRequest(BaseModel):
    client_slug: str | None = None
    api_url: str = "https://clay.nomynoms.com"
    api_key: str = "{{your-api-key}}"


class PlayTestRequest(BaseModel):
    data: dict
    model: str = "opus"
    instructions: str | None = None
