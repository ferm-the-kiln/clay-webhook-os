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
