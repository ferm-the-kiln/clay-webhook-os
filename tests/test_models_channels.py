"""Tests for channel/session Pydantic models."""

import pytest

from app.models.channels import (
    ChannelMessage,
    ChannelSession,
    CreateSessionRequest,
    SendMessageRequest,
    SessionSummary,
)


class TestChannelMessage:
    def test_basic_message(self):
        msg = ChannelMessage(role="user", content="Hello", timestamp=1000.0)
        assert msg.role == "user"
        assert msg.content == "Hello"
        assert msg.timestamp == 1000.0
        assert msg.data is None
        assert msg.results is None
        assert msg.execution_id is None

    def test_message_with_all_fields(self):
        msg = ChannelMessage(
            role="assistant",
            content="Here are your results",
            timestamp=1000.0,
            data=[{"company": "Acme"}],
            results=[{"enriched": True}],
            execution_id="exec-123",
        )
        assert msg.role == "assistant"
        assert msg.data == [{"company": "Acme"}]
        assert msg.results == [{"enriched": True}]
        assert msg.execution_id == "exec-123"

    def test_message_content_defaults_empty(self):
        msg = ChannelMessage(role="user", timestamp=1000.0)
        assert msg.content == ""

    def test_message_requires_role(self):
        with pytest.raises(Exception):
            ChannelMessage(timestamp=1000.0)

    def test_message_requires_timestamp(self):
        with pytest.raises(Exception):
            ChannelMessage(role="user")


class TestChannelSession:
    def test_basic_session(self):
        session = ChannelSession(
            id="abc123def456",
            function_id="my-func",
            created_at=1000.0,
            updated_at=1000.0,
        )
        assert session.id == "abc123def456"
        assert session.function_id == "my-func"
        assert session.title == ""
        assert session.messages == []
        assert session.status == "active"

    def test_session_with_messages(self):
        msg = ChannelMessage(role="user", content="test", timestamp=1000.0)
        session = ChannelSession(
            id="abc123def456",
            function_id="my-func",
            messages=[msg],
            created_at=1000.0,
            updated_at=1000.0,
        )
        assert len(session.messages) == 1
        assert session.messages[0].content == "test"

    def test_session_requires_id(self):
        with pytest.raises(Exception):
            ChannelSession(function_id="my-func", created_at=1000.0, updated_at=1000.0)

    def test_session_requires_function_id(self):
        with pytest.raises(Exception):
            ChannelSession(id="abc123def456", created_at=1000.0, updated_at=1000.0)


class TestCreateSessionRequest:
    def test_basic_request(self):
        req = CreateSessionRequest(function_id="my-func")
        assert req.function_id == "my-func"
        assert req.title == ""

    def test_request_with_title(self):
        req = CreateSessionRequest(function_id="my-func", title="My Session")
        assert req.title == "My Session"

    def test_empty_function_id_rejected(self):
        with pytest.raises(ValueError, match="function_id cannot be empty"):
            CreateSessionRequest(function_id="")

    def test_whitespace_function_id_rejected(self):
        with pytest.raises(ValueError, match="function_id cannot be empty"):
            CreateSessionRequest(function_id="   ")


class TestSendMessageRequest:
    def test_basic_request(self):
        req = SendMessageRequest(data=[{"company": "Acme"}])
        assert req.content == ""
        assert req.data == [{"company": "Acme"}]

    def test_request_with_content(self):
        req = SendMessageRequest(content="Enrich these", data=[{"company": "Acme"}])
        assert req.content == "Enrich these"

    def test_data_is_required(self):
        with pytest.raises(Exception):
            SendMessageRequest(content="Hello")


class TestSessionSummary:
    def test_basic_summary(self):
        summary = SessionSummary(
            id="abc123",
            function_id="my-func",
            title="Test",
            created_at=1000.0,
            updated_at=1000.0,
        )
        assert summary.id == "abc123"
        assert summary.function_name == ""
        assert summary.message_count == 0
        assert summary.status == "active"

    def test_summary_with_all_fields(self):
        summary = SessionSummary(
            id="abc123",
            function_id="my-func",
            function_name="My Function",
            title="Test",
            message_count=5,
            created_at=1000.0,
            updated_at=1000.0,
            status="archived",
        )
        assert summary.function_name == "My Function"
        assert summary.message_count == 5
        assert summary.status == "archived"
