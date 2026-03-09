import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.destination_store import DestinationStore
from app.core.job_queue import Job, JobStatus
from app.models.destinations import (
    CreateDestinationRequest,
    Destination,
    DestinationType,
    UpdateDestinationRequest,
)


def _make_create_req(**kwargs) -> CreateDestinationRequest:
    defaults = dict(
        name="My Webhook",
        type=DestinationType.generic_webhook,
        url="https://example.com/hook",
    )
    defaults.update(kwargs)
    return CreateDestinationRequest(**defaults)


def _make_dest(**kwargs) -> Destination:
    defaults = dict(
        id="d1",
        name="Test",
        type=DestinationType.generic_webhook,
        url="https://example.com/hook",
        created_at=1000.0,
        updated_at=1000.0,
    )
    defaults.update(kwargs)
    return Destination(**defaults)


def _make_job(job_id: str = "j1", status: JobStatus = JobStatus.completed,
              result: dict | None = None, row_id: str | None = None) -> Job:
    return Job(
        id=job_id, skill="s", data={}, instructions=None, model="opus",
        callback_url="", row_id=row_id, status=status,
        result=result if result is not None else {"answer": 42},
    )


@pytest.fixture
def store(tmp_path: Path) -> DestinationStore:
    s = DestinationStore(data_dir=tmp_path)
    s.load()
    return s


# ---------------------------------------------------------------------------
# Load / persist
# ---------------------------------------------------------------------------


class TestLoadPersist:
    def test_load_creates_directory(self, tmp_path):
        s = DestinationStore(data_dir=tmp_path)
        s.load()
        assert tmp_path.is_dir()

    def test_load_empty(self, store):
        assert store.list_all() == []

    def test_load_existing_file(self, tmp_path):
        dest = _make_dest()
        (tmp_path / "destinations.json").write_text(json.dumps([dest.model_dump()]))
        s = DestinationStore(data_dir=tmp_path)
        s.load()
        assert len(s.list_all()) == 1
        assert s.list_all()[0].name == "Test"


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


class TestCreate:
    def test_create_returns_destination(self, store):
        dest = store.create(_make_create_req())
        assert dest.name == "My Webhook"
        assert len(dest.id) == 12

    def test_create_persists_to_file(self, store, tmp_path):
        store.create(_make_create_req())
        f = tmp_path / "destinations.json"
        assert f.exists()
        data = json.loads(f.read_text())
        assert len(data) == 1

    def test_create_with_auth(self, store):
        dest = store.create(_make_create_req(
            auth_header_name="X-Key", auth_header_value="secret",
        ))
        assert dest.auth_header_name == "X-Key"
        assert dest.auth_header_value == "secret"

    def test_create_with_client_slug(self, store):
        dest = store.create(_make_create_req(client_slug="acme"))
        assert dest.client_slug == "acme"


class TestGet:
    def test_get_existing(self, store):
        created = store.create(_make_create_req())
        found = store.get(created.id)
        assert found is not None
        assert found.id == created.id

    def test_get_nonexistent(self, store):
        assert store.get("nope") is None


class TestListAll:
    def test_list_multiple(self, store):
        store.create(_make_create_req(name="A"))
        store.create(_make_create_req(name="B"))
        assert len(store.list_all()) == 2


class TestUpdate:
    def test_update_name(self, store):
        created = store.create(_make_create_req(name="Old"))
        updated = store.update(created.id, UpdateDestinationRequest(name="New"))
        assert updated is not None
        assert updated.name == "New"
        assert updated.updated_at > created.updated_at

    def test_update_url(self, store):
        created = store.create(_make_create_req())
        updated = store.update(created.id, UpdateDestinationRequest(url="https://new.com"))
        assert updated.url == "https://new.com"

    def test_update_nonexistent(self, store):
        assert store.update("nope", UpdateDestinationRequest(name="X")) is None

    def test_update_no_changes(self, store):
        created = store.create(_make_create_req())
        result = store.update(created.id, UpdateDestinationRequest())
        assert result.name == created.name

    def test_update_persists(self, store, tmp_path):
        created = store.create(_make_create_req(name="Old"))
        store.update(created.id, UpdateDestinationRequest(name="New"))
        data = json.loads((tmp_path / "destinations.json").read_text())
        assert data[0]["name"] == "New"


class TestDelete:
    def test_delete_existing(self, store):
        created = store.create(_make_create_req())
        assert store.delete(created.id) is True
        assert store.get(created.id) is None

    def test_delete_nonexistent(self, store):
        assert store.delete("nope") is False

    def test_delete_persists(self, store, tmp_path):
        created = store.create(_make_create_req())
        store.delete(created.id)
        data = json.loads((tmp_path / "destinations.json").read_text())
        assert len(data) == 0


# ---------------------------------------------------------------------------
# Push
# ---------------------------------------------------------------------------


class TestPush:
    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_completed_jobs(self, mock_client_cls, store):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest()
        jobs = [_make_job("j1", result={"x": 1}), _make_job("j2", result={"x": 2})]
        result = await store.push(dest, jobs)
        assert result.total == 2
        assert result.success == 2
        assert result.failed == 0

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_skips_non_completed(self, mock_client_cls, store):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest()
        jobs = [_make_job("j1", status=JobStatus.queued)]
        result = await store.push(dest, jobs)
        assert result.total == 0
        assert result.success == 0
        mock_client.post.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_includes_row_id(self, mock_client_cls, store):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest()
        jobs = [_make_job("j1", result={"x": 1}, row_id="r42")]
        await store.push(dest, jobs)

        payload = mock_client.post.call_args[1]["json"]
        assert payload["row_id"] == "r42"
        assert payload["_meta"]["job_id"] == "j1"

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_with_auth_headers(self, mock_client_cls, store):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest(auth_header_name="X-Api-Key", auth_header_value="secret123")
        jobs = [_make_job()]
        await store.push(dest, jobs)

        headers = mock_client.post.call_args[1]["headers"]
        assert headers["X-Api-Key"] == "secret123"

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_handles_failure(self, mock_client_cls, store):
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("connection refused")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest()
        jobs = [_make_job()]
        result = await store.push(dest, jobs)
        assert result.failed == 1
        assert result.success == 0
        assert len(result.errors) == 1

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_skips_null_result(self, mock_client_cls, store):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest()
        job = _make_job("j1", result=None)
        job.result = None  # Force None result
        result = await store.push(dest, [job])
        assert result.total == 0
        mock_client.post.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_meta_payload(self, mock_client_cls, store):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest()
        jobs = [_make_job("j1", result={"x": 1})]
        jobs[0].skill = "email-gen"
        jobs[0].model = "sonnet"
        jobs[0].duration_ms = 250
        await store.push(dest, jobs)

        payload = mock_client.post.call_args[1]["json"]
        assert payload["_meta"]["source"] == "clay-webhook-os"
        assert payload["_meta"]["skill"] == "email-gen"
        assert payload["_meta"]["model"] == "sonnet"
        assert payload["_meta"]["duration_ms"] == 250

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_failure_enqueues_retry(self, mock_client_cls, store):
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("fail")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        retry_worker = MagicMock()
        store._retry_worker = retry_worker

        dest = _make_dest()
        await store.push(dest, [_make_job()])
        retry_worker.enqueue.assert_called_once()
        call_kwargs = retry_worker.enqueue.call_args
        assert call_kwargs[1]["job_id"] == "j1"

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_no_retry_worker_no_crash(self, mock_client_cls, store):
        """Push failure without retry_worker doesn't crash."""
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("fail")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        store._retry_worker = None
        dest = _make_dest()
        result = await store.push(dest, [_make_job()])
        assert result.failed == 1


# ---------------------------------------------------------------------------
# push_data
# ---------------------------------------------------------------------------


class TestPushData:
    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_data_success(self, mock_client_cls, store):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest(name="My Hook")
        result = await store.push_data(dest, {"email": "Hi"})
        assert result["ok"] is True
        assert result["destination_name"] == "My Hook"
        assert result["status_code"] == 200

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_data_includes_meta(self, mock_client_cls, store):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest()
        await store.push_data(dest, {"email": "Hi"})
        payload = mock_client.post.call_args[1]["json"]
        assert payload["_meta"]["source"] == "clay-webhook-os"
        assert payload["_meta"]["pushed_from"] == "playground"
        assert payload["email"] == "Hi"

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_data_with_auth(self, mock_client_cls, store):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest(auth_header_name="Authorization", auth_header_value="Bearer xyz")
        await store.push_data(dest, {})
        headers = mock_client.post.call_args[1]["headers"]
        assert headers["Authorization"] == "Bearer xyz"

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_data_failure(self, mock_client_cls, store):
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("timeout")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest(name="Hook")
        result = await store.push_data(dest, {"email": "Hi"})
        assert result["ok"] is False
        assert "timeout" in result["error"]
        assert result["destination_name"] == "Hook"

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_data_failure_enqueues_retry(self, mock_client_cls, store):
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("fail")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        retry_worker = MagicMock()
        store._retry_worker = retry_worker

        dest = _make_dest()
        await store.push_data(dest, {"x": 1})
        retry_worker.enqueue.assert_called_once()
        assert retry_worker.enqueue.call_args[1]["job_id"] == "push-data"

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_data_no_retry_worker(self, mock_client_cls, store):
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("fail")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        store._retry_worker = None
        dest = _make_dest()
        result = await store.push_data(dest, {})
        assert result["ok"] is False


# ---------------------------------------------------------------------------
# Test endpoint
# ---------------------------------------------------------------------------


class TestTestEndpoint:
    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_test_success(self, mock_client_cls, store):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest()
        result = await store.test(dest)
        assert result["ok"] is True
        assert result["status_code"] == 200

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_test_failure(self, mock_client_cls, store):
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("timeout")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest()
        result = await store.test(dest)
        assert result["ok"] is False
        assert "timeout" in result["error"]

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_test_with_auth_headers(self, mock_client_cls, store):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest(auth_header_name="X-Key", auth_header_value="secret")
        await store.test(dest)
        headers = mock_client.post.call_args[1]["headers"]
        assert headers["X-Key"] == "secret"

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_test_4xx_not_ok(self, mock_client_cls, store):
        mock_resp = MagicMock()
        mock_resp.status_code = 401
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest()
        result = await store.test(dest)
        assert result["ok"] is False


# ---------------------------------------------------------------------------
# DEEPER TESTS — Load / Persist
# ---------------------------------------------------------------------------


class TestLoadPersistDeeper:
    def test_load_multiple_destinations(self, tmp_path):
        dests = [_make_dest(id="d1", name="A").model_dump(), _make_dest(id="d2", name="B").model_dump()]
        (tmp_path / "destinations.json").write_text(json.dumps(dests))
        s = DestinationStore(data_dir=tmp_path)
        s.load()
        assert len(s.list_all()) == 2
        names = {d.name for d in s.list_all()}
        assert names == {"A", "B"}

    def test_round_trip_create_reload(self, tmp_path):
        """Create, save, reload from file — data survives."""
        s1 = DestinationStore(data_dir=tmp_path)
        s1.load()
        created = s1.create(_make_create_req(name="Persisted Hook", url="https://hook.io/1"))

        s2 = DestinationStore(data_dir=tmp_path)
        s2.load()
        found = s2.get(created.id)
        assert found is not None
        assert found.name == "Persisted Hook"
        assert found.url == "https://hook.io/1"

    def test_load_nonexistent_dir_creates_it(self, tmp_path):
        data_dir = tmp_path / "sub" / "dir"
        assert not data_dir.exists()
        s = DestinationStore(data_dir=data_dir)
        s.load()
        assert data_dir.is_dir()

    def test_load_no_file_gives_empty(self, tmp_path):
        s = DestinationStore(data_dir=tmp_path)
        s.load()
        assert s.list_all() == []
        assert s.get("anything") is None


# ---------------------------------------------------------------------------
# DEEPER TESTS — Create
# ---------------------------------------------------------------------------


class TestCreateDeeper:
    def test_create_sets_timestamps(self, store):
        import time
        before = time.time()
        dest = store.create(_make_create_req())
        after = time.time()
        assert before <= dest.created_at <= after
        assert before <= dest.updated_at <= after

    def test_create_multiple_unique_ids(self, store):
        ids = set()
        for i in range(10):
            dest = store.create(_make_create_req(name=f"Hook {i}"))
            ids.add(dest.id)
        assert len(ids) == 10

    def test_create_preserves_type(self, store):
        dest = store.create(_make_create_req(type=DestinationType.generic_webhook))
        assert dest.type == DestinationType.generic_webhook

    def test_create_defaults_no_auth(self, store):
        dest = store.create(_make_create_req())
        assert dest.auth_header_name == ""
        assert dest.auth_header_value == ""

    def test_create_defaults_no_client_slug(self, store):
        dest = store.create(_make_create_req())
        assert dest.client_slug is None


# ---------------------------------------------------------------------------
# DEEPER TESTS — Update
# ---------------------------------------------------------------------------


class TestUpdateDeeper:
    def test_update_auth_headers(self, store):
        created = store.create(_make_create_req())
        updated = store.update(created.id, UpdateDestinationRequest(
            auth_header_name="X-Token", auth_header_value="abc123",
        ))
        assert updated.auth_header_name == "X-Token"
        assert updated.auth_header_value == "abc123"

    def test_update_client_slug(self, store):
        created = store.create(_make_create_req())
        updated = store.update(created.id, UpdateDestinationRequest(client_slug="acme"))
        assert updated.client_slug == "acme"

    def test_update_preserves_unchanged_fields(self, store):
        created = store.create(_make_create_req(
            name="Original", url="https://orig.com",
            auth_header_name="X-Key", auth_header_value="secret",
        ))
        updated = store.update(created.id, UpdateDestinationRequest(name="New Name"))
        assert updated.name == "New Name"
        assert updated.url == "https://orig.com"
        assert updated.auth_header_name == "X-Key"
        assert updated.auth_header_value == "secret"

    def test_update_created_at_unchanged(self, store):
        created = store.create(_make_create_req())
        updated = store.update(created.id, UpdateDestinationRequest(name="New"))
        assert updated.created_at == created.created_at
        assert updated.updated_at > created.created_at

    def test_update_no_changes_returns_original(self, store):
        created = store.create(_make_create_req())
        result = store.update(created.id, UpdateDestinationRequest())
        assert result.updated_at == created.updated_at  # No change triggers no updated_at bump


# ---------------------------------------------------------------------------
# DEEPER TESTS — Delete
# ---------------------------------------------------------------------------


class TestDeleteDeeper:
    def test_delete_from_multiple_keeps_others(self, store):
        d1 = store.create(_make_create_req(name="A"))
        d2 = store.create(_make_create_req(name="B"))
        d3 = store.create(_make_create_req(name="C"))

        store.delete(d2.id)
        remaining = store.list_all()
        assert len(remaining) == 2
        remaining_ids = {d.id for d in remaining}
        assert d1.id in remaining_ids
        assert d3.id in remaining_ids
        assert d2.id not in remaining_ids

    def test_double_delete(self, store):
        created = store.create(_make_create_req())
        assert store.delete(created.id) is True
        assert store.delete(created.id) is False


# ---------------------------------------------------------------------------
# DEEPER TESTS — Push
# ---------------------------------------------------------------------------


class TestPushDeeper:
    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_mixed_completed_and_queued(self, mock_client_cls, store):
        """Mix of completed and non-completed jobs — only completed are pushed."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest()
        jobs = [
            _make_job("j1", status=JobStatus.completed, result={"x": 1}),
            _make_job("j2", status=JobStatus.queued),
            _make_job("j3", status=JobStatus.completed, result={"x": 3}),
            _make_job("j4", status=JobStatus.failed),
        ]
        result = await store.push(dest, jobs)
        assert result.total == 2
        assert result.success == 2
        assert mock_client.post.call_count == 2

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_empty_job_list(self, mock_client_cls, store):
        mock_client = AsyncMock()
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest()
        result = await store.push(dest, [])
        assert result.total == 0
        assert result.success == 0
        assert result.failed == 0
        mock_client.post.assert_not_awaited()

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_no_row_id_excluded_from_payload(self, mock_client_cls, store):
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest()
        jobs = [_make_job("j1", result={"x": 1}, row_id=None)]
        await store.push(dest, jobs)
        payload = mock_client.post.call_args[1]["json"]
        assert "row_id" not in payload

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_no_auth_headers(self, mock_client_cls, store):
        """Without auth_header_name, only Content-Type is sent."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest(auth_header_name="", auth_header_value="")
        await store.push(dest, [_make_job()])
        headers = mock_client.post.call_args[1]["headers"]
        assert headers == {"Content-Type": "application/json"}

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_result_fields(self, mock_client_cls, store):
        """PushResult includes destination_id and destination_name."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest(id="dest-42", name="My Dest")
        result = await store.push(dest, [_make_job()])
        assert result.destination_id == "dest-42"
        assert result.destination_name == "My Dest"

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_error_contains_job_id(self, mock_client_cls, store):
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("network error")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest()
        result = await store.push(dest, [_make_job("job-99")])
        assert result.errors[0]["job_id"] == "job-99"
        assert "network error" in result.errors[0]["error"]

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_retry_worker_receives_correct_args(self, mock_client_cls, store):
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("fail")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        retry_worker = MagicMock()
        store._retry_worker = retry_worker
        dest = _make_dest(url="https://hook.io/push")
        await store.push(dest, [_make_job("j1", result={"x": 1})])

        args = retry_worker.enqueue.call_args
        assert args[0][0] == "https://hook.io/push"  # url
        assert args[0][1]["x"] == 1  # payload includes result
        assert args[0][1]["_meta"]["source"] == "clay-webhook-os"
        assert args[0][2]["Content-Type"] == "application/json"  # headers


# ---------------------------------------------------------------------------
# DEEPER TESTS — push_data
# ---------------------------------------------------------------------------


class TestPushDataDeeper:
    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_data_no_auth_headers(self, mock_client_cls, store):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest(auth_header_name="", auth_header_value="")
        await store.push_data(dest, {"data": 1})
        headers = mock_client.post.call_args[1]["headers"]
        assert headers == {"Content-Type": "application/json"}

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_data_retry_worker_args(self, mock_client_cls, store):
        mock_client = AsyncMock()
        mock_client.post.side_effect = Exception("fail")
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        retry_worker = MagicMock()
        store._retry_worker = retry_worker
        dest = _make_dest(url="https://hook.io/data")
        await store.push_data(dest, {"email": "Hi"})

        args = retry_worker.enqueue.call_args
        assert args[0][0] == "https://hook.io/data"  # url
        assert args[0][1]["email"] == "Hi"  # payload
        assert args[0][1]["_meta"]["pushed_from"] == "playground"
        assert args[1]["job_id"] == "push-data"

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_push_data_posts_to_destination_url(self, mock_client_cls, store):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_resp.raise_for_status = MagicMock()
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest(url="https://specific-hook.io/receive")
        await store.push_data(dest, {})
        assert mock_client.post.call_args[0][0] == "https://specific-hook.io/receive"


# ---------------------------------------------------------------------------
# DEEPER TESTS — Test endpoint
# ---------------------------------------------------------------------------


class TestTestEndpointDeeper:
    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_test_sends_test_payload(self, mock_client_cls, store):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest()
        await store.test(dest)
        payload = mock_client.post.call_args[1]["json"]
        assert payload["_test"] is True
        assert payload["source"] == "clay-webhook-os"

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_test_3xx_is_ok(self, mock_client_cls, store):
        """3xx status codes are < 400, so ok should be True."""
        mock_resp = MagicMock()
        mock_resp.status_code = 302
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest()
        result = await store.test(dest)
        assert result["ok"] is True
        assert result["status_code"] == 302

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_test_500_not_ok(self, mock_client_cls, store):
        mock_resp = MagicMock()
        mock_resp.status_code = 500
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest()
        result = await store.test(dest)
        assert result["ok"] is False
        assert result["status_code"] == 500

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_test_no_auth(self, mock_client_cls, store):
        """Without auth headers, only Content-Type is sent."""
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest(auth_header_name="", auth_header_value="")
        await store.test(dest)
        headers = mock_client.post.call_args[1]["headers"]
        assert headers == {"Content-Type": "application/json"}

    @pytest.mark.asyncio
    @patch("app.core.destination_store.httpx.AsyncClient")
    async def test_test_posts_to_destination_url(self, mock_client_cls, store):
        mock_resp = MagicMock()
        mock_resp.status_code = 200
        mock_client = AsyncMock()
        mock_client.post.return_value = mock_resp
        mock_client.__aenter__ = AsyncMock(return_value=mock_client)
        mock_client.__aexit__ = AsyncMock(return_value=False)
        mock_client_cls.return_value = mock_client

        dest = _make_dest(url="https://mysite.com/test-hook")
        await store.test(dest)
        assert mock_client.post.call_args[0][0] == "https://mysite.com/test-hook"
