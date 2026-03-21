"""Portal notifier — sends Slack notifications for client portal events.

Fires async POST to per-client Slack incoming webhook URLs.
Reads webhook URL from portal.json metadata (slack_webhook_url field).
Non-blocking: failures are logged but never raise to the caller.
"""

import logging
import time

import httpx

logger = logging.getLogger("clay-webhook-os")

# Dashboard URL for "View Portal" links
DASHBOARD_URL = "https://dashboard-beta-sable-36.vercel.app"


class PortalNotifier:
    """Sends Slack notifications for portal events."""

    def __init__(self, portal_store):
        self._store = portal_store
        self._client = httpx.AsyncClient(timeout=10.0)

    async def close(self):
        await self._client.aclose()

    # ── Public API ────────────────────────────────────────

    async def notify_action_assigned(self, slug: str, action: dict) -> None:
        """Notify when an action is assigned to the client."""
        if action.get("owner") != "client":
            return
        client_name = self._store._client_name(slug)
        priority = action.get("priority", "normal")
        priority_emoji = {"high": ":red_circle:", "normal": ":large_blue_circle:", "low": ":white_circle:"}.get(priority, "")

        blocks = [
            self._header(f"New Action Item for {client_name}"),
            self._section(
                f"{priority_emoji} *{action['title']}*\n"
                f"Priority: {priority.title()} | Owner: Client"
                + (f"\nDue: {action['due_date']}" if action.get("due_date") else "")
            ),
        ]
        if action.get("description"):
            blocks.append(self._section(f"_{action['description']}_"))
        blocks.append(self._portal_link(slug))

        await self._send(slug, blocks, f"New action: {action['title']}")

    async def notify_deliverable_posted(self, slug: str, title: str, body: str = "") -> None:
        """Notify when a deliverable is posted for review."""
        client_name = self._store._client_name(slug)
        blocks = [
            self._header(f"Deliverable Ready — {client_name}"),
            self._section(
                f":package: *{title}*"
                + (f"\n{body[:200]}{'...' if len(body) > 200 else ''}" if body else "")
            ),
            self._section("_Please review and approve at your earliest convenience._"),
            self._portal_link(slug),
        ]
        await self._send(slug, blocks, f"Deliverable ready: {title}")

    async def notify_update_posted(self, slug: str, type_: str, title: str, body: str = "") -> None:
        """Notify on milestone or general update posts."""
        if type_ not in ("milestone", "update"):
            return
        client_name = self._store._client_name(slug)
        emoji = ":trophy:" if type_ == "milestone" else ":memo:"
        blocks = [
            self._header(f"{type_.title()} — {client_name}"),
            self._section(
                f"{emoji} *{title}*"
                + (f"\n{body[:200]}{'...' if len(body) > 200 else ''}" if body else "")
            ),
            self._portal_link(slug),
        ]
        await self._send(slug, blocks, f"{type_.title()}: {title}")

    async def notify_sop_updated(self, slug: str, sop_title: str) -> None:
        """Notify when an SOP is updated."""
        client_name = self._store._client_name(slug)
        blocks = [
            self._header(f"SOP Updated — {client_name}"),
            self._section(f":page_facing_up: *{sop_title}* has been updated."),
            self._portal_link(slug),
        ]
        await self._send(slug, blocks, f"SOP updated: {sop_title}")

    async def notify_comment_posted(self, slug: str, update_title: str, comment_body: str, author: str) -> None:
        """Notify when a comment is posted on an update."""
        client_name = self._store._client_name(slug)
        preview = comment_body[:200] + ("..." if len(comment_body) > 200 else "")
        blocks = [
            self._header(f"New Comment — {client_name}"),
            self._section(
                f":speech_balloon: *{author}* commented on *{update_title}*\n"
                f"_{preview}_"
            ),
            self._portal_link(slug),
        ]
        await self._send(slug, blocks, f"New comment by {author} on {update_title}")

    async def notify_due_date_reminder(self, slug: str, upcoming: list[dict], overdue: list[dict]) -> None:
        """Send a digest of upcoming and overdue actions for a client."""
        client_name = self._store._client_name(slug)
        parts = []
        if overdue:
            parts.append(f":rotating_light: *{len(overdue)} overdue action{'s' if len(overdue) != 1 else ''}*")
            for a in overdue[:5]:
                parts.append(f"  • {a['title']} (due {a.get('due_date', '?')})")
        if upcoming:
            parts.append(f":clock3: *{len(upcoming)} due within 24h*")
            for a in upcoming[:5]:
                parts.append(f"  • {a['title']} (due {a.get('due_date', '?')})")
        blocks = [
            self._header(f"Action Reminder — {client_name}"),
            self._section("\n".join(parts)),
            self._portal_link(slug),
        ]
        await self._send(slug, blocks, f"Action reminder for {client_name}: {len(overdue)} overdue, {len(upcoming)} upcoming")

    # ── Block Kit Helpers ─────────────────────────────────

    def _header(self, text: str) -> dict:
        return {"type": "header", "text": {"type": "plain_text", "text": text[:150], "emoji": True}}

    def _section(self, text: str) -> dict:
        return {"type": "section", "text": {"type": "mrkdwn", "text": text}}

    def _portal_link(self, slug: str) -> dict:
        meta = self._store.get_meta(slug)
        token = meta.get("share_token")
        if token:
            url = f"{DASHBOARD_URL}/portal-view/{slug}?token={token}"
            label = "View Portal"
        else:
            url = f"{DASHBOARD_URL}/clients/{slug}"
            label = "Open Portal (internal)"
        return {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": label, "emoji": True},
                    "url": url,
                    "style": "primary",
                }
            ],
        }

    # ── Send ──────────────────────────────────────────────

    async def _send(self, slug: str, blocks: list[dict], fallback_text: str) -> None:
        """POST to the client's Slack webhook. Never raises."""
        meta = self._store.get_meta(slug)
        webhook_url = meta.get("slack_webhook_url")
        if not webhook_url:
            return

        payload = {
            "text": fallback_text,
            "blocks": blocks,
        }

        try:
            resp = await self._client.post(webhook_url, json=payload)
            if resp.status_code == 200:
                logger.info("[portal-notify] Sent Slack notification for %s: %s", slug, fallback_text)
            else:
                logger.warning(
                    "[portal-notify] Slack webhook returned %d for %s: %s",
                    resp.status_code, slug, resp.text[:200],
                )
        except Exception as e:
            logger.warning("[portal-notify] Failed to send Slack notification for %s: %s", slug, e)
