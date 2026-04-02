import json
import logging
import re
import time
import uuid
from pathlib import Path

from app.core.atomic_writer import atomic_write_text
from app.models.tables import (
    AddColumnRequest,
    TableColumn,
    TableDefinition,
    TableSummary,
    UpdateColumnRequest,
)

logger = logging.getLogger("clay-webhook-os")

_TEMPLATE_RE = re.compile(r"\{\{(\w+)\}\}")


def _slugify(name: str) -> str:
    """Convert display name to a slug ID."""
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "column"


def _compute_depends_on(params: dict[str, str], formula: str | None) -> list[str]:
    """Extract column references from params and formula."""
    refs: set[str] = set()
    for val in params.values():
        refs.update(_TEMPLATE_RE.findall(val))
    if formula:
        refs.update(_TEMPLATE_RE.findall(formula))
    return sorted(refs)


class TableStore:
    """File-based table persistence.

    Storage layout:
        data/tables/{table_id}/meta.json   -- TableDefinition metadata + columns
        data/tables/{table_id}/rows.jsonl   -- One JSON object per line
    """

    def __init__(self, data_dir: Path):
        self.base_dir = data_dir / "tables"

    def load(self):
        self.base_dir.mkdir(parents=True, exist_ok=True)
        count = sum(1 for d in self.base_dir.iterdir() if d.is_dir() and (d / "meta.json").exists())
        logger.info("[table_store] Loaded %d tables", count)

    # --- CRUD ---

    def create(self, name: str, description: str = "") -> TableDefinition:
        table_id = uuid.uuid4().hex[:12]
        now = time.time()
        table = TableDefinition(
            id=table_id,
            name=name,
            description=description,
            columns=[],
            row_count=0,
            created_at=now,
            updated_at=now,
        )
        table_dir = self.base_dir / table_id
        table_dir.mkdir(parents=True, exist_ok=True)
        self._save_meta(table)
        (table_dir / "rows.jsonl").touch()
        logger.info("[table_store] Created table %s: %s", table_id, name)
        return table

    def list_all(self) -> list[TableSummary]:
        summaries = []
        for d in sorted(self.base_dir.iterdir(), key=lambda p: p.name):
            meta_path = d / "meta.json"
            if not d.is_dir() or not meta_path.exists():
                continue
            meta = json.loads(meta_path.read_text())
            summaries.append(TableSummary(
                id=meta["id"],
                name=meta["name"],
                description=meta.get("description", ""),
                row_count=meta.get("row_count", 0),
                column_count=len(meta.get("columns", [])),
                created_at=meta["created_at"],
                updated_at=meta["updated_at"],
            ))
        return summaries

    def get(self, table_id: str) -> TableDefinition | None:
        meta_path = self.base_dir / table_id / "meta.json"
        if not meta_path.exists():
            return None
        return TableDefinition.model_validate_json(meta_path.read_text())

    def update(self, table_id: str, **fields) -> TableDefinition | None:
        table = self.get(table_id)
        if not table:
            return None
        for k, v in fields.items():
            if hasattr(table, k) and v is not None:
                setattr(table, k, v)
        table.updated_at = time.time()
        self._save_meta(table)
        return table

    def delete(self, table_id: str) -> bool:
        table_dir = self.base_dir / table_id
        if not table_dir.exists():
            return False
        for f in table_dir.iterdir():
            f.unlink()
        table_dir.rmdir()
        logger.info("[table_store] Deleted table %s", table_id)
        return True

    # --- Column operations ---

    def add_column(self, table_id: str, req: AddColumnRequest) -> TableDefinition | None:
        table = self.get(table_id)
        if not table:
            return None

        # Generate unique slug ID
        slug = _slugify(req.name)
        existing_ids = {c.id for c in table.columns}
        final_id = slug
        counter = 2
        while final_id in existing_ids:
            final_id = f"{slug}_{counter}"
            counter += 1

        # Determine position
        position = req.position if req.position is not None else len(table.columns)

        # Compute dependencies
        depends_on = _compute_depends_on(req.params, req.formula)
        if req.parent_column_id:
            depends_on = sorted(set(depends_on) | {req.parent_column_id})

        col = TableColumn(
            id=final_id,
            name=req.name,
            column_type=req.column_type,
            position=position,
            width=req.width,
            frozen=req.frozen,
            color=req.color,
            tool=req.tool,
            params=req.params,
            output_key=req.output_key,
            ai_prompt=req.ai_prompt,
            ai_model=req.ai_model,
            formula=req.formula,
            condition=req.condition,
            condition_label=req.condition_label,
            parent_column_id=req.parent_column_id,
            extract_path=req.extract_path,
            depends_on=depends_on,
        )

        # Shift positions of columns at or after the insertion point
        for c in table.columns:
            if c.position >= position:
                c.position += 1

        table.columns.append(col)
        table.columns.sort(key=lambda c: c.position)
        table.updated_at = time.time()
        self._save_meta(table)
        logger.info("[table_store] Added column %s to table %s", final_id, table_id)
        return table

    def update_column(self, table_id: str, column_id: str, req: UpdateColumnRequest) -> TableDefinition | None:
        table = self.get(table_id)
        if not table:
            return None

        col = next((c for c in table.columns if c.id == column_id), None)
        if not col:
            return None

        update_data = req.model_dump(exclude_none=True)
        for k, v in update_data.items():
            setattr(col, k, v)

        # Recompute dependencies
        col.depends_on = _compute_depends_on(col.params, col.formula)
        if col.parent_column_id:
            col.depends_on = sorted(set(col.depends_on) | {col.parent_column_id})

        table.updated_at = time.time()
        self._save_meta(table)
        return table

    def remove_column(self, table_id: str, column_id: str) -> TableDefinition | None:
        table = self.get(table_id)
        if not table:
            return None

        removed_pos = None
        new_cols = []
        for c in table.columns:
            if c.id == column_id:
                removed_pos = c.position
            else:
                new_cols.append(c)
        table.columns = new_cols

        # Renumber positions
        if removed_pos is not None:
            for c in table.columns:
                if c.position > removed_pos:
                    c.position -= 1

        table.updated_at = time.time()
        self._save_meta(table)

        # Remove column data from rows
        self._remove_column_from_rows(table_id, column_id)

        logger.info("[table_store] Removed column %s from table %s", column_id, table_id)
        return table

    def reorder_columns(self, table_id: str, column_ids: list[str]) -> TableDefinition | None:
        table = self.get(table_id)
        if not table:
            return None

        id_to_col = {c.id: c for c in table.columns}
        for i, col_id in enumerate(column_ids):
            if col_id in id_to_col:
                id_to_col[col_id].position = i

        # Assign positions to any columns not in the reorder list
        next_pos = len(column_ids)
        for c in table.columns:
            if c.id not in set(column_ids):
                c.position = next_pos
                next_pos += 1

        table.columns.sort(key=lambda c: c.position)
        table.updated_at = time.time()
        self._save_meta(table)
        return table

    # --- Row operations ---

    def import_rows(self, table_id: str, rows: list[dict]) -> int:
        table = self.get(table_id)
        if not table:
            return 0

        rows_path = self.base_dir / table_id / "rows.jsonl"

        # Auto-detect input columns from first row
        existing_col_ids = {c.id for c in table.columns}
        now = time.time()
        new_columns: list[TableColumn] = []

        if rows:
            sample = rows[0]
            pos = max((c.position for c in table.columns), default=-1) + 1
            for key in sample:
                if key == "_row_id":
                    continue
                slug = _slugify(key)
                if slug not in existing_col_ids:
                    new_columns.append(TableColumn(
                        id=slug,
                        name=key,
                        column_type="input",
                        position=pos,
                        frozen=pos == 0,
                    ))
                    existing_col_ids.add(slug)
                    pos += 1

        with open(rows_path, "a") as f:
            for row in rows:
                if "_row_id" not in row:
                    row["_row_id"] = uuid.uuid4().hex[:12]
                # Store input values using column_id__value convention
                stored = {"_row_id": row["_row_id"]}
                for key, val in row.items():
                    if key == "_row_id":
                        continue
                    col_id = _slugify(key)
                    stored[f"{col_id}__value"] = val
                    stored[f"{col_id}__status"] = "done"
                f.write(json.dumps(stored) + "\n")

        if new_columns:
            table.columns.extend(new_columns)
            table.columns.sort(key=lambda c: c.position)
        table.row_count += len(rows)
        table.updated_at = now
        self._save_meta(table)

        logger.info("[table_store] Imported %d rows into table %s", len(rows), table_id)
        return len(rows)

    def get_rows(self, table_id: str, offset: int = 0, limit: int = 100) -> tuple[list[dict], int]:
        rows_path = self.base_dir / table_id / "rows.jsonl"
        if not rows_path.exists():
            return [], 0

        page = []
        total = 0
        end = offset + limit
        with open(rows_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                if offset <= total < end:
                    page.append(json.loads(line))
                total += 1
        return page, total

    def add_row(self, table_id: str, data: dict) -> dict | None:
        table = self.get(table_id)
        if not table:
            return None

        row = {"_row_id": uuid.uuid4().hex[:12]}
        for key, val in data.items():
            col_id = _slugify(key)
            row[f"{col_id}__value"] = val
            row[f"{col_id}__status"] = "done"

        rows_path = self.base_dir / table_id / "rows.jsonl"
        with open(rows_path, "a") as f:
            f.write(json.dumps(row) + "\n")

        table.row_count += 1
        table.updated_at = time.time()
        self._save_meta(table)
        return row

    def delete_rows(self, table_id: str, row_ids: list[str]) -> int:
        rows_path = self.base_dir / table_id / "rows.jsonl"
        if not rows_path.exists():
            return 0

        ids_to_delete = set(row_ids)
        kept = []
        deleted = 0
        with open(rows_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                if row.get("_row_id") in ids_to_delete:
                    deleted += 1
                else:
                    kept.append(row)

        content = "".join(json.dumps(r) + "\n" for r in kept)
        atomic_write_text(rows_path, content)

        table = self.get(table_id)
        if table:
            table.row_count = max(0, table.row_count - deleted)
            table.updated_at = time.time()
            self._save_meta(table)

        return deleted

    def update_cells(self, table_id: str, updates: dict[str, dict]) -> int:
        """Update cells by row_id. updates = {row_id: {col_id__status: ..., col_id__value: ..., ...}}."""
        rows_path = self.base_dir / table_id / "rows.jsonl"
        if not rows_path.exists():
            return 0

        all_rows = []
        updated_count = 0
        with open(rows_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                row_id = row.get("_row_id")
                if row_id and row_id in updates:
                    row.update(updates[row_id])
                    updated_count += 1
                all_rows.append(row)

        content = "".join(json.dumps(row) + "\n" for row in all_rows)
        atomic_write_text(rows_path, content)
        return updated_count

    # --- Internal ---

    def _save_meta(self, table: TableDefinition):
        meta_path = self.base_dir / table.id / "meta.json"
        atomic_write_text(meta_path, table.model_dump_json(indent=2))

    def _remove_column_from_rows(self, table_id: str, column_id: str):
        """Remove all cell data for a column from rows."""
        rows_path = self.base_dir / table_id / "rows.jsonl"
        if not rows_path.exists():
            return

        prefix = f"{column_id}__"
        all_rows = []
        with open(rows_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                row = {k: v for k, v in row.items() if not k.startswith(prefix)}
                all_rows.append(row)

        content = "".join(json.dumps(row) + "\n" for row in all_rows)
        atomic_write_text(rows_path, content)
