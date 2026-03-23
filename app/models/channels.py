from pydantic import BaseModel, Field, model_validator


class ChannelMessage(BaseModel):
    role: str = Field(..., description="Message role: user or assistant")
    content: str = Field("", description="Message text content")
    timestamp: float = Field(..., description="Unix timestamp")
    data: list[dict] | None = Field(None, description="Data rows sent with message")
    results: list[dict] | None = Field(None, description="Execution results")
    execution_id: str | None = Field(None, description="Linked execution ID")


class ChannelSession(BaseModel):
    id: str = Field(..., description="Session ID (12-char hex)")
    function_id: str = Field(..., description="Function used in this session")
    title: str = Field("", description="Session title")
    messages: list[ChannelMessage] = Field(default_factory=list)
    created_at: float = Field(..., description="Unix timestamp")
    updated_at: float = Field(..., description="Unix timestamp")
    status: str = Field("active", description="Session status: active or archived")
    client_slug: str | None = Field(None, description="Client slug for client-scoped sessions")


class CreateSessionRequest(BaseModel):
    function_id: str = Field(..., description="Function to use in this session")
    title: str = Field("", description="Optional session title")
    client_slug: str | None = Field(None, description="Client slug for client-scoped sessions")

    @model_validator(mode="after")
    def validate_function_id(self) -> "CreateSessionRequest":
        if not self.function_id.strip():
            raise ValueError("function_id cannot be empty")
        return self


class SendMessageRequest(BaseModel):
    content: str = Field("", description="User message text")
    data: list[dict] = Field(..., description="Data rows to process")


class SessionSummary(BaseModel):
    id: str
    function_id: str
    function_name: str = ""
    title: str
    message_count: int = 0
    created_at: float
    updated_at: float
    status: str = "active"
    client_slug: str | None = None
