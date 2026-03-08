import json
import time
from pathlib import Path

import pytest

from app.core.campaign_store import CampaignStore
from app.models.campaigns import (
    CampaignGoal,
    CampaignSchedule,
    CampaignStatus,
    CreateCampaignRequest,
    UpdateCampaignRequest,
)


def _make_create_req(**kwargs) -> CreateCampaignRequest:
    defaults = dict(name="Test Campaign", pipeline="full-outbound")
    defaults.update(kwargs)
    return CreateCampaignRequest(**defaults)


@pytest.fixture
def store(tmp_path: Path) -> CampaignStore:
    s = CampaignStore(data_dir=tmp_path)
    s.load()
    return s


# ---------------------------------------------------------------------------
# Load / persist
# ---------------------------------------------------------------------------


class TestLoadPersist:
    def test_load_creates_directory(self, tmp_path):
        s = CampaignStore(data_dir=tmp_path)
        s.load()
        assert (tmp_path / "campaigns").is_dir()

    def test_load_empty(self, store):
        assert store.list_all() == []

    def test_load_existing(self, tmp_path):
        camp_dir = tmp_path / "campaigns"
        camp_dir.mkdir(parents=True)
        data = [{
            "id": "c1", "name": "Loaded", "pipeline": "p",
            "status": "draft", "created_at": 1000.0, "updated_at": 1000.0,
        }]
        (camp_dir / "campaigns.json").write_text(json.dumps(data))
        s = CampaignStore(data_dir=tmp_path)
        s.load()
        assert len(s.list_all()) == 1
        assert s.get("c1").name == "Loaded"


# ---------------------------------------------------------------------------
# CRUD
# ---------------------------------------------------------------------------


class TestCreate:
    def test_create_returns_campaign(self, store):
        c = store.create(_make_create_req())
        assert c.name == "Test Campaign"
        assert c.status == CampaignStatus.draft

    def test_create_persists(self, store, tmp_path):
        store.create(_make_create_req())
        f = tmp_path / "campaigns" / "campaigns.json"
        assert f.exists()
        assert len(json.loads(f.read_text())) == 1

    def test_create_with_goal_and_schedule(self, store):
        c = store.create(_make_create_req(
            goal=CampaignGoal(description="Send 100", target_count=100),
            schedule=CampaignSchedule(frequency="weekly", batch_size=20),
        ))
        assert c.goal.target_count == 100
        assert c.schedule.frequency == "weekly"
        assert c.schedule.batch_size == 20

    def test_create_with_audience(self, store):
        rows = [{"name": "A"}, {"name": "B"}]
        c = store.create(_make_create_req(audience=rows))
        assert len(c.audience) == 2


class TestGet:
    def test_get_existing(self, store):
        c = store.create(_make_create_req())
        assert store.get(c.id) is not None

    def test_get_nonexistent(self, store):
        assert store.get("nope") is None


class TestListAll:
    def test_list_sorted_newest_first(self, store):
        store.create(_make_create_req(name="Old"))
        store.create(_make_create_req(name="New"))
        campaigns = store.list_all()
        assert campaigns[0].name == "New"

    def test_list_filter_by_status(self, store):
        c = store.create(_make_create_req())
        store.update(c.id, UpdateCampaignRequest(status=CampaignStatus.active))
        store.create(_make_create_req(name="Draft"))
        assert len(store.list_all(status="active")) == 1
        assert len(store.list_all(status="draft")) == 1


class TestUpdate:
    def test_update_name(self, store):
        c = store.create(_make_create_req(name="Old"))
        updated = store.update(c.id, UpdateCampaignRequest(name="New"))
        assert updated.name == "New"
        assert updated.updated_at > c.created_at

    def test_update_status(self, store):
        c = store.create(_make_create_req())
        updated = store.update(c.id, UpdateCampaignRequest(status=CampaignStatus.active))
        assert updated.status == CampaignStatus.active

    def test_update_nonexistent(self, store):
        assert store.update("nope", UpdateCampaignRequest(name="X")) is None

    def test_update_no_changes(self, store):
        c = store.create(_make_create_req())
        result = store.update(c.id, UpdateCampaignRequest())
        assert result.name == c.name


class TestDelete:
    def test_delete_existing(self, store):
        c = store.create(_make_create_req())
        assert store.delete(c.id) is True
        assert store.get(c.id) is None

    def test_delete_nonexistent(self, store):
        assert store.delete("nope") is False


# ---------------------------------------------------------------------------
# Audience management
# ---------------------------------------------------------------------------


class TestAudience:
    def test_add_audience(self, store):
        c = store.create(_make_create_req())
        updated = store.add_audience(c.id, [{"name": "A"}, {"name": "B"}])
        assert len(updated.audience) == 2

    def test_add_audience_appends(self, store):
        c = store.create(_make_create_req(audience=[{"name": "X"}]))
        updated = store.add_audience(c.id, [{"name": "Y"}])
        assert len(updated.audience) == 2

    def test_add_audience_nonexistent(self, store):
        assert store.add_audience("nope", []) is None

    def test_advance_cursor(self, store):
        c = store.create(_make_create_req(audience=[{"a": 1}, {"a": 2}, {"a": 3}]))
        updated = store.advance_cursor(c.id, 2)
        assert updated.audience_cursor == 2

    def test_advance_cursor_nonexistent(self, store):
        assert store.advance_cursor("nope", 1) is None

    def test_get_next_batch(self, store):
        rows = [{"n": i} for i in range(20)]
        c = store.create(_make_create_req(
            audience=rows,
            schedule=CampaignSchedule(batch_size=5),
        ))
        batch = store.get_next_batch(c.id)
        assert len(batch) == 5
        assert batch[0]["n"] == 0

    def test_get_next_batch_after_advance(self, store):
        rows = [{"n": i} for i in range(20)]
        c = store.create(_make_create_req(
            audience=rows,
            schedule=CampaignSchedule(batch_size=5),
        ))
        store.advance_cursor(c.id, 5)
        batch = store.get_next_batch(c.id)
        assert batch[0]["n"] == 5

    def test_get_next_batch_nonexistent(self, store):
        assert store.get_next_batch("nope") == []


# ---------------------------------------------------------------------------
# Progress tracking
# ---------------------------------------------------------------------------


class TestProgress:
    def test_update_progress(self, store):
        c = store.create(_make_create_req())
        updated = store.update_progress(c.id, processed=5, approved=3, rejected=2, sent=3)
        assert updated.progress.total_processed == 5
        assert updated.progress.total_approved == 3
        assert updated.progress.total_rejected == 2
        assert updated.progress.total_sent == 3
        assert updated.progress.approval_rate == 0.6

    def test_update_progress_cumulative(self, store):
        c = store.create(_make_create_req())
        store.update_progress(c.id, processed=5, approved=3, rejected=2)
        store.update_progress(c.id, processed=5, approved=4, rejected=1)
        updated = store.get(c.id)
        assert updated.progress.total_processed == 10
        assert updated.progress.total_approved == 7

    def test_update_progress_nonexistent(self, store):
        assert store.update_progress("nope") is None

    def test_goal_completes_campaign(self, store):
        c = store.create(_make_create_req(
            goal=CampaignGoal(target_count=10, metric="emails_sent"),
        ))
        store.update(c.id, UpdateCampaignRequest(status=CampaignStatus.active))
        store.update_progress(c.id, sent=10)
        updated = store.get(c.id)
        assert updated.status == CampaignStatus.completed


# ---------------------------------------------------------------------------
# Active / due campaigns
# ---------------------------------------------------------------------------


class TestActiveDue:
    def test_get_active_campaigns(self, store):
        c = store.create(_make_create_req())
        store.update(c.id, UpdateCampaignRequest(status=CampaignStatus.active))
        store.create(_make_create_req(name="Draft"))
        assert len(store.get_active_campaigns()) == 1

    def test_get_due_campaigns(self, store):
        c = store.create(_make_create_req(
            audience=[{"n": 1}],
            schedule=CampaignSchedule(next_run_at=time.time() - 100),
        ))
        store.update(c.id, UpdateCampaignRequest(status=CampaignStatus.active))
        due = store.get_due_campaigns()
        assert len(due) == 1

    def test_not_due_if_future(self, store):
        c = store.create(_make_create_req(
            audience=[{"n": 1}],
            schedule=CampaignSchedule(next_run_at=time.time() + 10000),
        ))
        store.update(c.id, UpdateCampaignRequest(status=CampaignStatus.active))
        assert len(store.get_due_campaigns()) == 0

    def test_not_due_if_cursor_past_audience(self, store):
        c = store.create(_make_create_req(
            audience=[{"n": 1}],
            schedule=CampaignSchedule(next_run_at=time.time() - 100),
        ))
        store.update(c.id, UpdateCampaignRequest(status=CampaignStatus.active))
        store.advance_cursor(c.id, 1)
        assert len(store.get_due_campaigns()) == 0


# ---------------------------------------------------------------------------
# Schedule next run
# ---------------------------------------------------------------------------


class TestScheduleNextRun:
    def test_daily_schedule(self, store):
        c = store.create(_make_create_req(schedule=CampaignSchedule(frequency="daily")))
        before = time.time()
        updated = store.schedule_next_run(c.id)
        assert updated.schedule.next_run_at >= before + 86400

    def test_weekly_schedule(self, store):
        c = store.create(_make_create_req(schedule=CampaignSchedule(frequency="weekly")))
        before = time.time()
        updated = store.schedule_next_run(c.id)
        assert updated.schedule.next_run_at >= before + 604800

    def test_manual_schedule(self, store):
        c = store.create(_make_create_req(schedule=CampaignSchedule(frequency="manual")))
        updated = store.schedule_next_run(c.id)
        assert updated.schedule.next_run_at is None

    def test_schedule_nonexistent(self, store):
        assert store.schedule_next_run("nope") is None
