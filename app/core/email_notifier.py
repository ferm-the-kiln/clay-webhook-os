"""Email notifier — sends email notifications for portal events.

Uses smtplib in a thread pool executor to avoid blocking the event loop.
HTML templates for each event type. Non-blocking: failures are logged only.
"""

import asyncio
import logging
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

logger = logging.getLogger("clay-webhook-os")

DASHBOARD_URL = "https://dashboard-beta-sable-36.vercel.app"


def _html_wrapper(title: str, body_html: str, portal_url: str) -> str:
    """Wrap content in a styled HTML email template."""
    return f"""<!DOCTYPE html>
<html>
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width"></head>
<body style="margin:0;padding:0;background:#1a1a2e;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<div style="max-width:560px;margin:0 auto;padding:32px 24px;">
  <div style="background:#16213e;border:1px solid #2a2a4a;border-radius:12px;padding:24px;">
    <h2 style="color:#e2e8f0;font-size:18px;margin:0 0 16px;">{title}</h2>
    <div style="color:#a0aec0;font-size:14px;line-height:1.6;">{body_html}</div>
    <div style="margin-top:20px;">
      <a href="{portal_url}" style="display:inline-block;background:#2dd4bf;color:#0f172a;font-size:13px;font-weight:600;padding:8px 16px;border-radius:6px;text-decoration:none;">View Portal</a>
    </div>
  </div>
  <p style="color:#64748b;font-size:11px;text-align:center;margin-top:16px;">Clay Webhook OS</p>
</div>
</body></html>"""


class EmailNotifier:
    """Sends email notifications for portal events."""

    def __init__(
        self,
        portal_store,
        smtp_host: str = "",
        smtp_port: int = 587,
        smtp_user: str = "",
        smtp_pass: str = "",
        smtp_from: str = "",
    ):
        self._store = portal_store
        self._host = smtp_host
        self._port = smtp_port
        self._user = smtp_user
        self._pass = smtp_pass
        self._from = smtp_from

    @property
    def available(self) -> bool:
        return bool(self._host and self._user and self._pass)

    def _get_recipients(self, slug: str) -> list[str]:
        """Get email recipients from portal metadata."""
        meta = self._store.get_meta(slug)
        return meta.get("notification_emails", [])

    async def _send_email(self, to_addrs: list[str], subject: str, html: str) -> None:
        """Send email via SMTP in a thread pool. Never raises."""
        if not self.available or not to_addrs:
            return

        def _send():
            try:
                msg = MIMEMultipart("alternative")
                msg["From"] = self._from
                msg["To"] = ", ".join(to_addrs)
                msg["Subject"] = subject
                msg.attach(MIMEText(html, "html"))

                with smtplib.SMTP(self._host, self._port) as server:
                    server.starttls()
                    server.login(self._user, self._pass)
                    server.send_message(msg)
                logger.info("[email-notify] Sent to %s: %s", to_addrs, subject)
            except Exception as e:
                logger.warning("[email-notify] Failed to send to %s: %s", to_addrs, e)

        loop = asyncio.get_running_loop()
        await loop.run_in_executor(None, _send)

    def _portal_url(self, slug: str) -> str:
        meta = self._store.get_meta(slug)
        token = meta.get("share_token")
        if token:
            return f"{DASHBOARD_URL}/portal-view/{slug}?token={token}"
        return f"{DASHBOARD_URL}/clients/{slug}"

    async def notify_deliverable(self, slug: str, title: str, body: str = "") -> None:
        recipients = self._get_recipients(slug)
        if not recipients:
            return
        client_name = self._store._client_name(slug)
        preview = body[:300] if body else ""
        html = _html_wrapper(
            f"Deliverable Ready — {client_name}",
            f"<p><strong>{title}</strong></p><p>{preview}</p>"
            f"<p style='color:#94a3b8;font-style:italic;'>Please review and approve at your earliest convenience.</p>",
            self._portal_url(slug),
        )
        await self._send_email(recipients, f"Deliverable: {title} — {client_name}", html)

    async def notify_update(self, slug: str, type_: str, title: str, body: str = "") -> None:
        recipients = self._get_recipients(slug)
        if not recipients:
            return
        client_name = self._store._client_name(slug)
        preview = body[:300] if body else ""
        html = _html_wrapper(
            f"{type_.title()} — {client_name}",
            f"<p><strong>{title}</strong></p><p>{preview}</p>",
            self._portal_url(slug),
        )
        await self._send_email(recipients, f"{type_.title()}: {title} — {client_name}", html)

    async def notify_action(self, slug: str, action: dict) -> None:
        recipients = self._get_recipients(slug)
        if not recipients:
            return
        client_name = self._store._client_name(slug)
        due = f" (due {action.get('due_date')})" if action.get("due_date") else ""
        html = _html_wrapper(
            f"New Action Item — {client_name}",
            f"<p><strong>{action['title']}</strong>{due}</p>"
            f"<p>Priority: {action.get('priority', 'normal').title()} | Owner: {action.get('owner', 'internal').title()}</p>",
            self._portal_url(slug),
        )
        await self._send_email(recipients, f"Action: {action['title']} — {client_name}", html)

    async def notify_sop_updated(self, slug: str, sop_title: str) -> None:
        recipients = self._get_recipients(slug)
        if not recipients:
            return
        client_name = self._store._client_name(slug)
        html = _html_wrapper(
            f"SOP Updated — {client_name}",
            f"<p><strong>{sop_title}</strong> has been updated.</p>",
            self._portal_url(slug),
        )
        await self._send_email(recipients, f"SOP Updated: {sop_title} — {client_name}", html)

    async def notify_comment(self, slug: str, update_title: str, comment_body: str, author: str) -> None:
        recipients = self._get_recipients(slug)
        if not recipients:
            return
        client_name = self._store._client_name(slug)
        preview = comment_body[:300]
        html = _html_wrapper(
            f"New Comment — {client_name}",
            f"<p><strong>{author}</strong> commented on <strong>{update_title}</strong></p>"
            f"<blockquote style='border-left:3px solid #2dd4bf;padding-left:12px;color:#cbd5e1;margin:12px 0;'>{preview}</blockquote>",
            self._portal_url(slug),
        )
        await self._send_email(recipients, f"Comment on {update_title} — {client_name}", html)
