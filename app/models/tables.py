from enum import Enum

from pydantic import BaseModel, Field


class CellState(str, Enum):
    EMPTY = "empty"
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"
    SKIPPED = "skipped"
    FILTERED = "filtered"


class TableColumn(BaseModel):
    id: str = Field(..., description="Slug identifier, e.g. 'company_domain'")
    name: str = Field(..., description="Display name")
    column_type: str = Field(..., description="input | enrichment | ai | formula | gate | static")
    position: int = Field(..., description="Left-to-right order (0-based)")
    width: int = Field(180, description="Pixel width for UI")
    frozen: bool = Field(False, description="Pinned to left edge")
    color: str | None = Field(None, description="Header color override")
    hidden: bool = Field(False, description="Hidden from grid")

    # Enrichment config
    tool: str | None = Field(None, description="Provider from tool catalog, skill:*, or function:*")
    params: dict[str, str] = Field(default_factory=dict, description="Params with {{column_id}} references")
    output_key: str | None = Field(None, description="Which result key to display in this column")

    # AI column config
    ai_prompt: str | None = Field(None, description="Natural language prompt for AI columns")
    ai_model: str = Field("sonnet", description="Model for AI columns")

    # Formula config
    formula: str | None = Field(None, description="Template string e.g. '{{first_name}} {{last_name}}'")

    # Gate config
    condition: str | None = Field(None, description="Filter condition e.g. 'employee_count >= 50'")
    condition_label: str | None = Field(None, description="Human-readable condition label")

    # Parent-child
    parent_column_id: str | None = Field(None, description="Parent column ID for child extraction")
    extract_path: str | None = Field(None, description="JSON path to extract from parent e.g. 'funding.total_raised'")

    # Dependencies (auto-computed from params/formula)
    depends_on: list[str] = Field(default_factory=list, description="Column IDs this column depends on")


class TableDefinition(BaseModel):
    id: str
    name: str
    description: str = ""
    columns: list[TableColumn] = []
    row_count: int = 0
    created_at: float
    updated_at: float
    source_function_id: str | None = None


class TableSummary(BaseModel):
    id: str
    name: str
    description: str = ""
    row_count: int = 0
    column_count: int = 0
    created_at: float
    updated_at: float


# --- Request / Response models ---

class CreateTableRequest(BaseModel):
    name: str = Field(..., description="Table name")
    description: str = Field("", description="Optional description")


class UpdateTableRequest(BaseModel):
    name: str | None = None
    description: str | None = None


class AddColumnRequest(BaseModel):
    name: str = Field(..., description="Display name")
    column_type: str = Field(..., description="input | enrichment | ai | formula | gate | static")
    position: int | None = Field(None, description="Position (null = append to end)")
    width: int = Field(180, description="Pixel width")
    frozen: bool = False
    color: str | None = None

    # Enrichment
    tool: str | None = None
    params: dict[str, str] = Field(default_factory=dict)
    output_key: str | None = None

    # AI
    ai_prompt: str | None = None
    ai_model: str = "sonnet"

    # Formula
    formula: str | None = None

    # Gate
    condition: str | None = None
    condition_label: str | None = None

    # Parent-child
    parent_column_id: str | None = None
    extract_path: str | None = None


class UpdateColumnRequest(BaseModel):
    name: str | None = None
    position: int | None = None
    width: int | None = None
    frozen: bool | None = None
    color: str | None = None
    hidden: bool | None = None
    tool: str | None = None
    params: dict[str, str] | None = None
    output_key: str | None = None
    ai_prompt: str | None = None
    ai_model: str | None = None
    formula: str | None = None
    condition: str | None = None
    condition_label: str | None = None
    parent_column_id: str | None = None
    extract_path: str | None = None


class ReorderColumnsRequest(BaseModel):
    column_ids: list[str] = Field(..., description="Ordered list of column IDs")


class ImportRowsRequest(BaseModel):
    rows: list[dict] = Field(..., description="List of row objects")


class DeleteRowsRequest(BaseModel):
    row_ids: list[str] = Field(..., description="Row IDs to delete")


class ExecuteTableRequest(BaseModel):
    row_ids: list[str] | None = Field(None, description="Row IDs to execute (null = all)")
    column_ids: list[str] | None = Field(None, description="Column IDs to execute (null = all enrichment columns)")
    model: str = Field("sonnet", description="Model override")
    limit: int | None = Field(None, description="Limit rows to process (e.g. 10 for 'Save & Run 10')")
