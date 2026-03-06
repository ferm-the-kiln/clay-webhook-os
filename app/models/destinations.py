from enum import Enum

from pydantic import BaseModel


class DestinationType(str, Enum):
    clay_webhook = "clay_webhook"
    generic_webhook = "generic_webhook"


class Destination(BaseModel):
    id: str
    name: str
    type: DestinationType
    url: str
    auth_header_name: str = ""
    auth_header_value: str = ""
    client_slug: str | None = None
    created_at: float
    updated_at: float


class CreateDestinationRequest(BaseModel):
    name: str
    type: DestinationType
    url: str
    auth_header_name: str = ""
    auth_header_value: str = ""
    client_slug: str | None = None


class UpdateDestinationRequest(BaseModel):
    name: str | None = None
    url: str | None = None
    auth_header_name: str | None = None
    auth_header_value: str | None = None
    client_slug: str | None = None


class PushRequest(BaseModel):
    job_ids: list[str]


class PushResult(BaseModel):
    destination_id: str
    destination_name: str
    total: int
    success: int
    failed: int
    errors: list[dict]
