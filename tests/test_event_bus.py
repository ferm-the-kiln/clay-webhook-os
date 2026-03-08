import asyncio
import json

import pytest

from app.core.event_bus import EventBus


class TestSubscribe:
    def test_subscribe_returns_queue(self):
        bus = EventBus()
        q = bus.subscribe()
        assert isinstance(q, asyncio.Queue)

    def test_subscribe_adds_to_subscribers(self):
        bus = EventBus()
        q = bus.subscribe()
        assert q in bus._subscribers

    def test_multiple_subscribers(self):
        bus = EventBus()
        q1 = bus.subscribe()
        q2 = bus.subscribe()
        assert len(bus._subscribers) == 2
        assert q1 is not q2

    def test_queue_maxsize_is_100(self):
        bus = EventBus()
        q = bus.subscribe()
        assert q.maxsize == 100


class TestUnsubscribe:
    def test_unsubscribe_removes_queue(self):
        bus = EventBus()
        q = bus.subscribe()
        bus.unsubscribe(q)
        assert q not in bus._subscribers

    def test_unsubscribe_nonexistent_does_not_raise(self):
        bus = EventBus()
        q = asyncio.Queue()
        bus.unsubscribe(q)  # should not raise

    def test_unsubscribe_only_removes_target(self):
        bus = EventBus()
        q1 = bus.subscribe()
        q2 = bus.subscribe()
        bus.unsubscribe(q1)
        assert q1 not in bus._subscribers
        assert q2 in bus._subscribers


class TestPublish:
    def test_publish_delivers_to_subscriber(self):
        bus = EventBus()
        q = bus.subscribe()
        bus.publish("test_event", {"key": "value"})
        assert not q.empty()
        msg = q.get_nowait()
        assert "event: test_event" in msg
        assert '"key": "value"' in msg

    def test_publish_delivers_to_all_subscribers(self):
        bus = EventBus()
        q1 = bus.subscribe()
        q2 = bus.subscribe()
        bus.publish("evt", {"x": 1})
        assert not q1.empty()
        assert not q2.empty()

    def test_message_format_is_sse(self):
        bus = EventBus()
        q = bus.subscribe()
        bus.publish("my_event", {"foo": "bar"})
        msg = q.get_nowait()
        lines = msg.strip().split("\n")
        assert lines[0] == "event: my_event"
        assert lines[1].startswith("data: ")
        data = json.loads(lines[1][len("data: "):])
        assert data == {"foo": "bar"}

    def test_message_ends_with_double_newline(self):
        bus = EventBus()
        q = bus.subscribe()
        bus.publish("e", {})
        msg = q.get_nowait()
        assert msg.endswith("\n\n")

    def test_publish_no_subscribers_does_not_raise(self):
        bus = EventBus()
        bus.publish("orphan", {"a": 1})  # no error

    def test_publish_after_unsubscribe_does_not_deliver(self):
        bus = EventBus()
        q = bus.subscribe()
        bus.unsubscribe(q)
        bus.publish("evt", {})
        assert q.empty()


class TestPublishOverflow:
    def test_full_queue_skipped_silently(self):
        bus = EventBus()
        q = bus.subscribe()
        # Fill the queue to capacity (maxsize=100)
        for i in range(100):
            bus.publish("fill", {"i": i})
        assert q.full()
        # Publishing one more should not raise
        bus.publish("overflow", {"extra": True})
        # Queue still has 100 items, overflow was dropped
        assert q.qsize() == 100

    def test_other_subscribers_still_receive(self):
        bus = EventBus()
        q_full = bus.subscribe()
        q_ok = bus.subscribe()
        # Fill only q_full
        for i in range(100):
            q_full.put_nowait(f"filler-{i}")
        bus.publish("test", {"delivered": True})
        # q_ok should have the message
        assert not q_ok.empty()
        msg = q_ok.get_nowait()
        assert "delivered" in msg
        # q_full was full so the new message was dropped
        assert q_full.qsize() == 100


class TestMultipleEvents:
    def test_events_arrive_in_order(self):
        bus = EventBus()
        q = bus.subscribe()
        bus.publish("first", {"n": 1})
        bus.publish("second", {"n": 2})
        bus.publish("third", {"n": 3})
        msgs = [q.get_nowait() for _ in range(3)]
        assert "first" in msgs[0]
        assert "second" in msgs[1]
        assert "third" in msgs[2]
