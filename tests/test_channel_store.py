"""Tests for ChannelStore — file-based chat session persistence."""

import json
import time
from pathlib import Path

import pytest

from app.core.channel_store import ChannelStore
from app.models.channels import ChannelMessage, ChannelSession, SessionSummary


@pytest.fixture
def store(tmp_path: Path) -> ChannelStore:
    s = ChannelStore(data_dir=tmp_path)
    s.load()
    return s


# ---------------------------------------------------------------------------
# Load / init
# ---------------------------------------------------------------------------


class TestLoad:
    def test_load_creates_directory(self, tmp_path: Path):
        s = ChannelStore(data_dir=tmp_path)
        channels_dir = tmp_path / "channels"
        assert not channels_dir.exists()
        s.load()
        assert channels_dir.exists()
        assert channels_dir.is_dir()

    def test_load_idempotent(self, store: ChannelStore, tmp_path: Path):
        # Call load again — should not raise
        store.load()
        assert (tmp_path / "channels").is_dir()


# ---------------------------------------------------------------------------
# create_session
# ---------------------------------------------------------------------------


class TestCreateSession:
    def test_create_session(self, store: ChannelStore):
        session = store.create_session("my-func", "My Title")
        assert isinstance(session, ChannelSession)
        assert len(session.id) == 12
        assert all(c in "0123456789abcdef" for c in session.id)
        assert session.function_id == "my-func"
        assert session.title == "My Title"
        assert session.messages == []
        assert session.status == "active"
        assert session.created_at > 0
        assert session.updated_at > 0

    def test_create_session_auto_title(self, store: ChannelStore):
        session = store.create_session("my-func")
        assert session.title.startswith("Session ")
        assert session.id[:6] in session.title

    def test_create_session_persists_to_disk(self, store: ChannelStore, tmp_path: Path):
        session = store.create_session("my-func", "Disk Test")
        json_path = tmp_path / "channels" / f"{session.id}.json"
        assert json_path.exists()
        data = json.loads(json_path.read_text())
        assert data["function_id"] == "my-func"
        assert data["title"] == "Disk Test"


# ---------------------------------------------------------------------------
# get_session
# ---------------------------------------------------------------------------


class TestGetSession:
    def test_get_session(self, store: ChannelStore):
        created = store.create_session("my-func", "Get Test")
        retrieved = store.get_session(created.id)
        assert retrieved is not None
        assert retrieved.id == created.id
        assert retrieved.function_id == "my-func"
        assert retrieved.title == "Get Test"
        assert retrieved.status == "active"
        assert retrieved.created_at == created.created_at

    def test_get_session_not_found(self, store: ChannelStore):
        result = store.get_session("nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# add_message
# ---------------------------------------------------------------------------


class TestAddMessage:
    def test_add_message(self, store: ChannelStore):
        session = store.create_session("my-func")
        original_updated_at = session.updated_at

        msg_dict = {
            "role": "user",
            "content": "Hello",
            "timestamp": time.time(),
        }
        result = store.add_message(session.id, msg_dict)
        assert result is not None
        assert isinstance(result, ChannelMessage)
        assert result.role == "user"
        assert result.content == "Hello"

        # Verify persistence
        updated = store.get_session(session.id)
        assert updated is not None
        assert len(updated.messages) == 1
        assert updated.messages[0].content == "Hello"
        assert updated.updated_at >= original_updated_at

    def test_add_message_not_found(self, store: ChannelStore):
        msg_dict = {"role": "user", "content": "Hello", "timestamp": 1000.0}
        result = store.add_message("nonexistent", msg_dict)
        assert result is None

    def test_add_multiple_messages(self, store: ChannelStore):
        session = store.create_session("my-func")
        for i in range(3):
            store.add_message(session.id, {
                "role": "user" if i % 2 == 0 else "assistant",
                "content": f"Message {i}",
                "timestamp": time.time(),
            })
        updated = store.get_session(session.id)
        assert updated is not None
        assert len(updated.messages) == 3


# ---------------------------------------------------------------------------
# list_sessions
# ---------------------------------------------------------------------------


class TestListSessions:
    def test_list_sessions_empty(self, store: ChannelStore):
        result = store.list_sessions()
        assert result == []

    def test_list_sessions(self, store: ChannelStore):
        store.create_session("func-1", "First")
        store.create_session("func-2", "Second")
        result = store.list_sessions()
        assert len(result) == 2
        assert all(isinstance(s, SessionSummary) for s in result)

    def test_list_sessions_sorted_by_updated_at_desc(self, store: ChannelStore):
        s1 = store.create_session("func-1", "Older")
        # Ensure s2 has a later timestamp
        s2 = store.create_session("func-2", "Newer")
        result = store.list_sessions()
        assert len(result) == 2
        assert result[0].updated_at >= result[1].updated_at

    def test_list_sessions_message_count(self, store: ChannelStore):
        session = store.create_session("my-func")
        store.add_message(session.id, {"role": "user", "content": "Hi", "timestamp": 1000.0})
        store.add_message(session.id, {"role": "assistant", "content": "Hello", "timestamp": 1001.0})
        result = store.list_sessions()
        assert len(result) == 1
        assert result[0].message_count == 2


# ---------------------------------------------------------------------------
# archive_session
# ---------------------------------------------------------------------------


class TestArchiveSession:
    def test_archive_session(self, store: ChannelStore):
        session = store.create_session("my-func")
        archived = store.archive_session(session.id)
        assert archived is not None
        assert archived.status == "archived"

        # Verify persistence
        retrieved = store.get_session(session.id)
        assert retrieved is not None
        assert retrieved.status == "archived"

    def test_archive_session_not_found(self, store: ChannelStore):
        result = store.archive_session("nonexistent")
        assert result is None


# ---------------------------------------------------------------------------
# update_message_results
# ---------------------------------------------------------------------------


class TestUpdateMessageResults:
    def test_update_message_results(self, store: ChannelStore):
        session = store.create_session("my-func")
        store.add_message(session.id, {
            "role": "user",
            "content": "Enrich",
            "timestamp": 1000.0,
            "data": [{"company": "Acme"}],
        })
        results = [{"company": "Acme", "enriched": True, "employees": 500}]
        success = store.update_message_results(session.id, 0, results)
        assert success is True

        updated = store.get_session(session.id)
        assert updated is not None
        assert updated.messages[0].results == results

    def test_update_message_results_not_found(self, store: ChannelStore):
        result = store.update_message_results("nonexistent", 0, [{"test": True}])
        assert result is False

    def test_update_message_results_invalid_index(self, store: ChannelStore):
        session = store.create_session("my-func")
        result = store.update_message_results(session.id, 5, [{"test": True}])
        assert result is False


# ---------------------------------------------------------------------------
# Persistence across instances
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_persistence_across_instances(self, tmp_path: Path):
        # Create session with store1
        store1 = ChannelStore(data_dir=tmp_path)
        store1.load()
        session = store1.create_session("my-func", "Persistence Test")
        store1.add_message(session.id, {
            "role": "user",
            "content": "Test message",
            "timestamp": 1000.0,
        })

        # Read with a new store2 pointing to the same directory
        store2 = ChannelStore(data_dir=tmp_path)
        store2.load()
        retrieved = store2.get_session(session.id)
        assert retrieved is not None
        assert retrieved.title == "Persistence Test"
        assert len(retrieved.messages) == 1
        assert retrieved.messages[0].content == "Test message"
