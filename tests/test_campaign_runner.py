import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.core.campaign_runner import CampaignRunner
from app.models.campaigns import CampaignStatus


def _mock_campaign(**kwargs):
    defaults = dict(
        id="c1",
        name="Test Campaign",
        pipeline="full-outbound",
        status=CampaignStatus.active,
        model="opus",
        instructions=None,
        client_slug=None,
        destination_id=None,
        confidence_threshold=0.8,
        audience_cursor=0,
    )
    defaults.update(kwargs)
    m = MagicMock()
    for k, v in defaults.items():
        setattr(m, k, v)
    return m


@pytest.fixture
def deps():
    campaign_store = MagicMock()
    review_queue = MagicMock()
    pool = AsyncMock()
    cache = MagicMock()
    destination_store = MagicMock()
    destination_store.push_data = AsyncMock()
    job_queue = MagicMock()
    return campaign_store, review_queue, pool, cache, destination_store, job_queue


@pytest.fixture
def runner(deps):
    cs, rq, pool, cache, ds, jq = deps
    return CampaignRunner(
        campaign_store=cs,
        review_queue=rq,
        pool=pool,
        cache=cache,
        destination_store=ds,
        job_queue=jq,
    )


# ---------------------------------------------------------------------------
# Start / stop
# ---------------------------------------------------------------------------


class TestStartStop:
    async def test_start_creates_task(self, runner):
        with patch.object(runner, "_loop", new_callable=AsyncMock):
            await runner.start()
            assert runner._task is not None
            await runner.stop()

    async def test_stop_cancels_task(self, runner):
        with patch.object(runner, "_loop", new_callable=AsyncMock):
            await runner.start()
            task = runner._task
            await runner.stop()
            assert task.cancelled() or task.done()

    async def test_stop_without_start(self, runner):
        await runner.stop()  # should not raise


# ---------------------------------------------------------------------------
# Loop
# ---------------------------------------------------------------------------


class TestLoop:
    async def test_loop_processes_due_campaigns(self, runner, deps):
        cs, *_ = deps
        campaign = _mock_campaign()
        cs.get_due_campaigns.return_value = [campaign]

        with patch.object(runner, "run_batch", new_callable=AsyncMock, return_value={}):
            with patch("app.core.campaign_runner.asyncio.sleep", side_effect=asyncio.CancelledError):
                with pytest.raises(asyncio.CancelledError):
                    await runner._loop()
            runner.run_batch.assert_called_once_with("c1")

    async def test_loop_survives_batch_error(self, runner, deps):
        cs, *_ = deps
        campaign = _mock_campaign()
        cs.get_due_campaigns.side_effect = [
            [campaign],
            [],
        ]

        call_count = 0

        async def flaky_batch(cid):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("batch failed")
            return {}

        with patch.object(runner, "run_batch", side_effect=flaky_batch):
            with patch(
                "app.core.campaign_runner.asyncio.sleep",
                side_effect=[None, asyncio.CancelledError],
            ):
                with pytest.raises(asyncio.CancelledError):
                    await runner._loop()

        assert call_count == 1  # called once, failed, loop continued

    async def test_loop_survives_get_due_error(self, runner, deps):
        cs, *_ = deps
        cs.get_due_campaigns.side_effect = [
            RuntimeError("store error"),
            [],
        ]

        with patch(
            "app.core.campaign_runner.asyncio.sleep",
            side_effect=[None, asyncio.CancelledError],
        ):
            with pytest.raises(asyncio.CancelledError):
                await runner._loop()


# ---------------------------------------------------------------------------
# run_batch
# ---------------------------------------------------------------------------


class TestRunBatch:
    async def test_campaign_not_found(self, runner, deps):
        cs, *_ = deps
        cs.get.return_value = None
        result = await runner.run_batch("nope")
        assert "error" in result

    async def test_campaign_not_active(self, runner, deps):
        cs, *_ = deps
        cs.get.return_value = _mock_campaign(status=CampaignStatus.draft)
        result = await runner.run_batch("c1")
        assert "error" in result
        assert "draft" in result["error"]

    async def test_no_rows_completes_campaign(self, runner, deps):
        cs, *_ = deps
        cs.get.return_value = _mock_campaign()
        cs.get_next_batch.return_value = []
        result = await runner.run_batch("c1")
        assert result["status"] == "completed"
        cs.update.assert_called_once()

    @patch("app.core.campaign_runner.run_pipeline")
    async def test_auto_routing_high_confidence(self, mock_pipeline, runner, deps):
        cs, rq, pool, cache, ds, jq = deps
        campaign = _mock_campaign(destination_id="d1")
        cs.get.return_value = campaign
        cs.get_next_batch.return_value = [{"name": "Alice"}]

        mock_pipeline.return_value = {
            "confidence": 0.95,
            "routing": "auto",
            "final_output": {"email": "Hi Alice"},
        }

        dest = MagicMock()
        ds.get.return_value = dest

        result = await runner.run_batch("c1")
        assert result["auto_sent"] == 1
        assert result["queued_for_review"] == 0
        ds.push_data.assert_called_once_with(dest, {"email": "Hi Alice"})
        rq.add.assert_not_called()

    @patch("app.core.campaign_runner.run_pipeline")
    async def test_review_routing_low_confidence(self, mock_pipeline, runner, deps):
        cs, rq, *_ = deps
        cs.get.return_value = _mock_campaign()
        cs.get_next_batch.return_value = [{"name": "Alice"}]

        mock_pipeline.return_value = {
            "confidence": 0.5,
            "routing": "review",
            "final_output": {"email": "Maybe Alice?"},
        }

        result = await runner.run_batch("c1")
        assert result["auto_sent"] == 0
        assert result["queued_for_review"] == 1
        rq.add.assert_called_once()
        review_item = rq.add.call_args[0][0]
        assert review_item.campaign_id == "c1"
        assert review_item.confidence_score == 0.5

    @patch("app.core.campaign_runner.run_pipeline")
    async def test_client_slug_injected(self, mock_pipeline, runner, deps):
        cs, *_ = deps
        cs.get.return_value = _mock_campaign(client_slug="acme")
        cs.get_next_batch.return_value = [{"name": "Alice"}]
        mock_pipeline.return_value = {
            "confidence": 0.95,
            "routing": "auto",
            "final_output": {},
        }

        await runner.run_batch("c1")
        call_kwargs = mock_pipeline.call_args[1]
        assert call_kwargs["data"]["client_slug"] == "acme"

    @patch("app.core.campaign_runner.run_pipeline")
    async def test_advances_cursor_and_progress(self, mock_pipeline, runner, deps):
        cs, *_ = deps
        cs.get.return_value = _mock_campaign()
        cs.get_next_batch.return_value = [{"n": 1}, {"n": 2}, {"n": 3}]
        mock_pipeline.return_value = {
            "confidence": 0.95,
            "routing": "auto",
            "final_output": {},
        }

        await runner.run_batch("c1")
        cs.advance_cursor.assert_called_once_with("c1", 3)
        cs.update_progress.assert_called_once()
        progress_kwargs = cs.update_progress.call_args[1]
        assert progress_kwargs["processed"] == 3

    @patch("app.core.campaign_runner.run_pipeline")
    async def test_schedules_next_run(self, mock_pipeline, runner, deps):
        cs, *_ = deps
        cs.get.return_value = _mock_campaign()
        cs.get_next_batch.return_value = [{"n": 1}]
        mock_pipeline.return_value = {
            "confidence": 0.95,
            "routing": "auto",
            "final_output": {},
        }

        await runner.run_batch("c1")
        cs.schedule_next_run.assert_called_once_with("c1")

    @patch("app.core.campaign_runner.run_pipeline")
    async def test_pipeline_error_continues(self, mock_pipeline, runner, deps):
        cs, *_ = deps
        cs.get.return_value = _mock_campaign()
        cs.get_next_batch.return_value = [{"n": 1}, {"n": 2}]
        mock_pipeline.side_effect = [
            RuntimeError("pipeline crashed"),
            {"confidence": 0.9, "routing": "auto", "final_output": {}},
        ]

        result = await runner.run_batch("c1")
        assert len(result["results"]) == 2
        assert result["results"][0]["routing"] == "error"
        assert "pipeline crashed" in result["results"][0]["error"]
        assert result["results"][1]["routing"] == "auto_sent"

    @patch("app.core.campaign_runner.run_pipeline")
    async def test_auto_without_destination(self, mock_pipeline, runner, deps):
        cs, rq, _, _, ds, _ = deps
        cs.get.return_value = _mock_campaign(destination_id=None)
        cs.get_next_batch.return_value = [{"n": 1}]
        mock_pipeline.return_value = {
            "confidence": 0.95,
            "routing": "auto",
            "final_output": {"email": "Hi"},
        }

        result = await runner.run_batch("c1")
        # No destination, so push_data is not called but still counts as auto_sent=0
        ds.push_data.assert_not_called()
        assert result["results"][0]["routing"] == "auto_sent"

    @patch("app.core.campaign_runner.run_pipeline")
    async def test_batch_result_structure(self, mock_pipeline, runner, deps):
        cs, *_ = deps
        cs.get.return_value = _mock_campaign()
        cs.get_next_batch.return_value = [{"n": 1}]
        mock_pipeline.return_value = {
            "confidence": 0.85,
            "routing": "auto",
            "final_output": {"x": 1},
        }

        result = await runner.run_batch("c1")
        assert result["campaign_id"] == "c1"
        assert result["batch_size"] == 1
        assert "auto_sent" in result
        assert "queued_for_review" in result
        assert "results" in result

    @patch("app.core.campaign_runner.run_pipeline")
    async def test_review_item_has_row_id(self, mock_pipeline, runner, deps):
        cs, rq, *_ = deps
        cs.get.return_value = _mock_campaign()
        cs.get_next_batch.return_value = [{"name": "Alice", "row_id": "r42"}]
        mock_pipeline.return_value = {
            "confidence": 0.3,
            "routing": "review",
            "final_output": {"email": "..."},
        }

        await runner.run_batch("c1")
        review_item = rq.add.call_args[0][0]
        assert review_item.row_id == "r42"
        assert review_item.input_data == {"name": "Alice", "row_id": "r42"}

    @patch("app.core.campaign_runner.run_pipeline")
    async def test_confidence_at_exact_threshold(self, mock_pipeline, runner, deps):
        """Confidence == threshold routes as auto."""
        cs, rq, _, _, ds, _ = deps
        cs.get.return_value = _mock_campaign(confidence_threshold=0.8)
        cs.get_next_batch.return_value = [{"n": 1}]
        mock_pipeline.return_value = {
            "confidence": 0.8,  # exactly at threshold
            "routing": "auto",
            "final_output": {"x": 1},
        }

        result = await runner.run_batch("c1")
        assert result["results"][0]["routing"] == "auto_sent"
        rq.add.assert_not_called()

    @patch("app.core.campaign_runner.run_pipeline")
    async def test_confidence_just_below_threshold(self, mock_pipeline, runner, deps):
        """Confidence < threshold routes to review."""
        cs, rq, *_ = deps
        cs.get.return_value = _mock_campaign(confidence_threshold=0.8)
        cs.get_next_batch.return_value = [{"n": 1}]
        mock_pipeline.return_value = {
            "confidence": 0.79,
            "routing": "auto",
            "final_output": {},
        }

        result = await runner.run_batch("c1")
        assert result["results"][0]["routing"] == "review"
        rq.add.assert_called_once()

    @patch("app.core.campaign_runner.run_pipeline")
    async def test_destination_configured_but_not_found(self, mock_pipeline, runner, deps):
        """destination_id is set but dest object is gone — no push, still auto_sent."""
        cs, rq, _, _, ds, _ = deps
        cs.get.return_value = _mock_campaign(destination_id="d-gone")
        cs.get_next_batch.return_value = [{"n": 1}]
        ds.get.return_value = None  # destination was deleted
        mock_pipeline.return_value = {
            "confidence": 0.95,
            "routing": "auto",
            "final_output": {},
        }

        result = await runner.run_batch("c1")
        assert result["results"][0]["routing"] == "auto_sent"
        assert result["auto_sent"] == 0  # push didn't happen
        ds.push_data.assert_not_called()

    @patch("app.core.campaign_runner.run_pipeline")
    async def test_pipeline_result_missing_keys_defaults(self, mock_pipeline, runner, deps):
        """Pipeline result with no confidence/routing/final_output uses defaults."""
        cs, rq, *_ = deps
        cs.get.return_value = _mock_campaign()
        cs.get_next_batch.return_value = [{"n": 1}]
        mock_pipeline.return_value = {}  # all keys missing

        result = await runner.run_batch("c1")
        # confidence=1.0 >= 0.8, routing="auto" → auto_sent
        assert result["results"][0]["routing"] == "auto_sent"
        assert result["results"][0]["confidence"] == 1.0

    @patch("app.core.campaign_runner.run_pipeline")
    async def test_nonzero_cursor_affects_row_index(self, mock_pipeline, runner, deps):
        cs, *_ = deps
        cs.get.return_value = _mock_campaign(audience_cursor=100)
        cs.get_next_batch.return_value = [{"n": 1}, {"n": 2}]
        mock_pipeline.return_value = {
            "confidence": 0.95,
            "routing": "auto",
            "final_output": {},
        }

        result = await runner.run_batch("c1")
        assert result["results"][0]["row_index"] == 100
        assert result["results"][1]["row_index"] == 101

    @patch("app.core.campaign_runner.run_pipeline")
    async def test_review_item_fields(self, mock_pipeline, runner, deps):
        """Review item has correct skill, model, client_slug from campaign."""
        cs, rq, *_ = deps
        cs.get.return_value = _mock_campaign(
            pipeline="full-outbound", model="sonnet", client_slug="acme"
        )
        cs.get_next_batch.return_value = [{"name": "Alice"}]
        mock_pipeline.return_value = {
            "confidence": 0.3,
            "routing": "review",
            "final_output": {"email": "hi"},
        }

        await runner.run_batch("c1")
        review_item = rq.add.call_args[0][0]
        assert review_item.skill == "full-outbound"
        assert review_item.model == "sonnet"
        assert review_item.client_slug == "acme"
        assert review_item.output == {"email": "hi"}

    @patch("app.core.campaign_runner.run_pipeline")
    async def test_progress_counts_sent_and_review(self, mock_pipeline, runner, deps):
        cs, rq, _, _, ds, _ = deps
        campaign = _mock_campaign(destination_id="d1")
        cs.get.return_value = campaign
        cs.get_next_batch.return_value = [{"n": 1}, {"n": 2}]
        ds.get.return_value = MagicMock()

        mock_pipeline.side_effect = [
            {"confidence": 0.95, "routing": "auto", "final_output": {}},
            {"confidence": 0.3, "routing": "review", "final_output": {}},
        ]

        await runner.run_batch("c1")
        progress = cs.update_progress.call_args[1]
        assert progress["processed"] == 2
        assert progress["sent"] == 1
        assert progress["pending_review"] == 1

    @patch("app.core.campaign_runner.run_pipeline")
    async def test_mixed_routing_counts(self, mock_pipeline, runner, deps):
        cs, rq, _, _, ds, _ = deps
        campaign = _mock_campaign(destination_id="d1")
        cs.get.return_value = campaign
        cs.get_next_batch.return_value = [{"n": 1}, {"n": 2}, {"n": 3}]
        ds.get.return_value = MagicMock()

        mock_pipeline.side_effect = [
            {"confidence": 0.95, "routing": "auto", "final_output": {}},
            {"confidence": 0.3, "routing": "review", "final_output": {}},
            {"confidence": 0.9, "routing": "auto", "final_output": {}},
        ]

        result = await runner.run_batch("c1")
        assert result["auto_sent"] == 2
        assert result["queued_for_review"] == 1
        assert ds.push_data.call_count == 2
        assert rq.add.call_count == 1


# ---------------------------------------------------------------------------
# push_approved
# ---------------------------------------------------------------------------


class TestPushApproved:
    async def test_item_not_found(self, runner, deps):
        _, rq, *_ = deps
        rq.get.return_value = None
        result = await runner.push_approved("nope")
        assert "error" in result

    async def test_no_campaign_on_item(self, runner, deps):
        _, rq, *_ = deps
        item = MagicMock()
        item.campaign_id = None
        rq.get.return_value = item
        result = await runner.push_approved("r1")
        assert "error" in result

    async def test_campaign_not_found(self, runner, deps):
        cs, rq, *_ = deps
        item = MagicMock()
        item.campaign_id = "c1"
        rq.get.return_value = item
        cs.get.return_value = None
        result = await runner.push_approved("r1")
        assert "error" in result

    async def test_push_with_destination(self, runner, deps):
        cs, rq, _, _, ds, _ = deps
        item = MagicMock()
        item.campaign_id = "c1"
        item.output = {"email": "Hello"}
        rq.get.return_value = item

        campaign = _mock_campaign(destination_id="d1")
        cs.get.return_value = campaign
        dest = MagicMock()
        ds.get.return_value = dest
        ds.push_data.return_value = {"status": 200}

        result = await runner.push_approved("r1")
        assert result["ok"] is True
        assert result["push_result"] == {"status": 200}
        ds.push_data.assert_called_once_with(dest, {"email": "Hello"})
        cs.update_progress.assert_called_once_with("c1", approved=1, sent=1, pending_review=-1)

    async def test_push_without_destination(self, runner, deps):
        cs, rq, _, _, ds, _ = deps
        item = MagicMock()
        item.campaign_id = "c1"
        rq.get.return_value = item

        campaign = _mock_campaign(destination_id=None)
        cs.get.return_value = campaign

        result = await runner.push_approved("r1")
        assert result["ok"] is True
        assert "no destination" in result["message"].lower()
        ds.push_data.assert_not_called()
        cs.update_progress.assert_called_once_with("c1", approved=1, pending_review=-1)

    async def test_push_destination_not_found(self, runner, deps):
        cs, rq, _, _, ds, _ = deps
        item = MagicMock()
        item.campaign_id = "c1"
        rq.get.return_value = item

        campaign = _mock_campaign(destination_id="d-gone")
        cs.get.return_value = campaign
        ds.get.return_value = None  # destination removed

        result = await runner.push_approved("r1")
        assert result["ok"] is True
        assert "no destination" in result["message"].lower()
