"""Scrape company websites via ScraperAPI for all 251 CW companies.

Fetches homepage + /products + /about for each company.
Strips HTML to clean text. Saves alongside existing Parallel Search data.

Usage:
    python scripts/scrape_benchmark.py [--limit N] [--concurrency N]
"""

import asyncio
import json
import re
import sys
import time
from pathlib import Path

import httpx

SCRAPERAPI_KEY = "f5b31a4cf0174006bc784ef2acad5b58"
SCRAPERAPI_URL = "http://api.scraperapi.com"

CW_PATH = Path(__file__).resolve().parent.parent / "data" / "cw_companies.json"
WATERFALL_PATH = Path(__file__).resolve().parent.parent / "data" / "cw_waterfall_results.json"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "cw_scraped_results.json"


def _strip_html(html: str) -> str:
    """Strip HTML tags and collapse whitespace."""
    text = re.sub(r"<script[^>]*>.*?</script>", " ", html, flags=re.DOTALL)
    text = re.sub(r"<style[^>]*>.*?</style>", " ", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text[:3000]


async def scrape_page(url: str, client: httpx.AsyncClient) -> str:
    """Scrape a single page via ScraperAPI."""
    try:
        resp = await client.get(
            SCRAPERAPI_URL,
            params={"api_key": SCRAPERAPI_KEY, "url": url},
            timeout=30,
        )
        if resp.status_code < 400:
            return _strip_html(resp.text)
    except Exception as e:
        print(f"    [warn] {url}: {e}", file=sys.stderr)
    return ""


async def scrape_company(
    name: str,
    domain: str,
    semaphore: asyncio.Semaphore,
    client: httpx.AsyncClient,
) -> dict:
    """Scrape 3 pages for a company."""
    if not domain:
        return {"homepage": "", "products": "", "about": "", "combined": "", "duration_ms": 0, "pages_found": 0}

    async with semaphore:
        start = time.monotonic()
        urls = [
            f"https://{domain}",
            f"https://{domain}/products",
            f"https://{domain}/about",
        ]

        homepage, products, about = await asyncio.gather(
            scrape_page(urls[0], client),
            scrape_page(urls[1], client),
            scrape_page(urls[2], client),
        )

        duration_ms = int((time.monotonic() - start) * 1000)

        # Combine into a readable summary
        parts = []
        if homepage:
            parts.append(f"[Homepage] {homepage[:1000]}")
        if products:
            parts.append(f"[Products] {products[:1000]}")
        if about:
            parts.append(f"[About] {about[:1000]}")

        return {
            "homepage": homepage[:1500],
            "products": products[:1500],
            "about": about[:1500],
            "combined": "\n".join(parts)[:3000],
            "duration_ms": duration_ms,
            "pages_found": sum(1 for p in [homepage, products, about] if p),
        }


async def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--concurrency", type=int, default=5)
    args = parser.parse_args()

    with open(CW_PATH) as f:
        companies = json.load(f)

    if args.limit:
        companies = companies[:args.limit]

    total = len(companies)
    print(f"Scraping {total} companies via ScraperAPI (concurrency={args.concurrency})...")
    print(f"3 pages each = {total * 3} requests (you have 5000 credits)\n")

    semaphore = asyncio.Semaphore(args.concurrency)
    results = []
    start_time = time.monotonic()

    async with httpx.AsyncClient() as client:
        for i, c in enumerate(companies):
            name = c.get("name", "")
            domain = c.get("domain", "")

            result = await scrape_company(name, domain, semaphore, client)
            result["company_name"] = name
            result["company_domain"] = domain
            results.append(result)

            pages = result["pages_found"]
            ms = result["duration_ms"]
            print(f"  [{i+1}/{total}] {name:40s} {pages}/3 pages  {ms}ms")

    total_time = int((time.monotonic() - start_time) * 1000)

    # Stats
    companies_with_content = sum(1 for r in results if r["pages_found"] > 0)
    total_pages = sum(r["pages_found"] for r in results)

    print(f"\n{'='*60}")
    print(f"SCRAPE COMPLETE: {total} companies in {total_time/1000:.1f}s")
    print(f"Companies with content: {companies_with_content}/{total} ({companies_with_content/total*100:.0f}%)")
    print(f"Total pages scraped: {total_pages}/{total*3}")
    print(f"Credits used: ~{total_pages}")

    with open(OUT_PATH, "w") as f:
        json.dump({"results": results}, f, indent=2)
    print(f"Saved to {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
