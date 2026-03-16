import json
import logging
import time
import uuid
from pathlib import Path

from app.models.datasets import Dataset, DatasetColumn, DatasetSummary

logger = logging.getLogger("clay-webhook-os")


class DatasetStore:
    """File-based dataset persistence.

    Storage layout:
        data/datasets/{dataset_id}/meta.json   — Dataset metadata + columns
        data/datasets/{dataset_id}/rows.jsonl   — One JSON object per line
    """

    def __init__(self, data_dir: Path):
        self.base_dir = data_dir / "datasets"

    def load(self):
        self.base_dir.mkdir(parents=True, exist_ok=True)
        count = sum(1 for d in self.base_dir.iterdir() if d.is_dir() and (d / "meta.json").exists())
        logger.info("[dataset_store] Loaded %d datasets", count)

    # --- CRUD ---

    def create(self, name: str, description: str = "", client_slug: str | None = None) -> Dataset:
        dataset_id = uuid.uuid4().hex[:12]
        now = time.time()
        ds = Dataset(
            id=dataset_id,
            name=name,
            description=description,
            client_slug=client_slug,
            columns=[],
            row_count=0,
            stages_completed=[],
            created_at=now,
            updated_at=now,
        )
        ds_dir = self.base_dir / dataset_id
        ds_dir.mkdir(parents=True, exist_ok=True)
        self._save_meta(ds)
        # Create empty rows file
        (ds_dir / "rows.jsonl").touch()
        logger.info("[dataset_store] Created dataset %s: %s", dataset_id, name)
        return ds

    def list_all(self) -> list[DatasetSummary]:
        summaries = []
        for d in sorted(self.base_dir.iterdir(), key=lambda p: p.name):
            meta_path = d / "meta.json"
            if not d.is_dir() or not meta_path.exists():
                continue
            meta = json.loads(meta_path.read_text())
            summaries.append(DatasetSummary(
                id=meta["id"],
                name=meta["name"],
                row_count=meta.get("row_count", 0),
                column_count=len(meta.get("columns", [])),
                stages_completed=meta.get("stages_completed", []),
                created_at=meta["created_at"],
                updated_at=meta["updated_at"],
            ))
        return summaries

    def get(self, dataset_id: str) -> Dataset | None:
        meta_path = self.base_dir / dataset_id / "meta.json"
        if not meta_path.exists():
            return None
        return Dataset.model_validate_json(meta_path.read_text())

    def update(self, dataset_id: str, **fields) -> Dataset | None:
        ds = self.get(dataset_id)
        if not ds:
            return None
        for k, v in fields.items():
            if hasattr(ds, k):
                setattr(ds, k, v)
        ds.updated_at = time.time()
        self._save_meta(ds)
        return ds

    def delete(self, dataset_id: str) -> bool:
        ds_dir = self.base_dir / dataset_id
        if not ds_dir.exists():
            return False
        # Remove all files in dataset dir
        for f in ds_dir.iterdir():
            f.unlink()
        ds_dir.rmdir()
        logger.info("[dataset_store] Deleted dataset %s", dataset_id)
        return True

    # --- Row operations ---

    def import_rows(self, dataset_id: str, rows: list[dict]) -> int:
        """Import rows into dataset. Each row gets a stable _row_id."""
        ds = self.get(dataset_id)
        if not ds:
            return 0

        rows_path = self.base_dir / dataset_id / "rows.jsonl"
        now = time.time()
        new_columns: dict[str, DatasetColumn] = {}
        existing_col_names = {c.name for c in ds.columns}

        with open(rows_path, "a") as f:
            for row in rows:
                if "_row_id" not in row:
                    row["_row_id"] = uuid.uuid4().hex[:12]
                f.write(json.dumps(row) + "\n")
                # Track new columns
                for key in row:
                    if key != "_row_id" and key not in existing_col_names and key not in new_columns:
                        new_columns[key] = DatasetColumn(
                            name=key,
                            source="import",
                            type=_infer_type(row[key]),
                            added_at=now,
                        )

        # Update metadata
        ds.columns.extend(new_columns.values())
        ds.row_count += len(rows)
        ds.updated_at = now
        self._save_meta(ds)
        logger.info("[dataset_store] Imported %d rows into %s", len(rows), dataset_id)
        return len(rows)

    def get_rows(self, dataset_id: str, offset: int = 0, limit: int = 100) -> tuple[list[dict], int]:
        """Return (rows, total_count) with pagination."""
        rows_path = self.base_dir / dataset_id / "rows.jsonl"
        if not rows_path.exists():
            return [], 0

        all_rows = []
        with open(rows_path) as f:
            for line in f:
                line = line.strip()
                if line:
                    all_rows.append(json.loads(line))

        total = len(all_rows)
        page = all_rows[offset : offset + limit]
        return page, total

    def update_rows(self, dataset_id: str, updates: dict[str, dict]) -> int:
        """Update rows by _row_id. updates = {row_id: {col: val, ...}}."""
        rows_path = self.base_dir / dataset_id / "rows.jsonl"
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

        # Rewrite file
        with open(rows_path, "w") as f:
            for row in all_rows:
                f.write(json.dumps(row) + "\n")

        # Update column metadata if new columns were added
        ds = self.get(dataset_id)
        if ds:
            existing_col_names = {c.name for c in ds.columns}
            now = time.time()
            for row_updates in updates.values():
                for key, val in row_updates.items():
                    if key != "_row_id" and key not in existing_col_names:
                        ds.columns.append(DatasetColumn(
                            name=key,
                            source="stage",
                            type=_infer_type(val),
                            added_at=now,
                        ))
                        existing_col_names.add(key)
            ds.updated_at = now
            self._save_meta(ds)

        return updated_count

    def export_csv(self, dataset_id: str) -> str | None:
        """Export dataset as CSV string."""
        rows_path = self.base_dir / dataset_id / "rows.jsonl"
        if not rows_path.exists():
            return None

        all_rows = []
        all_keys: list[str] = []
        seen_keys: set[str] = set()

        with open(rows_path) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                row = json.loads(line)
                all_rows.append(row)
                for k in row:
                    if k != "_row_id" and k not in seen_keys:
                        all_keys.append(k)
                        seen_keys.add(k)

        if not all_rows:
            return ""

        import csv
        import io

        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=all_keys, extrasaction="ignore")
        writer.writeheader()
        for row in all_rows:
            writer.writerow({k: row.get(k, "") for k in all_keys})
        return output.getvalue()

    # --- Internal ---

    def _save_meta(self, ds: Dataset):
        meta_path = self.base_dir / ds.id / "meta.json"
        meta_path.write_text(ds.model_dump_json(indent=2))

    # --- Stage tracking ---

    def add_stage_columns(self, dataset_id: str, stage: str, columns: dict[str, str]):
        """Register new columns from a stage execution. columns = {name: type}."""
        ds = self.get(dataset_id)
        if not ds:
            return
        now = time.time()
        existing = {c.name for c in ds.columns}
        for col_name, col_type in columns.items():
            if col_name not in existing:
                ds.columns.append(DatasetColumn(
                    name=col_name,
                    source=stage,
                    type=col_type,
                    added_at=now,
                ))
        if stage not in ds.stages_completed:
            ds.stages_completed.append(stage)
        ds.updated_at = now
        self._save_meta(ds)


def _infer_type(value) -> str:
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int | float):
        return "number"
    if isinstance(value, dict):
        return "json"
    if isinstance(value, list):
        return "json"
    if isinstance(value, str):
        if "@" in value and "." in value:
            return "email"
        return "string"
    return "string"
