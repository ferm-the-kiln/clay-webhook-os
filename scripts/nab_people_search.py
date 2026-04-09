"""NAB Show People Search — find senior tech/AI/engineering leaders at media companies.

Two-step DeepLine/Apollo pipeline:
  1. apollo_enrich_company → get Apollo org ID from domain
  2. apollo_search_people  → search people by org ID + seniority filters

Usage:
    /opt/homebrew/bin/python3.11 scripts/nab_people_search.py <csv_path> [--concurrency 5] [--limit N] [--resume]

Output: data/nab_people_search_results.csv

Use --resume to skip companies already in the output CSV (saves credits after partial runs).
"""

import asyncio
import csv
import re
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings

OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "nab_people_search_results.csv"

# ── Title filtering (from Clay People Search config) ────────────────

TITLE_INCLUDE_KEYWORDS = [
    # Original Clay config keywords
    "chief technology officer", "chief innovation officer",
    "cio", "cto", "ai", "ai engineering",
    "machine learning engineer", "ml", "mle", "engineering",
    # Broader tech keywords for media companies
    "technology", "technical", "data", "software",
    "infrastructure", "platform", "systems",
    "innovation", "information technology",
    "product", "it",
]

TITLE_EXCLUDE_KEYWORDS = [
    "assistant", "secretary", "advocate", "digital",
    "security", "operations", "cluster", "recruiting",
    "recruiter", "associate", "people", "alexa",
    # Additional noise for media companies
    "sales", "marketing", "creative director",
    "art director", "photography", "photographer",
    "producer", "production designer", "casting",
    "costume", "makeup", "hair", "music",
    "accounting", "finance", "legal", "counsel",
    "hr", "human resources", "talent acquisition",
    "communications", "public relations",
]

# Pre-compile word-boundary regex patterns for each keyword
_INCLUDE_PATTERNS = [re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE) for kw in TITLE_INCLUDE_KEYWORDS]
_EXCLUDE_PATTERNS = [re.compile(r"\b" + re.escape(kw) + r"\b", re.IGNORECASE) for kw in TITLE_EXCLUDE_KEYWORDS]

LIMIT_PER_COMPANY = 15


def clean_domain(raw: str) -> str:
    """Strip protocol, www, trailing slash from a domain."""
    d = raw.strip()
    for prefix in ("https://", "http://", "www."):
        if d.lower().startswith(prefix):
            d = d[len(prefix):]
    return d.rstrip("/")


def load_csv(path: str) -> list[dict]:
    """Load NAB CSV — extract company name, domain, and LinkedIn URL."""
    companies = []
    seen_domains = set()

    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            name = row.get("COMPANY", "").strip()

            # Prefer enriched Website column, fallback to raw domain
            domain = clean_domain(
                row.get("Website", "")
                or row.get("Linked In & Website UR Ls website Domain Url", "")
            )
            linkedin_url = row.get("Linked In & Website UR Ls linkedin Company Url", "").strip()

            if not domain:
                continue

            # Dedupe by domain
            if domain in seen_domains:
                continue
            seen_domains.add(domain)

            companies.append({
                "id": i + 1,
                "name": name or domain,
                "domain": domain,
                "linkedin_url": linkedin_url,
            })

    return companies


def title_passes_filter(title: str) -> bool:
    """Check if a title matches the include/exclude keyword filters (word-boundary)."""
    # Must match at least one include keyword (whole word)
    if not any(pat.search(title) for pat in _INCLUDE_PATTERNS):
        return False

    # Must not match any exclude keyword (whole word)
    if any(pat.search(title) for pat in _EXCLUDE_PATTERNS):
        return False

    return True


async def get_apollo_org_id(
    domain: str,
    deepline_key: str,
    client: httpx.AsyncClient,
) -> str | None:
    """Step 1: Get Apollo org ID from company domain."""
    try:
        resp = await client.post(
            "/api/v2/integrations/execute",
            json={
                "provider": "apollo",
                "operation": "apollo_enrich_company",
                "payload": {"domain": domain},
            },
        )
        resp.raise_for_status()
        org = resp.json().get("result", {}).get("data", {}).get("organization", {})
        return org.get("id")
    except Exception as e:
        print(f"    [warn] Org lookup failed for {domain}: {e}", file=sys.stderr)
        return None


async def search_people_at_org(
    org_id: str,
    client: httpx.AsyncClient,
    max_pages: int = 3,
) -> list[dict]:
    """Step 2: Search for senior people at an Apollo org ID (paginated)."""
    all_people: list[dict] = []

    for page in range(1, max_pages + 1):
        try:
            resp = await client.post(
                "/api/v2/integrations/execute",
                json={
                    "provider": "apollo",
                    "operation": "apollo_search_people",
                    "payload": {
                        "organization_ids": [org_id],
                        "person_seniorities": ["c_suite", "vp", "director", "owner", "manager"],
                        "per_page": 50,
                        "page": page,
                    },
                },
            )
            resp.raise_for_status()
            data = resp.json().get("result", {}).get("data", {})
            people = data.get("people", [])
            all_people.extend(people)

            # Stop if fewer than 50 results (no more pages)
            if len(people) < 50:
                break
        except Exception as e:
            print(f"    [warn] People search page {page} failed for org {org_id}: {e}", file=sys.stderr)
            break

    return all_people


async def search_org_by_name(
    name: str,
    client: httpx.AsyncClient,
) -> str | None:
    """Fallback: search Apollo for org ID by company name."""
    try:
        resp = await client.post(
            "/api/v2/integrations/execute",
            json={
                "provider": "apollo",
                "operation": "apollo_search_people",
                "payload": {
                    "q_keywords": name,
                    "person_seniorities": ["c_suite"],
                    "per_page": 1,
                },
            },
        )
        resp.raise_for_status()
        people = resp.json().get("result", {}).get("data", {}).get("people", [])
        if people:
            org = people[0].get("organization", {})
            org_name = org.get("name", "").lower()
            # Verify it's the right company (fuzzy match)
            if any(word in org_name for word in name.lower().split()[:2]):
                return people[0].get("organization_id") or None
    except Exception:
        pass
    return None


async def process_company(
    company: dict,
    deepline_key: str,
    client: httpx.AsyncClient,
    semaphore: asyncio.Semaphore,
) -> tuple[list[dict], int]:
    """Full pipeline for one company: org ID → people search → filter.

    Returns (filtered_people, raw_count).
    """
    async with semaphore:
        # Step 1: Get org ID (try domain first, fallback to name search)
        org_id = await get_apollo_org_id(company["domain"], deepline_key, client)
        if not org_id:
            org_id = await search_org_by_name(company["name"], client)
        if not org_id:
            return [], 0

        # Step 2: Search people
        raw_people = await search_people_at_org(org_id, client)

        # Step 3: Filter by title keywords
        filtered = []
        for p in raw_people:
            title = p.get("title", "")
            if title_passes_filter(title):
                filtered.append({
                    "company_name": company["name"],
                    "company_domain": company["domain"],
                    "company_linkedin_url": company["linkedin_url"],
                    "person_first_name": p.get("first_name", ""),
                    "person_last_name": p.get("last_name_obfuscated", ""),
                    "person_title": title,
                    "apollo_person_id": p.get("id", ""),
                    "has_email": p.get("has_email", False),
                })

        # Cap at LIMIT_PER_COMPANY
        filtered = filtered[:LIMIT_PER_COMPANY]

        return filtered, len(raw_people)


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="NAB Show People Search via DeepLine/Apollo")
    parser.add_argument("csv_path", help="Path to NAB attendees CSV")
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--limit", type=int, default=0, help="Process only first N companies")
    parser.add_argument("--resume", action="store_true", help="Skip companies already in output CSV")
    args = parser.parse_args()

    companies = load_csv(args.csv_path)
    if args.limit:
        companies = companies[: args.limit]

    # Resume: load existing results and skip already-processed domains
    existing_people: list[dict] = []
    already_done: set[str] = set()
    if args.resume and OUT_PATH.exists():
        with open(OUT_PATH, newline="") as f:
            existing_people = list(csv.DictReader(f))
        already_done = {r["company_domain"] for r in existing_people}
        before = len(companies)
        companies = [c for c in companies if c["domain"] not in already_done]
        print(f"  Resuming: {before - len(companies)} companies already done, {len(companies)} remaining")
        print(f"  Existing results: {len(existing_people)} people")
        print()

    total = len(companies)
    deepline_key = settings.deepline_api_key

    print(f"NAB Show People Search")
    print(f"{'=' * 60}")
    print(f"  Companies to process: {total}")
    print(f"  DeepLine key: {'...' + deepline_key[-4:] if deepline_key else 'NOT SET'}")
    print(f"  Concurrency: {args.concurrency}")
    print(f"  Title filter: {len(TITLE_INCLUDE_KEYWORDS)} include / {len(TITLE_EXCLUDE_KEYWORDS)} exclude keywords")
    print(f"  Per-company cap: {LIMIT_PER_COMPANY}")
    print(f"  Est. API calls: ~{total * 2}")
    print()

    if not deepline_key:
        print("ERROR: DEEPLINE_API_KEY not set in .env", file=sys.stderr)
        sys.exit(1)

    if total == 0:
        print("Nothing to process.")
        return

    semaphore = asyncio.Semaphore(args.concurrency)
    all_people: list[dict] = list(existing_people)
    companies_with_results = 0
    companies_processed = 0
    total_raw = 0
    start_time = time.monotonic()

    async with httpx.AsyncClient(
        base_url=settings.deepline_base_url.rstrip("/"),
        headers={
            "Authorization": f"Bearer {deepline_key}",
            "Content-Type": "application/json",
            "User-Agent": "clay-webhook-os/3.0",
        },
        timeout=60,
    ) as client:
        tasks = [
            process_company(c, deepline_key, client, semaphore)
            for c in companies
        ]

        for coro in asyncio.as_completed(tasks):
            people, raw_count = await coro
            companies_processed += 1
            total_raw += raw_count
            if people:
                companies_with_results += 1
                all_people.extend(people)
                company_name = people[0]["company_name"]
                print(
                    f"  [{companies_processed:3d}/{total}] {company_name:40s} → {len(people)}/{raw_count} matched"
                )
            else:
                label = f"(0/{raw_count} matched)" if raw_count else "(no org found)"
                print(f"  [{companies_processed:3d}/{total}] {label:40s}")

    total_time = int((time.monotonic() - start_time) * 1000)

    # Write CSV
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    fieldnames = [
        "company_name", "company_domain", "company_linkedin_url",
        "person_first_name", "person_last_name", "person_title",
        "apollo_person_id", "has_email",
    ]
    with open(OUT_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(all_people)

    print(f"\n{'=' * 60}")
    print(f"COMPLETE: {total} companies in {total_time / 1000:.1f}s")
    print(f"  Companies with results: {companies_with_results}/{total}")
    print(f"  Raw senior people found: {total_raw}")
    print(f"  After title filter: {len(all_people)}")
    print(f"  Saved to: {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
