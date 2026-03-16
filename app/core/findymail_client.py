"""Thin async Findymail API client — no class, just functions.

Proxies all 7 Findymail tools through httpx so the API key stays server-side.
"""

import logging

import httpx

logger = logging.getLogger("clay-webhook-os")


def _headers(api_key: str) -> dict:
    return {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
        "User-Agent": "clay-webhook-os/3.0",
    }


async def find_email(
    *,
    name: str | None = None,
    domain: str | None = None,
    linkedin_url: str | None = None,
    api_key: str,
    base_url: str = "https://app.findymail.com",
    timeout: int = 30,
) -> dict:
    """Find a verified B2B email via name+domain or LinkedIn URL."""
    payload: dict = {}
    if name:
        payload["name"] = name
    if domain:
        payload["domain"] = domain
    if linkedin_url:
        payload["linkedin_url"] = linkedin_url

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base_url}/api/search/name",
                headers=_headers(api_key),
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("[findymail] find_email failed: %s", e)
        return {"error": True, "error_message": str(e)}


async def find_phone(
    *,
    linkedin_url: str,
    api_key: str,
    base_url: str = "https://app.findymail.com",
    timeout: int = 30,
) -> dict:
    """Find phone number(s) via LinkedIn profile URL."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base_url}/api/search/phone",
                headers=_headers(api_key),
                json={"linkedin_url": linkedin_url},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("[findymail] find_phone failed: %s", e)
        return {"error": True, "error_message": str(e)}


async def verify_email(
    *,
    email: str,
    api_key: str,
    base_url: str = "https://app.findymail.com",
    timeout: int = 30,
) -> dict:
    """Verify if an email address is deliverable."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base_url}/api/verify",
                headers=_headers(api_key),
                json={"email": email},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("[findymail] verify_email failed: %s", e)
        return {"error": True, "error_message": str(e)}


async def reverse_email_lookup(
    *,
    email: str,
    with_profile: bool = False,
    api_key: str,
    base_url: str = "https://app.findymail.com",
    timeout: int = 30,
) -> dict:
    """Reverse lookup: get name, company, title from an email."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base_url}/api/search/reverse",
                headers=_headers(api_key),
                json={"email": email, "with_profile": with_profile},
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("[findymail] reverse_email_lookup failed: %s", e)
        return {"error": True, "error_message": str(e)}


async def enrich_company(
    *,
    domain: str | None = None,
    linkedin_url: str | None = None,
    name: str | None = None,
    api_key: str,
    base_url: str = "https://app.findymail.com",
    timeout: int = 30,
) -> dict:
    """Enrich company data via domain, LinkedIn URL, or name."""
    payload: dict = {}
    if domain:
        payload["domain"] = domain
    if linkedin_url:
        payload["linkedin_url"] = linkedin_url
    if name:
        payload["name"] = name

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base_url}/api/company/enrich",
                headers=_headers(api_key),
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("[findymail] enrich_company failed: %s", e)
        return {"error": True, "error_message": str(e)}


async def generate_lead_list(
    *,
    query: str,
    target_job_titles: list[str] | None = None,
    mode: str = "broad",
    find_contact: bool = True,
    find_email_flag: bool = True,
    find_phone_flag: bool = False,
    limit: int = 100,
    api_key: str,
    base_url: str = "https://app.findymail.com",
    timeout: int = 60,
) -> dict:
    """Generate a lead list from Findymail's 100M+ B2B database."""
    payload: dict = {
        "query": query,
        "mode": mode,
        "find_contact": find_contact,
        "find_email": find_email_flag,
        "find_phone": find_phone_flag,
        "limit": limit,
    }
    if target_job_titles:
        payload["target_job_titles"] = target_job_titles

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(
                f"{base_url}/api/leads/generate",
                headers=_headers(api_key),
                json=payload,
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("[findymail] generate_lead_list failed: %s", e)
        return {"error": True, "error_message": str(e)}


async def get_lead_list_results(
    *,
    hash_id: str,
    api_key: str,
    base_url: str = "https://app.findymail.com",
    timeout: int = 60,
) -> dict:
    """Retrieve results from a previously generated lead list."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(
                f"{base_url}/api/leads/results/{hash_id}",
                headers=_headers(api_key),
            )
            resp.raise_for_status()
            return resp.json()
    except Exception as e:
        logger.warning("[findymail] get_lead_list_results failed: %s", e)
        return {"error": True, "error_message": str(e)}
