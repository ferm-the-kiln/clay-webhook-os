"""Portal doc sync — creates Google Docs for portal posts.

Fire-and-forget: triggered async after post creation. Creates a Google Doc
per post, organized into sub-folders by post type under each client folder.

Folder structure:
  Google Drive / Client Portals / {Client Name} / Deliverables/
                                                 / Updates/
                                                 / Milestones/
                                                 / Notes/
"""

import logging

from app.core.portal_store import PortalStore
from app.core.sheets_client import SheetsClient

logger = logging.getLogger("clay-webhook-os")

# Map post type → subfolder name
TYPE_FOLDERS: dict[str, str] = {
    "deliverable": "Deliverables",
    "update": "Updates",
    "milestone": "Milestones",
    "note": "Notes",
}


class PortalDocSync:
    """Creates Google Docs for portal posts, organized per client."""

    def __init__(self, sheets_client: SheetsClient, portal_store: PortalStore) -> None:
        self.sheets_client = sheets_client
        self.portal_store = portal_store
        self._root_id: str | None = None
        self._client_folder_cache: dict[str, str] = {}  # slug → client folder ID
        self._type_folder_cache: dict[str, str] = {}    # "slug/type" → type subfolder ID
        self._shared_clients: set[str] = set()           # slugs already shared this runtime

    @property
    def available(self) -> bool:
        return self.sheets_client.available

    async def _ensure_root(self) -> str:
        """Find or create 'Client Portals' root folder in Drive."""
        if self._root_id:
            return self._root_id
        folder_id = await self.sheets_client.find_folder("Client Portals")
        if folder_id:
            self._root_id = folder_id
            return folder_id
        self._root_id = await self.sheets_client.create_folder("Client Portals")
        return self._root_id

    async def _ensure_client_folder(self, slug: str) -> str:
        """Ensure Client Portals / {Client Name} folder exists."""
        if slug in self._client_folder_cache:
            return self._client_folder_cache[slug]

        root_id = await self._ensure_root()
        meta = self.portal_store.get_meta(slug)
        client_name = self.portal_store._client_name(slug)

        # Reuse gws_folder_id from portal.json if already set
        client_folder_id = meta.get("gws_folder_id")
        if not client_folder_id:
            client_folder_id = await self.sheets_client.ensure_subfolder(root_id, client_name)
            self.portal_store.update_meta(slug, {"gws_folder_id": client_folder_id})

        self._client_folder_cache[slug] = client_folder_id
        return client_folder_id

    async def _ensure_type_folder(self, slug: str, post_type: str) -> str:
        """Ensure type subfolder exists under client folder."""
        cache_key = f"{slug}/{post_type}"
        if cache_key in self._type_folder_cache:
            return self._type_folder_cache[cache_key]

        client_folder_id = await self._ensure_client_folder(slug)
        folder_name = TYPE_FOLDERS.get(post_type, "Updates")
        type_folder_id = await self.sheets_client.ensure_subfolder(client_folder_id, folder_name)
        self._type_folder_cache[cache_key] = type_folder_id
        return type_folder_id

    async def _share_client_folder(self, slug: str) -> None:
        """Share client folder with notification_emails (once per runtime)."""
        if slug in self._shared_clients:
            return

        meta = self.portal_store.get_meta(slug)
        emails = meta.get("notification_emails", [])
        if not emails:
            self._shared_clients.add(slug)
            return

        client_folder_id = await self._ensure_client_folder(slug)
        for email in emails:
            try:
                await self.sheets_client.share_file(client_folder_id, email)
                logger.info("[portal_doc_sync] Shared folder with %s for %s", email, slug)
            except RuntimeError as e:
                logger.warning("[portal_doc_sync] Failed to share with %s: %s", email, e)

        self._shared_clients.add(slug)

    async def sync_post(self, slug: str, update: dict) -> dict | None:
        """Create a Google Doc for a portal post and store the URL back.

        Args:
            slug: Client slug
            update: The update dict (must have id, type, title, body)

        Returns:
            {"doc_id": "...", "url": "..."} on success, None on failure
        """
        if not self.available:
            return None

        update_id = update["id"]
        post_type = update.get("type", "update")
        title = update.get("title", "Untitled")
        body = update.get("body", "")

        try:
            # 1. Ensure folder structure
            type_folder_id = await self._ensure_type_folder(slug, post_type)

            # 2. Create Google Doc
            doc_id = await self.sheets_client.create_document(title)

            # 3. Write body content
            if body:
                await self.sheets_client.write_document_text(doc_id, body)

            # 4. Move doc into type subfolder
            await self.sheets_client.move_file_to_folder(doc_id, type_folder_id)

            # 5. Share client folder (idempotent, first-time only per runtime)
            await self._share_client_folder(slug)

            # 6. Store doc URL back on the update entry
            doc_url = SheetsClient.get_document_url(doc_id)
            self.portal_store.update_entry_field(slug, update_id, "google_doc_url", doc_url)

            logger.info("[portal_doc_sync] Created doc for %s/%s → %s", slug, update_id, doc_url)
            return {"doc_id": doc_id, "url": doc_url}

        except Exception as e:
            logger.error("[portal_doc_sync] Failed to sync post %s/%s: %s", slug, update_id, e)
            return None
