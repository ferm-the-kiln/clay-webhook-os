"""Portal store — manages SOPs, updates, media metadata per client.

Storage layout:
  clients/{slug}/portal.json              — portal metadata + GWS sync state
  clients/{slug}/sops/{id}.md             — individual SOP markdown files
  clients/{slug}/sops/acks.json           — SOP acknowledgments
  clients/{slug}/updates/updates.jsonl    — activity entries (append-only)
  clients/{slug}/updates/comments/{id}.jsonl — comments per update
  clients/{slug}/media/media.json         — media metadata list
  clients/{slug}/actions/actions.json     — action items
  clients/{slug}/views.jsonl              — portal view log
  data/portal/uploads/{slug}/             — actual uploaded files
"""

import hmac
import json
import logging
import mimetypes
import secrets
import time
import uuid
from datetime import datetime, timedelta
from pathlib import Path

from app.core.atomic_writer import atomic_write_json, atomic_write_text

logger = logging.getLogger("clay-webhook-os")


class PortalStore:
    """File-based portal store for client engagement hubs."""

    def __init__(self, clients_dir: str | Path = "clients", data_dir: str | Path = "data"):
        self._clients_dir = Path(clients_dir)
        self._uploads_dir = Path(data_dir) / "portal" / "uploads"

    # ── Helpers ───────────────────────────────────────────

    def _portal_dir(self, slug: str) -> Path:
        return self._clients_dir / slug

    def _ensure_dirs(self, slug: str) -> None:
        """Lazy-create portal subdirectories on first access."""
        base = self._portal_dir(slug)
        (base / "sops").mkdir(parents=True, exist_ok=True)
        (base / "updates").mkdir(parents=True, exist_ok=True)
        (base / "media").mkdir(parents=True, exist_ok=True)
        (base / "actions").mkdir(parents=True, exist_ok=True)
        (self._uploads_dir / slug).mkdir(parents=True, exist_ok=True)

    def _client_name(self, slug: str) -> str:
        """Extract client name from profile.md if it exists."""
        profile = self._portal_dir(slug) / "profile.md"
        if profile.exists():
            content = profile.read_text()
            for line in content.split("\n"):
                if line.startswith("# "):
                    return line[2:].strip()
        return slug.replace("-", " ").title()

    # ── Portal Metadata ───────────────────────────────────

    def _meta_path(self, slug: str) -> Path:
        return self._portal_dir(slug) / "portal.json"

    def get_meta(self, slug: str) -> dict:
        """Get or create portal metadata."""
        path = self._meta_path(slug)
        if path.exists():
            try:
                return json.loads(path.read_text())
            except (json.JSONDecodeError, OSError):
                pass
        now = time.time()
        meta = {
            "slug": slug,
            "status": "active",
            "notes": "",
            "gws_folder_id": None,
            "gws_doc_id": None,
            "last_synced_at": None,
            "slack_webhook_url": None,
            "created_at": now,
            "updated_at": now,
        }
        return meta

    def save_meta(self, slug: str, meta: dict) -> dict:
        self._ensure_dirs(slug)
        meta["updated_at"] = time.time()
        atomic_write_json(self._meta_path(slug), meta)
        return meta

    def update_meta(self, slug: str, updates: dict) -> dict:
        meta = self.get_meta(slug)
        for k, v in updates.items():
            if v is not None:
                meta[k] = v
        return self.save_meta(slug, meta)

    # ── Client Listing (overview cards) ───────────────────

    def list_portals(self) -> list[dict]:
        """List all client portals with overview stats."""
        portals = []
        if not self._clients_dir.exists():
            return portals

        for entry in sorted(self._clients_dir.iterdir()):
            if not entry.is_dir() or entry.name.startswith("_"):
                continue
            # Must have profile.md to be a real client
            if not (entry / "profile.md").exists():
                continue

            slug = entry.name
            meta = self.get_meta(slug)
            sops = self.list_sops(slug)
            updates = self._count_updates(slug)
            media = self.list_media(slug)
            actions = self.list_actions(slug)
            last_activity = self._last_activity(slug, updates)

            health = self.get_health_metrics(slug)
            portals.append({
                "slug": slug,
                "name": self._client_name(slug),
                "status": meta.get("status", "active"),
                "sop_count": len(sops),
                "update_count": updates,
                "media_count": len(media),
                "action_count": len(actions),
                "open_client_actions": sum(
                    1 for a in actions
                    if a.get("owner") == "client" and a.get("status") != "done"
                ),
                "last_activity": last_activity,
                "has_gws_sync": meta.get("gws_doc_id") is not None,
                **health,
            })

        return portals

    def _count_updates(self, slug: str) -> int:
        path = self._portal_dir(slug) / "updates" / "updates.jsonl"
        if not path.exists():
            return 0
        try:
            return sum(1 for line in path.read_text().splitlines() if line.strip())
        except OSError:
            return 0

    def _last_activity(self, slug: str, update_count: int) -> float | None:
        if update_count > 0:
            updates = self.list_updates(slug, limit=1)
            if updates:
                return updates[0].get("created_at")
        meta = self.get_meta(slug)
        return meta.get("updated_at")

    # ── SOPs ──────────────────────────────────────────────

    def list_sops(self, slug: str) -> list[dict]:
        sops_dir = self._portal_dir(slug) / "sops"
        if not sops_dir.exists():
            return []

        results = []
        for f in sorted(sops_dir.glob("*.md"), key=lambda p: p.stat().st_mtime, reverse=True):
            sop = self._read_sop(f)
            if sop:
                results.append(sop)
        return results

    def _read_sop(self, path: Path) -> dict | None:
        try:
            content = path.read_text()
        except OSError:
            return None

        # Parse YAML-ish frontmatter
        sop_id = path.stem
        title = sop_id.replace("-", " ").title()
        category = "general"
        body = content
        created_at = path.stat().st_mtime
        updated_at = created_at

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                body = parts[2].strip()
                for line in frontmatter.strip().split("\n"):
                    if line.startswith("title:"):
                        title = line.split(":", 1)[1].strip().strip('"').strip("'")
                    elif line.startswith("category:"):
                        category = line.split(":", 1)[1].strip()
                    elif line.startswith("created_at:"):
                        try:
                            created_at = float(line.split(":", 1)[1].strip())
                        except ValueError:
                            pass
                    elif line.startswith("updated_at:"):
                        try:
                            updated_at = float(line.split(":", 1)[1].strip())
                        except ValueError:
                            pass

        return {
            "id": sop_id,
            "title": title,
            "category": category,
            "content": body,
            "created_at": created_at,
            "updated_at": updated_at,
        }

    def create_sop(self, slug: str, title: str, category: str = "general", content: str = "") -> dict:
        self._ensure_dirs(slug)
        sop_id = f"sop_{uuid.uuid4().hex[:8]}"
        now = time.time()
        md = f"""---
title: {title}
category: {category}
created_at: {now}
updated_at: {now}
---

{content}"""
        path = self._portal_dir(slug) / "sops" / f"{sop_id}.md"
        atomic_write_text(path, md)
        logger.info("[portal] Created SOP '%s' for %s", title, slug)
        return {
            "id": sop_id,
            "title": title,
            "category": category,
            "content": content,
            "created_at": now,
            "updated_at": now,
        }

    def get_sop(self, slug: str, sop_id: str) -> dict | None:
        path = self._portal_dir(slug) / "sops" / f"{sop_id}.md"
        if not path.exists():
            return None
        return self._read_sop(path)

    def update_sop(self, slug: str, sop_id: str, updates: dict) -> dict | None:
        path = self._portal_dir(slug) / "sops" / f"{sop_id}.md"
        if not path.exists():
            return None

        sop = self._read_sop(path)
        if not sop:
            return None

        title = updates.get("title", sop["title"])
        category = updates.get("category", sop["category"])
        content = updates.get("content", sop["content"])
        now = time.time()

        md = f"""---
title: {title}
category: {category}
created_at: {sop['created_at']}
updated_at: {now}
---

{content}"""
        atomic_write_text(path, md)
        logger.info("[portal] Updated SOP '%s' for %s", sop_id, slug)
        return {
            "id": sop_id,
            "title": title,
            "category": category,
            "content": content,
            "created_at": sop["created_at"],
            "updated_at": now,
        }

    def delete_sop(self, slug: str, sop_id: str) -> bool:
        path = self._portal_dir(slug) / "sops" / f"{sop_id}.md"
        if not path.exists():
            return False
        path.unlink()
        logger.info("[portal] Deleted SOP '%s' for %s", sop_id, slug)
        return True

    # ── Updates (JSONL, append-only) ──────────────────────

    def list_updates(self, slug: str, limit: int = 50, offset: int = 0) -> list[dict]:
        path = self._portal_dir(slug) / "updates" / "updates.jsonl"
        if not path.exists():
            return []

        try:
            lines = [l for l in path.read_text().splitlines() if l.strip()]
        except OSError:
            return []

        # Reverse for most-recent-first
        lines.reverse()
        entries = []
        for line in lines[offset:offset + limit]:
            try:
                entries.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return entries

    def create_update(self, slug: str, type_: str, title: str, body: str = "", media_ids: list[str] | None = None) -> dict:
        self._ensure_dirs(slug)
        update_id = f"upd_{uuid.uuid4().hex[:8]}"
        now = time.time()
        entry = {
            "id": update_id,
            "type": type_,
            "title": title,
            "body": body,
            "pinned": False,
            "media_ids": media_ids or [],
            "created_at": now,
        }
        path = self._portal_dir(slug) / "updates" / "updates.jsonl"
        with open(path, "a") as f:
            f.write(json.dumps(entry) + "\n")
        logger.info("[portal] Created update '%s' for %s", title, slug)
        return entry

    def toggle_pin(self, slug: str, update_id: str) -> dict | None:
        path = self._portal_dir(slug) / "updates" / "updates.jsonl"
        if not path.exists():
            return None

        lines = path.read_text().splitlines()
        updated_entry = None
        new_lines = []
        for line in lines:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                new_lines.append(line)
                continue

            if entry.get("id") == update_id:
                entry["pinned"] = not entry.get("pinned", False)
                updated_entry = entry
            new_lines.append(json.dumps(entry))

        if updated_entry is None:
            return None

        atomic_write_text(path, "\n".join(new_lines) + "\n")
        return updated_entry

    def delete_update(self, slug: str, update_id: str) -> bool:
        path = self._portal_dir(slug) / "updates" / "updates.jsonl"
        if not path.exists():
            return False

        lines = path.read_text().splitlines()
        found = False
        new_lines = []
        for line in lines:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                new_lines.append(line)
                continue
            if entry.get("id") == update_id:
                found = True
                continue
            new_lines.append(json.dumps(entry))

        if not found:
            return False

        atomic_write_text(path, "\n".join(new_lines) + "\n" if new_lines else "")
        logger.info("[portal] Deleted update '%s' for %s", update_id, slug)
        return True

    # ── Media ─────────────────────────────────────────────

    def _media_meta_path(self, slug: str) -> Path:
        return self._portal_dir(slug) / "media" / "media.json"

    def _load_media(self, slug: str) -> list[dict]:
        path = self._media_meta_path(slug)
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return []

    def _save_media(self, slug: str, media_list: list[dict]) -> None:
        self._ensure_dirs(slug)
        atomic_write_json(self._media_meta_path(slug), media_list)

    def list_media(self, slug: str) -> list[dict]:
        return self._load_media(slug)

    def add_media(
        self,
        slug: str,
        original_name: str,
        file_bytes: bytes,
        caption: str = "",
    ) -> dict:
        self._ensure_dirs(slug)
        media_id = f"med_{uuid.uuid4().hex[:8]}"
        ext = Path(original_name).suffix or ".bin"
        filename = f"{media_id}{ext}"

        # Write file
        upload_path = self._uploads_dir / slug / filename
        upload_path.write_bytes(file_bytes)

        mime_type = mimetypes.guess_type(original_name)[0] or "application/octet-stream"
        now = time.time()

        entry = {
            "id": media_id,
            "filename": filename,
            "original_name": original_name,
            "mime_type": mime_type,
            "size_bytes": len(file_bytes),
            "caption": caption,
            "created_at": now,
        }

        media_list = self._load_media(slug)
        media_list.append(entry)
        self._save_media(slug, media_list)
        logger.info("[portal] Uploaded media '%s' for %s (%d bytes)", original_name, slug, len(file_bytes))
        return entry

    def get_media_path(self, slug: str, filename: str) -> Path | None:
        path = self._uploads_dir / slug / filename
        if path.exists():
            return path
        return None

    def delete_media(self, slug: str, media_id: str) -> bool:
        media_list = self._load_media(slug)
        found = None
        new_list = []
        for m in media_list:
            if m["id"] == media_id:
                found = m
            else:
                new_list.append(m)

        if not found:
            return False

        # Delete the file
        file_path = self._uploads_dir / slug / found["filename"]
        if file_path.exists():
            file_path.unlink()

        self._save_media(slug, new_list)
        logger.info("[portal] Deleted media '%s' for %s", media_id, slug)
        return True

    # ── Full Portal View ──────────────────────────────────

    def get_portal(self, slug: str) -> dict | None:
        """Get full portal data for a client."""
        client_dir = self._portal_dir(slug)
        if not client_dir.exists() or not (client_dir / "profile.md").exists():
            return None

        meta = self.get_meta(slug)
        sops = self.list_sops(slug)
        updates = self.list_updates(slug, limit=20)
        media = self.list_media(slug)
        actions = self.list_actions(slug)
        view_stats = self.get_view_stats(slug)
        sop_acks = self.get_sop_acks(slug)

        return {
            "slug": slug,
            "name": self._client_name(slug),
            "meta": meta,
            "sops": sops,
            "recent_updates": updates,
            "media": media,
            "actions": actions,
            "view_stats": view_stats,
            "sop_acks": sop_acks,
        }

    # ── Actions ────────────────────────────────────────────

    def _actions_path(self, slug: str) -> Path:
        return self._portal_dir(slug) / "actions" / "actions.json"

    def _load_actions(self, slug: str) -> list[dict]:
        path = self._actions_path(slug)
        if not path.exists():
            return []
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return []

    def _save_actions(self, slug: str, actions: list[dict]) -> None:
        self._ensure_dirs(slug)
        atomic_write_json(self._actions_path(slug), actions)

    def list_actions(self, slug: str) -> list[dict]:
        return self._load_actions(slug)

    def create_action(
        self,
        slug: str,
        title: str,
        description: str = "",
        owner: str = "internal",
        due_date: str | None = None,
        priority: str = "normal",
        recurrence: str | None = None,
    ) -> dict:
        self._ensure_dirs(slug)
        action_id = f"act_{uuid.uuid4().hex[:8]}"
        now = time.time()
        action = {
            "id": action_id,
            "title": title,
            "description": description,
            "owner": owner,
            "due_date": due_date,
            "status": "open",
            "priority": priority,
            "recurrence": recurrence,
            "created_at": now,
            "updated_at": now,
        }
        actions = self._load_actions(slug)
        actions.append(action)
        self._save_actions(slug, actions)
        logger.info("[portal] Created action '%s' for %s", title, slug)
        return action

    def get_action(self, slug: str, action_id: str) -> dict | None:
        for a in self._load_actions(slug):
            if a["id"] == action_id:
                return a
        return None

    def update_action(self, slug: str, action_id: str, updates: dict) -> dict | None:
        actions = self._load_actions(slug)
        for a in actions:
            if a["id"] == action_id:
                for k, v in updates.items():
                    if v is not None:
                        a[k] = v
                a["updated_at"] = time.time()
                self._save_actions(slug, actions)
                logger.info("[portal] Updated action '%s' for %s", action_id, slug)
                return a
        return None

    def toggle_action_complete(self, slug: str, action_id: str) -> dict | None:
        actions = self._load_actions(slug)
        for a in actions:
            if a["id"] == action_id:
                a["status"] = "open" if a.get("status") == "done" else "done"
                a["updated_at"] = time.time()

                # Auto-create next instance for recurring actions when marked done
                if a["status"] == "done" and a.get("recurrence") and a["recurrence"] != "none":
                    next_due = self._next_due_date(a.get("due_date"), a["recurrence"])
                    new_action = {
                        "id": f"act_{uuid.uuid4().hex[:8]}",
                        "title": a["title"],
                        "description": a.get("description", ""),
                        "owner": a.get("owner", "internal"),
                        "due_date": next_due,
                        "status": "open",
                        "priority": a.get("priority", "normal"),
                        "recurrence": a["recurrence"],
                        "created_at": time.time(),
                        "updated_at": time.time(),
                    }
                    actions.append(new_action)
                    logger.info("[portal] Auto-created recurring action '%s' due %s for %s", a["title"], next_due, slug)

                self._save_actions(slug, actions)
                logger.info("[portal] Toggled action '%s' to %s for %s", action_id, a["status"], slug)
                return a
        return None

    @staticmethod
    def _next_due_date(current_due: str | None, recurrence: str) -> str | None:
        """Calculate the next due date based on recurrence pattern."""
        if not current_due:
            base = datetime.now()
        else:
            try:
                base = datetime.strptime(current_due, "%Y-%m-%d")
            except ValueError:
                base = datetime.now()

        if recurrence == "weekly":
            next_date = base + timedelta(weeks=1)
        elif recurrence == "biweekly":
            next_date = base + timedelta(weeks=2)
        elif recurrence == "monthly":
            # Approximate: add 30 days
            next_date = base + timedelta(days=30)
        else:
            return current_due

        return next_date.strftime("%Y-%m-%d")

    def delete_action(self, slug: str, action_id: str) -> bool:
        actions = self._load_actions(slug)
        new_actions = [a for a in actions if a["id"] != action_id]
        if len(new_actions) == len(actions):
            return False
        self._save_actions(slug, new_actions)
        logger.info("[portal] Deleted action '%s' for %s", action_id, slug)
        return True

    # ── SOP Templates ─────────────────────────────────────

    def list_sop_templates(self) -> list[dict]:
        """List SOP templates from clients/_templates/sops/."""
        templates_dir = self._clients_dir / "_templates" / "sops"
        if not templates_dir.exists():
            return []
        results = []
        for f in sorted(templates_dir.glob("*.md")):
            sop = self._read_sop(f)
            if sop:
                sop["is_template"] = True
                results.append(sop)
        return results

    def clone_sop_template(self, template_id: str, slug: str, client_name: str) -> dict | None:
        """Clone a SOP template to a client, replacing {{client_name}}."""
        templates_dir = self._clients_dir / "_templates" / "sops"
        template_path = templates_dir / f"{template_id}.md"
        if not template_path.exists():
            return None
        sop = self._read_sop(template_path)
        if not sop:
            return None
        content = sop["content"].replace("{{client_name}}", client_name)
        title = sop["title"].replace("{{client_name}}", client_name)
        return self.create_sop(slug, title=title, category=sop["category"], content=content)

    # ── Onboarding ────────────────────────────────────────

    def onboard_client(self, slug: str, name: str) -> dict:
        """Full client setup: profile, portal.json, SOPs from templates."""
        profile_path = self._portal_dir(slug) / "profile.md"
        if profile_path.exists():
            raise ValueError(f"Client '{slug}' already exists")

        # Create directories
        self._ensure_dirs(slug)

        # Clone profile template
        template_profile = self._clients_dir / "_template" / "profile.md"
        if template_profile.exists():
            profile_content = template_profile.read_text().replace("{{Client Name}}", name)
        else:
            profile_content = f"# {name}\n\n## Company\n- **Domain:** —\n- **Industry:** —\n"
        atomic_write_text(profile_path, profile_content)

        # Create portal.json
        now = time.time()
        meta = {
            "slug": slug,
            "status": "onboarding",
            "notes": "",
            "gws_folder_id": None,
            "gws_doc_id": None,
            "last_synced_at": None,
            "share_token": None,
            "share_token_created_at": None,
            "created_at": now,
            "updated_at": now,
        }
        self.save_meta(slug, meta)

        # Clone all SOP templates
        templates = self.list_sop_templates()
        sop_ids = []
        for t in templates:
            sop = self.clone_sop_template(t["id"], slug, name)
            if sop:
                sop_ids.append(sop["id"])

        logger.info("[portal] Onboarded client '%s' (%s) with %d SOPs", name, slug, len(sop_ids))
        return {
            "slug": slug,
            "name": name,
            "status": "onboarding",
            "sops_created": len(sop_ids),
            "sop_ids": sop_ids,
        }

    # ── Comments ───────────────────────────────────────────

    def _comments_dir(self, slug: str) -> Path:
        return self._portal_dir(slug) / "updates" / "comments"

    def add_comment(self, slug: str, update_id: str, body: str, author: str) -> dict:
        """Append a comment to an update's JSONL file."""
        self._ensure_dirs(slug)
        comments_dir = self._comments_dir(slug)
        comments_dir.mkdir(parents=True, exist_ok=True)

        comment_id = f"cmt_{uuid.uuid4().hex[:8]}"
        now = time.time()
        comment = {
            "id": comment_id,
            "update_id": update_id,
            "body": body,
            "author": author,
            "created_at": now,
        }
        path = comments_dir / f"{update_id}.jsonl"
        with open(path, "a") as f:
            f.write(json.dumps(comment) + "\n")
        logger.info("[portal] Comment added to update '%s' by %s for %s", update_id, author, slug)
        return comment

    def list_comments(self, slug: str, update_id: str) -> list[dict]:
        """Read comments for an update, sorted chronologically."""
        path = self._comments_dir(slug) / f"{update_id}.jsonl"
        if not path.exists():
            return []
        try:
            lines = [l for l in path.read_text().splitlines() if l.strip()]
        except OSError:
            return []
        comments = []
        for line in lines:
            try:
                comments.append(json.loads(line))
            except json.JSONDecodeError:
                continue
        return sorted(comments, key=lambda c: c.get("created_at", 0))

    def delete_comment(self, slug: str, update_id: str, comment_id: str) -> bool:
        """Remove a comment from an update's JSONL file."""
        path = self._comments_dir(slug) / f"{update_id}.jsonl"
        if not path.exists():
            return False
        lines = path.read_text().splitlines()
        found = False
        new_lines = []
        for line in lines:
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                new_lines.append(line)
                continue
            if entry.get("id") == comment_id:
                found = True
                continue
            new_lines.append(json.dumps(entry))
        if not found:
            return False
        atomic_write_text(path, "\n".join(new_lines) + "\n" if new_lines else "")
        logger.info("[portal] Deleted comment '%s' from update '%s' for %s", comment_id, update_id, slug)
        return True

    def comment_count(self, slug: str, update_id: str) -> int:
        """Count comments for an update without loading them all."""
        path = self._comments_dir(slug) / f"{update_id}.jsonl"
        if not path.exists():
            return 0
        try:
            return sum(1 for line in path.read_text().splitlines() if line.strip())
        except OSError:
            return 0

    # ── View Tracking ─────────────────────────────────────

    def _views_path(self, slug: str) -> Path:
        return self._portal_dir(slug) / "views.jsonl"

    def record_view(self, slug: str, source: str = "dashboard") -> None:
        """Append a view event for the portal."""
        self._ensure_dirs(slug)
        entry = {"timestamp": time.time(), "source": source}
        path = self._views_path(slug)
        with open(path, "a") as f:
            f.write(json.dumps(entry) + "\n")

    def get_view_stats(self, slug: str) -> dict:
        """Return view statistics: last_viewed_at, 7d count, 30d count."""
        path = self._views_path(slug)
        if not path.exists():
            return {"last_viewed_at": None, "view_count_7d": 0, "view_count_30d": 0}

        try:
            lines = [l for l in path.read_text().splitlines() if l.strip()]
        except OSError:
            return {"last_viewed_at": None, "view_count_7d": 0, "view_count_30d": 0}

        now = time.time()
        seven_days_ago = now - 7 * 86400
        thirty_days_ago = now - 30 * 86400
        last_viewed = None
        count_7d = 0
        count_30d = 0

        for line in lines:
            try:
                entry = json.loads(line)
                ts = entry.get("timestamp", 0)
                if last_viewed is None or ts > last_viewed:
                    last_viewed = ts
                if ts >= seven_days_ago:
                    count_7d += 1
                if ts >= thirty_days_ago:
                    count_30d += 1
            except json.JSONDecodeError:
                continue

        return {
            "last_viewed_at": last_viewed,
            "view_count_7d": count_7d,
            "view_count_30d": count_30d,
        }

    # ── SOP Acknowledgment ────────────────────────────────

    def _acks_path(self, slug: str) -> Path:
        return self._portal_dir(slug) / "sops" / "acks.json"

    def acknowledge_sop(self, slug: str, sop_id: str, user: str) -> dict:
        """Record that a user acknowledged a SOP."""
        self._ensure_dirs(slug)
        acks = self._load_acks(slug)
        now = time.time()
        acks[sop_id] = {"acknowledged_at": now, "acknowledged_by": user}
        atomic_write_json(self._acks_path(slug), acks)
        logger.info("[portal] SOP '%s' acknowledged by %s for %s", sop_id, user, slug)
        return {"sop_id": sop_id, "acknowledged_at": now, "acknowledged_by": user}

    def get_sop_acks(self, slug: str) -> dict:
        """Return {sop_id: {acknowledged_at, acknowledged_by}}."""
        return self._load_acks(slug)

    def _load_acks(self, slug: str) -> dict:
        path = self._acks_path(slug)
        if not path.exists():
            return {}
        try:
            return json.loads(path.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    # ── Update Templates ──────────────────────────────────

    def list_update_templates(self) -> list[dict]:
        """List update templates from clients/_templates/updates/."""
        templates_dir = self._clients_dir / "_templates" / "updates"
        if not templates_dir.exists():
            return []
        results = []
        for f in sorted(templates_dir.glob("*.md")):
            template = self._read_update_template(f)
            if template:
                results.append(template)
        return results

    def get_update_template(self, template_id: str) -> dict | None:
        """Get a specific update template by ID."""
        templates_dir = self._clients_dir / "_templates" / "updates"
        path = templates_dir / f"{template_id}.md"
        if not path.exists():
            return None
        return self._read_update_template(path)

    def _read_update_template(self, path: Path) -> dict | None:
        """Parse an update template markdown file with frontmatter."""
        try:
            content = path.read_text()
        except OSError:
            return None

        template_id = path.stem
        title = template_id.replace("-", " ").title()
        type_ = "update"
        body = content

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                frontmatter = parts[1]
                body = parts[2].strip()
                for line in frontmatter.strip().split("\n"):
                    if line.startswith("title:"):
                        title = line.split(":", 1)[1].strip().strip('"').strip("'")
                    elif line.startswith("type:"):
                        type_ = line.split(":", 1)[1].strip()

        return {
            "id": template_id,
            "title": title,
            "type": type_,
            "body": body,
        }

    # ── Health Metrics ────────────────────────────────────

    def get_health_metrics(self, slug: str) -> dict:
        """Compute health metrics for a single client portal."""
        actions = self.list_actions(slug)
        today = datetime.now().strftime("%Y-%m-%d")
        overdue_count = sum(
            1 for a in actions
            if a.get("status") != "done" and a.get("due_date") and a["due_date"] < today
        )

        # Days since last update
        last_update_ts = None
        updates = self.list_updates(slug, limit=1)
        if updates:
            last_update_ts = updates[0].get("created_at")
        days_since = None
        if last_update_ts:
            days_since = int((time.time() - last_update_ts) / 86400)

        # View stats
        view_stats = self.get_view_stats(slug)

        # Unacked SOPs
        sops = self.list_sops(slug)
        acks = self.get_sop_acks(slug)
        unacked = sum(1 for s in sops if s["id"] not in acks)

        return {
            "overdue_action_count": overdue_count,
            "days_since_last_update": days_since,
            "last_viewed_at": view_stats["last_viewed_at"],
            "unacked_sop_count": unacked,
        }

    # ── Share Links ───────────────────────────────────────

    def create_share_token(self, slug: str) -> dict:
        """Generate a share token for client-facing read-only view."""
        token = secrets.token_urlsafe(32)
        now = time.time()
        meta = self.get_meta(slug)
        meta["share_token"] = token
        meta["share_token_created_at"] = now
        self.save_meta(slug, meta)
        logger.info("[portal] Created share token for %s", slug)
        return {"token": token, "created_at": now}

    def revoke_share_token(self, slug: str) -> bool:
        """Remove the share token."""
        meta = self.get_meta(slug)
        if not meta.get("share_token"):
            return False
        meta["share_token"] = None
        meta["share_token_created_at"] = None
        self.save_meta(slug, meta)
        logger.info("[portal] Revoked share token for %s", slug)
        return True

    def validate_share_token(self, slug: str, token: str) -> bool:
        """Timing-safe token comparison."""
        meta = self.get_meta(slug)
        stored = meta.get("share_token")
        if not stored or not token:
            return False
        return hmac.compare_digest(stored, token)

    def get_public_portal(self, slug: str) -> dict | None:
        """Stripped-down portal for public view (no media URLs, no edit metadata)."""
        client_dir = self._portal_dir(slug)
        if not client_dir.exists() or not (client_dir / "profile.md").exists():
            return None

        sops = self.list_sops(slug)
        updates = self.list_updates(slug, limit=20)
        actions = self.list_actions(slug)
        meta = self.get_meta(slug)

        return {
            "slug": slug,
            "name": self._client_name(slug),
            "status": meta.get("status", "active"),
            "sops": sops,
            "recent_updates": updates,
            "actions": actions,
        }
