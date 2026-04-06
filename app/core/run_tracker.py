"""Table execution run tracker — persists execution history.

Each table execution gets a run ID with per-column stats.
Stored at data/runs/{table_id}/{run_id}.json.
"""

import json
import logging
import time
import uuid
from pathlib import Path

from pydantic import BaseModel, Field

from app.core.atomic_writer import atomic_write_text

logger = logging.getLogger("clay-webhook-os")

MAX_RUNS_PER_TABLE = 50


class ColumnSummary(BaseModel):
    column_id: str
    column_name: str = ""
    column_type: str = ""
    success: int = 0
    errors: int = 0
    skipped: int = 0
    duration_ms: int = 0


class RunError(BaseModel):
    row_id: str
    column_id: str
    error: str


class RunState(BaseModel):
    run_id: str
    table_id: str
    table_name: str = ""
    status: str = "running"  # running | completed | failed | aborted
    started_at: str = ""
    completed_at: str | None = None
    duration_ms: int | None = None
    total_rows: int = 0
    processed_rows: int = 0
    column_summaries: list[ColumnSummary] = Field(default_factory=list)
    errors: list[RunError] = Field(default_factory=list)
    halted: bool = False


class RunTracker:
    """Tracks table execution runs and persists history."""

    def __init__(self, data_dir: str | Path):
        self._base = Path(data_dir) / "runs"
        self._base.mkdir(parents=True, exist_ok=True)

    def create_run(self, table_id: str, table_name: str, total_rows: int, columns: list[dict]) -> RunState:
        """Create a new run and return its state."""
        run_id = uuid.uuid4().hex[:8]
        run = RunState(
            run_id=run_id,
            table_id=table_id,
            table_name=table_name,
            status="running",
            started_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            total_rows=total_rows,
            column_summaries=[
                ColumnSummary(
                    column_id=c.get("id", ""),
                    column_name=c.get("name", ""),
                    column_type=c.get("column_type", ""),
                )
                for c in columns
            ],
        )
        self._save(run)
        return run

    def record_cell(self, run: RunState, column_id: str, status: str, error: str | None = None, row_id: str = "") -> None:
        """Record a cell result."""
        summary = next((s for s in run.column_summaries if s.column_id == column_id), None)
        if not summary:
            return
        if status == "done":
            summary.success += 1
        elif status == "error":
            summary.errors += 1
            if error and len(run.errors) < 100:
                run.errors.append(RunError(row_id=row_id, column_id=column_id, error=error[:200]))
        elif status in ("skipped", "filtered"):
            summary.skipped += 1

    def record_column_complete(self, run: RunState, column_id: str, duration_ms: int) -> None:
        """Record column completion with duration."""
        summary = next((s for s in run.column_summaries if s.column_id == column_id), None)
        if summary:
            summary.duration_ms = duration_ms

    def finalize(self, run: RunState, halted: bool = False) -> None:
        """Finalize a run — set status, duration, save."""
        run.completed_at = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        total_errors = sum(s.errors for s in run.column_summaries)
        run.processed_rows = max(s.success + s.errors + s.skipped for s in run.column_summaries) if run.column_summaries else 0
        run.halted = halted

        if halted:
            run.status = "aborted"
        elif total_errors > 0 and run.processed_rows == 0:
            run.status = "failed"
        else:
            run.status = "completed"

        # Calculate duration from started_at
        try:
            start = time.mktime(time.strptime(run.started_at, "%Y-%m-%dT%H:%M:%SZ"))
            run.duration_ms = int((time.time() - start) * 1000)
        except Exception:
            pass

        self._save(run)
        self._prune(run.table_id)
        logger.info("[run_tracker] Finalized run %s for table %s: %s", run.run_id, run.table_id, run.status)

    def get_run(self, table_id: str, run_id: str) -> RunState | None:
        """Load a specific run."""
        path = self._base / table_id / f"{run_id}.json"
        if not path.exists():
            return None
        try:
            return RunState(**json.loads(path.read_text()))
        except Exception:
            return None

    def list_runs(self, table_id: str, limit: int = 20) -> list[RunState]:
        """List recent runs for a table, newest first."""
        table_dir = self._base / table_id
        if not table_dir.exists():
            return []

        runs = []
        for f in sorted(table_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True):
            if len(runs) >= limit:
                break
            try:
                runs.append(RunState(**json.loads(f.read_text())))
            except Exception:
                continue
        return runs

    def _save(self, run: RunState) -> None:
        """Persist run state to disk."""
        table_dir = self._base / run.table_id
        table_dir.mkdir(parents=True, exist_ok=True)
        path = table_dir / f"{run.run_id}.json"
        atomic_write_text(path, json.dumps(run.model_dump(), indent=2))

    def _prune(self, table_id: str) -> None:
        """Keep only the most recent N runs per table."""
        table_dir = self._base / table_id
        if not table_dir.exists():
            return
        files = sorted(table_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
        for f in files[MAX_RUNS_PER_TABLE:]:
            f.unlink(missing_ok=True)
