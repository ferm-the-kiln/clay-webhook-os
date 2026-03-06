import json
import logging
import time
from pathlib import Path

from app.models.campaigns import (
    Campaign,
    CampaignGoal,
    CampaignSchedule,
    CampaignStatus,
    CreateCampaignRequest,
    UpdateCampaignRequest,
)

logger = logging.getLogger("clay-webhook-os")


class CampaignStore:
    def __init__(self, data_dir: Path):
        self._data_dir = data_dir / "campaigns"
        self._file = self._data_dir / "campaigns.json"
        self._campaigns: dict[str, Campaign] = {}

    def load(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        if self._file.exists():
            raw = json.loads(self._file.read_text())
            for item in raw:
                campaign = Campaign(**item)
                self._campaigns[campaign.id] = campaign
            logger.info("[campaigns] Loaded %d campaigns", len(self._campaigns))

    def _save(self) -> None:
        self._data_dir.mkdir(parents=True, exist_ok=True)
        raw = [c.model_dump() for c in self._campaigns.values()]
        self._file.write_text(json.dumps(raw, indent=2))

    def list_all(self, status: str | None = None) -> list[Campaign]:
        campaigns = list(self._campaigns.values())
        if status:
            campaigns = [c for c in campaigns if c.status == status]
        return sorted(campaigns, key=lambda c: c.created_at, reverse=True)

    def get(self, campaign_id: str) -> Campaign | None:
        return self._campaigns.get(campaign_id)

    def create(self, data: CreateCampaignRequest) -> Campaign:
        campaign = Campaign(
            name=data.name,
            description=data.description,
            pipeline=data.pipeline,
            destination_id=data.destination_id,
            client_slug=data.client_slug,
            goal=data.goal or CampaignGoal(),
            schedule=data.schedule or CampaignSchedule(),
            audience=data.audience,
            confidence_threshold=data.confidence_threshold,
            instructions=data.instructions,
            model=data.model,
        )
        self._campaigns[campaign.id] = campaign
        self._save()
        return campaign

    def update(self, campaign_id: str, data: UpdateCampaignRequest) -> Campaign | None:
        campaign = self._campaigns.get(campaign_id)
        if campaign is None:
            return None
        updates = data.model_dump(exclude_none=True)
        if updates:
            for key, value in updates.items():
                setattr(campaign, key, value)
            campaign.updated_at = time.time()
            self._campaigns[campaign_id] = campaign
            self._save()
        return campaign

    def delete(self, campaign_id: str) -> bool:
        if campaign_id not in self._campaigns:
            return False
        del self._campaigns[campaign_id]
        self._save()
        return True

    def add_audience(self, campaign_id: str, rows: list[dict]) -> Campaign | None:
        campaign = self._campaigns.get(campaign_id)
        if campaign is None:
            return None
        campaign.audience.extend(rows)
        campaign.updated_at = time.time()
        self._save()
        return campaign

    def advance_cursor(self, campaign_id: str, count: int) -> Campaign | None:
        campaign = self._campaigns.get(campaign_id)
        if campaign is None:
            return None
        campaign.audience_cursor += count
        campaign.updated_at = time.time()
        self._save()
        return campaign

    def update_progress(
        self,
        campaign_id: str,
        processed: int = 0,
        approved: int = 0,
        sent: int = 0,
        rejected: int = 0,
        pending_review: int = 0,
    ) -> Campaign | None:
        campaign = self._campaigns.get(campaign_id)
        if campaign is None:
            return None
        p = campaign.progress
        p.total_processed += processed
        p.total_approved += approved
        p.total_sent += sent
        p.total_rejected += rejected
        p.total_pending_review += pending_review
        total_decided = p.total_approved + p.total_rejected
        p.approval_rate = round(p.total_approved / total_decided, 3) if total_decided > 0 else 0.0
        campaign.updated_at = time.time()
        # Check if goal met
        if campaign.goal.target_count > 0:
            if campaign.goal.metric == "emails_sent" and p.total_sent >= campaign.goal.target_count:
                campaign.status = CampaignStatus.completed
            elif campaign.goal.metric == "meetings_booked":
                pass  # tracked externally
        self._save()
        return campaign

    def get_next_batch(self, campaign_id: str) -> list[dict]:
        campaign = self._campaigns.get(campaign_id)
        if campaign is None:
            return []
        start = campaign.audience_cursor
        end = start + campaign.schedule.batch_size
        return campaign.audience[start:end]

    def get_active_campaigns(self) -> list[Campaign]:
        return [c for c in self._campaigns.values() if c.status == CampaignStatus.active]

    def get_due_campaigns(self) -> list[Campaign]:
        now = time.time()
        return [
            c for c in self._campaigns.values()
            if c.status == CampaignStatus.active
            and c.schedule.next_run_at is not None
            and c.schedule.next_run_at <= now
            and c.audience_cursor < len(c.audience)
        ]

    def schedule_next_run(self, campaign_id: str) -> Campaign | None:
        campaign = self._campaigns.get(campaign_id)
        if campaign is None:
            return None
        now = time.time()
        if campaign.schedule.frequency == "daily":
            campaign.schedule.next_run_at = now + 86400
        elif campaign.schedule.frequency == "weekly":
            campaign.schedule.next_run_at = now + 604800
        else:
            campaign.schedule.next_run_at = None
        campaign.updated_at = time.time()
        self._save()
        return campaign
