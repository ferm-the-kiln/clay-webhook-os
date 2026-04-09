"""Serper enrichment for all 251 CW companies.

Runs 3 parallel Serper searches + knowledge graph per company.
Saves results to data/cw_serper_results.json for skill qualification.
"""

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

SERPER_KEY = "0ea2faeaa6ee6e52654c2c6633c7e9664dacc1e3"
CW_PATH = Path(__file__).resolve().parent.parent / "data" / "cw_companies.json"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "cw_serper_results.json"
MAX_CONCURRENT = 3
RETRY_BACKOFF = [2, 5, 10]  # seconds between retries


async def serper_search(query: str, sem: asyncio.Semaphore) -> list[dict]:
    for attempt, backoff in enumerate([0] + RETRY_BACKOFF):
        if backoff:
            await asyncio.sleep(backoff)
        async with sem:
            try:
                async with httpx.AsyncClient(
                    base_url="https://google.serper.dev",
                    headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
                    timeout=15,
                ) as client:
                    resp = await client.post("/search", json={"q": query, "num": 5})
                    if resp.status_code == 429:
                        if attempt < len(RETRY_BACKOFF):
                            continue
                    resp.raise_for_status()
                    return [
                        {"title": r.get("title", ""), "url": r.get("link", ""), "snippet": r.get("snippet", "")}
                        for r in resp.json().get("organic", [])[:5]
                    ]
            except Exception as e:
                if attempt == len(RETRY_BACKOFF):
                    print(f"    [warn] search failed after retries: {e}", file=sys.stderr)
                    return []
    return []


async def enrich_company(name: str, domain: str, sem: asyncio.Semaphore) -> dict:
    q1 = f"site:{domain} products OR hardware OR device OR sensor OR tracker" if domain else f'"{name}" products hardware device'
    q2 = f'"{name}" "GPS tracker" OR "fleet tracking" OR "IoT device" OR "SIM card" OR "cellular modem" OR telematics OR "LTE-M" OR "CAT-M1" OR "NB-IoT"'
    q3 = f'"{name}" deploys OR "fleet management" OR "device management" OR "connected devices" -blog -news -article'

    r1, r2, r3 = await asyncio.gather(
        serper_search(q1, sem), serper_search(q2, sem), serper_search(q3, sem),
    )

    # Knowledge graph
    kg = {}
    async with sem:
        try:
            async with httpx.AsyncClient(
                base_url="https://google.serper.dev",
                headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
                timeout=15,
            ) as client:
                resp = await client.post("/search", json={"q": f"{name} company", "num": 1})
                if resp.status_code == 200:
                    raw_kg = resp.json().get("knowledgeGraph", {})
                    if raw_kg:
                        kg = {
                            "title": raw_kg.get("title", ""),
                            "description": raw_kg.get("description", ""),
                            "type": raw_kg.get("type", ""),
                        }
        except Exception:
            pass

    # Build all_snippets text
    snippets = []
    for results, label in [(r1, "PRODUCT SEARCH"), (r2, "CONNECTIVITY SEARCH"), (r3, "DEPLOYMENT SEARCH")]:
        if results:
            snippets.append(f"--- {label} ---")
            for r in results:
                if r.get("snippet"):
                    snippets.append(f"[{r['title']}] {r['snippet']}")

    all_snippets = "\n".join(snippets)[:3000]
    has_results = bool(r1 or r2 or r3)

    return {
        "product_search": r1,
        "connectivity_search": r2,
        "deployment_search": r3,
        "knowledge_graph": kg,
        "all_snippets": all_snippets,
        "serper_had_results": has_results,
    }


async def main():
    with open(CW_PATH, "r") as f:
        companies = json.load(f)

    total = len(companies)
    print(f"Enriching {total} CW companies via Serper.dev...")
    print(f"  4 API calls per company = {total * 4} total calls")
    print(f"  Concurrency: {MAX_CONCURRENT}")
    print()

    sem = asyncio.Semaphore(MAX_CONCURRENT)
    results = []
    start_time = time.monotonic()

    batch_size = 10
    for batch_start in range(0, total, batch_size):
        batch = companies[batch_start:batch_start + batch_size]

        enrichments = await asyncio.gather(*[
            enrich_company(c["name"], c.get("domain", ""), sem)
            for c in batch
        ])

        for company, enrichment in zip(batch, enrichments):
            results.append({
                "company_name": company["name"],
                "domain": company.get("domain", ""),
                "research_context": enrichment,
                "evidence": enrichment["all_snippets"],
                "serper_had_results": enrichment["serper_had_results"],
            })

        done = batch_start + len(batch)
        elapsed = time.monotonic() - start_time
        rate = done / elapsed if elapsed > 0 else 0
        remaining = (total - done) / rate if rate > 0 else 0
        print(f"  [{done}/{total}] {elapsed:.0f}s elapsed, ~{remaining:.0f}s remaining")
        sys.stdout.flush()

    OUT_PATH.parent.mkdir(exist_ok=True)
    with open(OUT_PATH, "w") as f:
        json.dump(results, f, indent=2)

    elapsed = time.monotonic() - start_time
    has_results = sum(1 for r in results if r["serper_had_results"])
    print(f"\nDone in {elapsed:.0f}s.")
    print(f"Saved {len(results)} enriched companies to {OUT_PATH}")
    print(f"Serper had results for {has_results}/{len(results)} companies ({has_results/len(results)*100:.1f}%)")


if __name__ == "__main__":
    asyncio.run(main())
