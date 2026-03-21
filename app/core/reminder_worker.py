"""Reminder worker — scans portals for due/overdue actions and sends Slack digests.

Runs every 6 hours. Groups reminders by client and sends one message per client.
Tracks last_reminded_at per action to avoid duplicate notifications.
"""

import asyncio
import logging
import time
from datetime import datetime, timedelta

logger = logging.getLogger("clay-webhook-os")


class ReminderWorker:
    """Background worker for due date reminders."""

    def __init__(self, portal_store, portal_notifier, interval_hours: int = 6):
        self._store = portal_store
        self._notifier = portal_notifier
        self._interval = interval_hours * 3600
        self._task: asyncio.Task | None = None
        self._running = False

    async def start(self) -> None:
        self._running = True
        self._task = asyncio.create_task(self._loop())
        logger.info("[reminder-worker] Started (interval=%dh)", self._interval // 3600)

    async def stop(self) -> None:
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("[reminder-worker] Stopped")

    async def _loop(self) -> None:
        # Initial delay: wait 60s after startup before first scan
        await asyncio.sleep(60)
        while self._running:
            try:
                await self._scan()
            except Exception as e:
                logger.warning("[reminder-worker] Scan error: %s", e)
            await asyncio.sleep(self._interval)

    async def _scan(self) -> None:
        """Scan all portals and send reminders for upcoming/overdue actions."""
        portals = self._store.list_portals()
        now = time.time()
        today = datetime.now().strftime("%Y-%m-%d")
        tomorrow = (datetime.now() + timedelta(days=1)).strftime("%Y-%m-%d")

        for portal_info in portals:
            slug = portal_info["slug"]
            actions = self._store.list_actions(slug)
            upcoming = []
            overdue = []

            for action in actions:
                if action.get("status") == "done":
                    continue
                due = action.get("due_date")
                if not due:
                    continue

                # Skip if reminded within the last interval
                last_reminded = action.get("last_reminded_at", 0)
                if now - last_reminded < self._interval:
                    continue

                if due < today:
                    overdue.append(action)
                elif due <= tomorrow:
                    upcoming.append(action)

            if not upcoming and not overdue:
                continue

            # Send notification
            try:
                await self._notifier.notify_due_date_reminder(slug, upcoming, overdue)
            except Exception as e:
                logger.warning("[reminder-worker] Failed to notify %s: %s", slug, e)
                continue

            # Update last_reminded_at on notified actions
            all_actions = self._store.list_actions(slug)
            notified_ids = {a["id"] for a in upcoming + overdue}
            for a in all_actions:
                if a["id"] in notified_ids:
                    a["last_reminded_at"] = now
            self._store._save_actions(slug, all_actions)

        logger.info("[reminder-worker] Scan complete")
