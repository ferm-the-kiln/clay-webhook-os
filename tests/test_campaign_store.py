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


# ---------------------------------------------------------------------------
# Deeper: Load / persist round-trip
# ---------------------------------------------------------------------------


class TestLoadPersistDeeper:
    def test_create_reload_preserves_all_fields(self, tmp_path):
        s = CampaignStore(data_dir=tmp_path)
        s.load()
        c = s.create(_make_create_req(
            name="RT",
            description="Round trip",
            pipeline="pipe",
            destination_id="dest-1",
            client_slug="acme",
            instructions="Do stuff",
            model="sonnet",
            confidence_threshold=0.5,
            audience=[{"name": "A"}],
            goal=CampaignGoal(description="Goal", target_count=50, metric="meetings_booked"),
            schedule=CampaignSchedule(frequency="weekly", batch_size=25, next_run_at=1234.0),
        ))
        s2 = CampaignStore(data_dir=tmp_path)
        s2.load()
        reloaded = s2.get(c.id)
        assert reloaded.name == "RT"
        assert reloaded.description == "Round trip"
        assert reloaded.destination_id == "dest-1"
        assert reloaded.client_slug == "acme"
        assert reloaded.instructions == "Do stuff"
        assert reloaded.model == "sonnet"
        assert reloaded.confidence_threshold == 0.5
        assert len(reloaded.audience) == 1
        assert reloaded.goal.target_count == 50
        assert reloaded.goal.metric == "meetings_booked"
        assert reloaded.schedule.frequency == "weekly"
        assert reloaded.schedule.batch_size == 25
        assert reloaded.schedule.next_run_at == 1234.0

    def test_multiple_campaigns_persist_and_reload(self, tmp_path):
        s = CampaignStore(data_dir=tmp_path)
        s.load()
        ids = [s.create(_make_create_req(name=f"C{i}")).id for i in range(5)]
        s2 = CampaignStore(data_dir=tmp_path)
        s2.load()
        assert len(s2.list_all()) == 5
        for cid in ids:
            assert s2.get(cid) is not None

    def test_load_corrupt_json_raises(self, tmp_path):
        camp_dir = tmp_path / "campaigns"
        camp_dir.mkdir()
        (camp_dir / "campaigns.json").write_text("{bad json")
        s = CampaignStore(data_dir=tmp_path)
        with pytest.raises(json.JSONDecodeError):
            s.load()

    def test_progress_persists_through_reload(self, tmp_path):
        s = CampaignStore(data_dir=tmp_path)
        s.load()
        c = s.create(_make_create_req())
        s.update_progress(c.id, processed=10, approved=7, rejected=3, sent=5, pending_review=2)
        s2 = CampaignStore(data_dir=tmp_path)
        s2.load()
        p = s2.get(c.id).progress
        assert p.total_processed == 10
        assert p.total_approved == 7
        assert p.total_rejected == 3
        assert p.total_sent == 5
        assert p.total_pending_review == 2
        assert p.approval_rate == 0.7


# ---------------------------------------------------------------------------
# Deeper: Create
# ---------------------------------------------------------------------------


class TestCreateDeeper:
    def test_create_defaults_goal_and_schedule(self, store):
        c = store.create(_make_create_req())
        assert c.goal.target_count == 0
        assert c.goal.metric == "emails_sent"
        assert c.schedule.frequency == "daily"
        assert c.schedule.batch_size == 10

    def test_create_with_optional_fields(self, store):
        c = store.create(_make_create_req(
            description="desc",
            destination_id="d-1",
            client_slug="acme",
            instructions="be nice",
            model="haiku",
            confidence_threshold=0.3,
        ))
        assert c.description == "desc"
        assert c.destination_id == "d-1"
        assert c.client_slug == "acme"
        assert c.instructions == "be nice"
        assert c.model == "haiku"
        assert c.confidence_threshold == 0.3

    def test_create_unique_ids(self, store):
        ids = {store.create(_make_create_req()).id for _ in range(20)}
        assert len(ids) == 20

    def test_create_sets_timestamps(self, store):
        before = time.time()
        c = store.create(_make_create_req())
        after = time.time()
        assert before <= c.created_at <= after
        assert before <= c.updated_at <= after


# ---------------------------------------------------------------------------
# Deeper: Update
# ---------------------------------------------------------------------------


class TestUpdateDeeper:
    def test_update_persists_to_file(self, store, tmp_path):
        c = store.create(_make_create_req(name="Old"))
        store.update(c.id, UpdateCampaignRequest(name="New"))
        raw = json.loads((tmp_path / "campaigns" / "campaigns.json").read_text())
        assert raw[0]["name"] == "New"

    def test_update_preserves_unchanged(self, store):
        c = store.create(_make_create_req(
            name="Keep", description="Also keep", pipeline="p1",
        ))
        store.update(c.id, UpdateCampaignRequest(name="Changed"))
        updated = store.get(c.id)
        assert updated.name == "Changed"
        assert updated.description == "Also keep"
        assert updated.pipeline == "p1"

    def test_update_goal(self, store):
        c = store.create(_make_create_req())
        store.update(c.id, UpdateCampaignRequest(
            goal=CampaignGoal(target_count=200, metric="meetings_booked"),
        ))
        updated = store.get(c.id)
        assert updated.goal.target_count == 200
        assert updated.goal.metric == "meetings_booked"

    def test_update_schedule(self, store):
        c = store.create(_make_create_req())
        store.update(c.id, UpdateCampaignRequest(
            schedule=CampaignSchedule(frequency="weekly", batch_size=50),
        ))
        updated = store.get(c.id)
        assert updated.schedule.frequency == "weekly"
        assert updated.schedule.batch_size == 50

    def test_update_bumps_updated_at(self, store):
        c = store.create(_make_create_req())
        old_ts = c.updated_at
        time.sleep(0.01)
        updated = store.update(c.id, UpdateCampaignRequest(name="X"))
        assert updated.updated_at > old_ts


# ---------------------------------------------------------------------------
# Deeper: Delete
# ---------------------------------------------------------------------------


class TestDeleteDeeper:
    def test_delete_from_many_keeps_others(self, store):
        ids = [store.create(_make_create_req(name=f"C{i}")).id for i in range(5)]
        store.delete(ids[2])
        assert store.get(ids[2]) is None
        assert len(store.list_all()) == 4
        for i in [0, 1, 3, 4]:
            assert store.get(ids[i]) is not None

    def test_delete_persists(self, store, tmp_path):
        c = store.create(_make_create_req())
        store.delete(c.id)
        raw = json.loads((tmp_path / "campaigns" / "campaigns.json").read_text())
        assert len(raw) == 0

    def test_delete_twice_returns_false(self, store):
        c = store.create(_make_create_req())
        assert store.delete(c.id) is True
        assert store.delete(c.id) is False


# ---------------------------------------------------------------------------
# Deeper: Audience management
# ---------------------------------------------------------------------------


class TestAudienceDeeper:
    def test_add_audience_updates_timestamp(self, store):
        c = store.create(_make_create_req())
        old_ts = c.updated_at
        time.sleep(0.01)
        updated = store.add_audience(c.id, [{"name": "X"}])
        assert updated.updated_at > old_ts

    def test_advance_cursor_cumulative(self, store):
        rows = [{"n": i} for i in range(10)]
        c = store.create(_make_create_req(audience=rows))
        store.advance_cursor(c.id, 3)
        store.advance_cursor(c.id, 4)
        updated = store.get(c.id)
        assert updated.audience_cursor == 7

    def test_get_next_batch_at_end(self, store):
        rows = [{"n": i} for i in range(3)]
        c = store.create(_make_create_req(
            audience=rows,
            schedule=CampaignSchedule(batch_size=5),
        ))
        store.advance_cursor(c.id, 3)
        batch = store.get_next_batch(c.id)
        assert batch == []

    def test_get_next_batch_partial(self, store):
        rows = [{"n": i} for i in range(7)]
        c = store.create(_make_create_req(
            audience=rows,
            schedule=CampaignSchedule(batch_size=5),
        ))
        store.advance_cursor(c.id, 5)
        batch = store.get_next_batch(c.id)
        assert len(batch) == 2
        assert batch[0]["n"] == 5
        assert batch[1]["n"] == 6

    def test_add_empty_audience(self, store):
        c = store.create(_make_create_req(audience=[{"x": 1}]))
        updated = store.add_audience(c.id, [])
        assert len(updated.audience) == 1


# ---------------------------------------------------------------------------
# Deeper: Progress tracking
# ---------------------------------------------------------------------------


class TestProgressDeeper:
    def test_approval_rate_zero_when_no_decisions(self, store):
        c = store.create(_make_create_req())
        updated = store.update_progress(c.id, processed=5)
        assert updated.progress.approval_rate == 0.0

    def test_pending_review_tracked(self, store):
        c = store.create(_make_create_req())
        updated = store.update_progress(c.id, pending_review=8)
        assert updated.progress.total_pending_review == 8

    def test_pending_review_cumulative(self, store):
        c = store.create(_make_create_req())
        store.update_progress(c.id, pending_review=5)
        store.update_progress(c.id, pending_review=3)
        updated = store.get(c.id)
        assert updated.progress.total_pending_review == 8

    def test_approval_rate_precision(self, store):
        c = store.create(_make_create_req())
        store.update_progress(c.id, approved=1, rejected=2)
        updated = store.get(c.id)
        assert updated.progress.approval_rate == 0.333

    def test_goal_meetings_booked_does_not_complete(self, store):
        c = store.create(_make_create_req(
            goal=CampaignGoal(target_count=10, metric="meetings_booked"),
        ))
        store.update(c.id, UpdateCampaignRequest(status=CampaignStatus.active))
        store.update_progress(c.id, sent=100)
        updated = store.get(c.id)
        assert updated.status == CampaignStatus.active  # meetings_booked is pass-through

    def test_goal_target_zero_does_not_complete(self, store):
        c = store.create(_make_create_req(
            goal=CampaignGoal(target_count=0, metric="emails_sent"),
        ))
        store.update(c.id, UpdateCampaignRequest(status=CampaignStatus.active))
        store.update_progress(c.id, sent=50)
        updated = store.get(c.id)
        assert updated.status == CampaignStatus.active

    def test_goal_not_reached_stays_active(self, store):
        c = store.create(_make_create_req(
            goal=CampaignGoal(target_count=100, metric="emails_sent"),
        ))
        store.update(c.id, UpdateCampaignRequest(status=CampaignStatus.active))
        store.update_progress(c.id, sent=99)
        updated = store.get(c.id)
        assert updated.status == CampaignStatus.active

    def test_goal_exceeded_still_completes(self, store):
        c = store.create(_make_create_req(
            goal=CampaignGoal(target_count=10, metric="emails_sent"),
        ))
        store.update(c.id, UpdateCampaignRequest(status=CampaignStatus.active))
        store.update_progress(c.id, sent=50)
        updated = store.get(c.id)
        assert updated.status == CampaignStatus.completed

    def test_all_progress_fields_cumulative(self, store):
        c = store.create(_make_create_req())
        store.update_progress(c.id, processed=3, approved=2, rejected=1, sent=2, pending_review=1)
        store.update_progress(c.id, processed=7, approved=5, rejected=2, sent=4, pending_review=3)
        p = store.get(c.id).progress
        assert p.total_processed == 10
        assert p.total_approved == 7
        assert p.total_rejected == 3
        assert p.total_sent == 6
        assert p.total_pending_review == 4
        assert p.approval_rate == 0.7


# ---------------------------------------------------------------------------
# Deeper: Active / due campaigns
# ---------------------------------------------------------------------------


class TestActiveDueDeeper:
    def test_active_excludes_paused(self, store):
        c = store.create(_make_create_req())
        store.update(c.id, UpdateCampaignRequest(status=CampaignStatus.paused))
        assert len(store.get_active_campaigns()) == 0

    def test_active_excludes_completed(self, store):
        c = store.create(_make_create_req())
        store.update(c.id, UpdateCampaignRequest(status=CampaignStatus.completed))
        assert len(store.get_active_campaigns()) == 0

    def test_active_excludes_draft(self, store):
        store.create(_make_create_req())
        assert len(store.get_active_campaigns()) == 0

    def test_due_requires_active_status(self, store):
        c = store.create(_make_create_req(
            audience=[{"n": 1}],
            schedule=CampaignSchedule(next_run_at=time.time() - 100),
        ))
        # draft → not due
        assert len(store.get_due_campaigns()) == 0
        store.update(c.id, UpdateCampaignRequest(status=CampaignStatus.paused))
        assert len(store.get_due_campaigns()) == 0

    def test_due_requires_next_run_at(self, store):
        c = store.create(_make_create_req(
            audience=[{"n": 1}],
            schedule=CampaignSchedule(next_run_at=None),
        ))
        store.update(c.id, UpdateCampaignRequest(status=CampaignStatus.active))
        assert len(store.get_due_campaigns()) == 0

    def test_due_multiple_campaigns(self, store):
        for i in range(3):
            c = store.create(_make_create_req(
                name=f"Due{i}",
                audience=[{"n": 1}],
                schedule=CampaignSchedule(next_run_at=time.time() - 100),
            ))
            store.update(c.id, UpdateCampaignRequest(status=CampaignStatus.active))
        assert len(store.get_due_campaigns()) == 3


# ---------------------------------------------------------------------------
# Deeper: Schedule next run
# ---------------------------------------------------------------------------


class TestScheduleNextRunDeeper:
    def test_unknown_frequency_clears_next_run(self, store):
        c = store.create(_make_create_req(
            schedule=CampaignSchedule(frequency="custom", next_run_at=1234.0),
        ))
        updated = store.schedule_next_run(c.id)
        assert updated.schedule.next_run_at is None

    def test_schedule_updates_timestamp(self, store):
        c = store.create(_make_create_req(schedule=CampaignSchedule(frequency="daily")))
        old_ts = c.updated_at
        time.sleep(0.01)
        updated = store.schedule_next_run(c.id)
        assert updated.updated_at > old_ts

    def test_schedule_persists(self, store, tmp_path):
        c = store.create(_make_create_req(schedule=CampaignSchedule(frequency="daily")))
        store.schedule_next_run(c.id)
        s2 = CampaignStore(data_dir=tmp_path)
        s2.load()
        reloaded = s2.get(c.id)
        assert reloaded.schedule.next_run_at is not None


# ---------------------------------------------------------------------------
# Deeper: list_all
# ---------------------------------------------------------------------------


class TestListAllDeeper:
    def test_list_all_returns_all_statuses(self, store):
        for status in [CampaignStatus.draft, CampaignStatus.active, CampaignStatus.paused, CampaignStatus.completed]:
            c = store.create(_make_create_req(name=status.value))
            if status != CampaignStatus.draft:
                store.update(c.id, UpdateCampaignRequest(status=status))
        assert len(store.list_all()) == 4

    def test_list_all_filter_no_match(self, store):
        store.create(_make_create_req())
        assert store.list_all(status="active") == []
