"""Tests for ExecutionHistory store."""

import json
import time

import pytest

from app.core.execution_history import ExecutionHistory


@pytest.fixture
def history(tmp_path):
    return ExecutionHistory(data_dir=str(tmp_path))


def _make_record(function_id="test-func", status="success", **kwargs):
    return {
        "function_id": function_id,
        "timestamp": time.time(),
        "inputs": {"company_name": "Acme"},
        "outputs": {"domain": "acme.com"},
        "trace": [{"step_index": 0, "tool": "findymail", "status": "success", "duration_ms": 100}],
        "duration_ms": 1200,
        "status": status,
        "warnings": [],
        "step_count": 1,
        **kwargs,
    }


class TestSave:
    def test_save_returns_id(self, history):
        rec = _make_record()
        exec_id = history.save(rec)
        assert exec_id.startswith("exec_")
        assert len(exec_id) > 5

    def test_save_with_custom_id(self, history):
        rec = _make_record(id="exec_custom123")
        exec_id = history.save(rec)
        assert exec_id == "exec_custom123"

    def test_save_creates_file(self, history, tmp_path):
        rec = _make_record()
        exec_id = history.save(rec)
        path = tmp_path / "function-executions" / "test-func" / f"{exec_id}.json"
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["function_id"] == "test-func"
        assert data["status"] == "success"

    def test_save_multiple_functions(self, history):
        history.save(_make_record(function_id="func-a"))
        history.save(_make_record(function_id="func-b"))
        assert len(history.list("func-a")) == 1
        assert len(history.list("func-b")) == 1


class TestList:
    def test_list_empty(self, history):
        assert history.list("nonexistent") == []

    def test_list_returns_records(self, history):
        history.save(_make_record())
        history.save(_make_record())
        records = history.list("test-func")
        assert len(records) == 2

    def test_list_sorted_newest_first(self, history):
        rec1 = _make_record(timestamp=1000.0)
        rec1["id"] = "exec_old"
        history.save(rec1)

        # Small delay to ensure different mtime
        import os
        time.sleep(0.05)

        rec2 = _make_record(timestamp=2000.0)
        rec2["id"] = "exec_new"
        history.save(rec2)

        records = history.list("test-func")
        assert records[0]["id"] == "exec_new"
        assert records[1]["id"] == "exec_old"

    def test_list_respects_limit(self, history):
        for i in range(5):
            rec = _make_record()
            rec["id"] = f"exec_{i:03d}"
            history.save(rec)
            time.sleep(0.01)
        assert len(history.list("test-func", limit=3)) == 3


class TestGet:
    def test_get_existing(self, history):
        rec = _make_record()
        exec_id = history.save(rec)
        result = history.get("test-func", exec_id)
        assert result is not None
        assert result["function_id"] == "test-func"
        assert result["id"] == exec_id

    def test_get_nonexistent(self, history):
        assert history.get("test-func", "exec_nonexistent") is None

    def test_get_wrong_function(self, history):
        rec = _make_record(function_id="func-a")
        exec_id = history.save(rec)
        assert history.get("func-b", exec_id) is None


class TestPrune:
    def test_prune_removes_oldest(self, history, tmp_path):
        # Save 25 records (MAX_PER_FUNCTION is 20)
        for i in range(25):
            rec = _make_record()
            rec["id"] = f"exec_{i:03d}"
            history.save(rec)
            time.sleep(0.01)

        func_dir = tmp_path / "function-executions" / "test-func"
        files = list(func_dir.glob("*.json"))
        assert len(files) == 20


class TestRecordShape:
    def test_record_has_all_fields(self, history):
        rec = _make_record()
        exec_id = history.save(rec)
        result = history.get("test-func", exec_id)
        assert "id" in result
        assert "function_id" in result
        assert "timestamp" in result
        assert "inputs" in result
        assert "outputs" in result
        assert "trace" in result
        assert "duration_ms" in result
        assert "status" in result
        assert "warnings" in result
        assert "step_count" in result

    def test_status_values(self, history):
        for status in ["success", "error", "partial"]:
            rec = _make_record(status=status)
            exec_id = history.save(rec)
            result = history.get("test-func", exec_id)
            assert result["status"] == status

    def test_trace_preserved(self, history):
        trace = [
            {"step_index": 0, "tool": "findymail", "status": "success", "duration_ms": 500},
            {"step_index": 1, "tool": "call_ai", "status": "error", "duration_ms": 200, "error_message": "timeout"},
        ]
        rec = _make_record(trace=trace, step_count=2)
        exec_id = history.save(rec)
        result = history.get("test-func", exec_id)
        assert len(result["trace"]) == 2
        assert result["trace"][1]["error_message"] == "timeout"
