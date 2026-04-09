"""Retry Serper enrichment for companies that got rate-limited."""

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

SERPER_KEY = "0ea2faeaa6ee6e52654c2c6633c7e9664dacc1e3"
RETRY_PATH = Path(__file__).resolve().parent.parent / "data" / "cw_serper_retry.json"
MAIN_PATH = Path(__file__).resolve().parent.parent / "data" / "cw_serper_results.json"
MAX_CONCURRENT = 2  # Very conservative


async def serper_search(query: str, sem: asyncio.Semaphore) -> list[dict]:
    for attempt in range(4):
        if attempt > 0:
            await asyncio.sleep(3 * attempt)  # 3s, 6s, 9s backoff
        async with sem:
            try:
                async with httpx.AsyncClient(
                    base_url="https://google.serper.dev",
                    headers={"X-API-KEY": SERPER_KEY, "Content-Type": "application/json"},
                    timeout=15,
                ) as client:
                    resp = await client.post("/search", json={"q": query, "num": 5})
                    if resp.status_code == 429:
                        continue
                    resp.raise_for_status()
                    return [
                        {"title": r.get("title", ""), "url": r.get("link", ""), "snippet": r.get("snippet", "")}
                        for r in resp.json().get("organic", [])[:5]
                    ]
            except Exception as e:
                if attempt == 3:
                    print(f"    [fail] {e}", file=sys.stderr)
    return []


async def enrich_company(name: str, domain: str, sem: asyncio.Semaphore) -> dict:
    q1 = f"site:{domain} products OR hardware OR device OR sensor OR tracker" if domain else f'"{name}" products hardware device'
    q2 = f'"{name}" "GPS tracker" OR "fleet tracking" OR "IoT device" OR "SIM card" OR "cellular modem" OR telematics OR "LTE-M" OR "CAT-M1" OR "NB-IoT"'
    q3 = f'"{name}" deploys OR "fleet management" OR "device management" OR "connected devices" -blog -news -article'

    # Run searches sequentially to avoid rate limits
    r1 = await serper_search(q1, sem)
    await asyncio.sleep(1)
    r2 = await serper_search(q2, sem)
    await asyncio.sleep(1)
    r3 = await serper_search(q3, sem)
    await asyncio.sleep(1)

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
                        kg = {"title": raw_kg.get("title", ""), "description": raw_kg.get("description", ""), "type": raw_kg.get("type", "")}
        except Exception:
            pass

    snippets = []
    for results, label in [(r1, "PRODUCT SEARCH"), (r2, "CONNECTIVITY SEARCH"), (r3, "DEPLOYMENT SEARCH")]:
        if results:
            snippets.append(f"--- {label} ---")
            for r in results:
                if r.get("snippet"):
                    snippets.append(f"[{r['title']}] {r['snippet']}")

    all_snippets = "\n".join(snippets)[:3000]
    return {
        "product_search": r1, "connectivity_search": r2, "deployment_search": r3,
        "knowledge_graph": kg, "all_snippets": all_snippets,
        "serper_had_results": bool(r1 or r2 or r3),
    }


async def main():
    with open(RETRY_PATH) as f:
        retry_companies = json.load(f)

    with open(MAIN_PATH) as f:
        all_results = json.load(f)

    # Index main results by company name for updating
    result_map = {r["company_name"]: r for r in all_results}

    total = len(retry_companies)
    print(f"Retrying {total} companies (sequential, 2 concurrent max)...")

    sem = asyncio.Semaphore(MAX_CONCURRENT)
    start_time = time.monotonic()
    updated = 0

    for i, company in enumerate(retry_companies):
        name, domain = company["name"], company["domain"]
        enrichment = await enrich_company(name, domain, sem)

        if enrichment["serper_had_results"]:
            result_map[name] = {
                "company_name": name,
                "domain": domain,
                "research_context": enrichment,
                "evidence": enrichment["all_snippets"],
                "serper_had_results": True,
            }
            updated += 1

        elapsed = time.monotonic() - start_time
        print(f"  [{i+1}/{total}] {name}: {'OK' if enrichment['serper_had_results'] else 'NO DATA'} ({elapsed:.0f}s)")
        sys.stdout.flush()

    # Save updated results
    final = list(result_map.values())
    with open(MAIN_PATH, "w") as f:
        json.dump(final, f, indent=2)

    has_results = sum(1 for r in final if r["serper_had_results"])
    elapsed = time.monotonic() - start_time
    print(f"\nDone in {elapsed:.0f}s. Updated {updated} companies.")
    print(f"Total with Serper data: {has_results}/{len(final)} ({has_results/len(final)*100:.1f}%)")


if __name__ == "__main__":
    asyncio.run(main())
