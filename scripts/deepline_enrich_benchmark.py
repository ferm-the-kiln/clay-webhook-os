"""Enrich all 251 CW companies via DeepLine company API to get LinkedIn descriptions.

Usage:
    python scripts/deepline_enrich_benchmark.py [--limit N] [--concurrency N]
"""

import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

DEEPLINE_KEY = "dlp_1d449202c572919b1b2c8cfbca533bd1f5c98ce87f1d1b72"
DEEPLINE_URL = "https://code.deepline.com"

CW_PATH = Path(__file__).resolve().parent.parent / "data" / "cw_companies.json"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "cw_deepline_results.json"


async def enrich_company(domain: str, semaphore: asyncio.Semaphore) -> dict:
    if not domain:
        return {}

    async with semaphore:
        try:
            async with httpx.AsyncClient(
                base_url=DEEPLINE_URL,
                headers={"Authorization": f"Bearer {DEEPLINE_KEY}", "Content-Type": "application/json"},
                timeout=30,
            ) as client:
                resp = await client.post(
                    "/api/v2/integrations/execute",
                    json={
                        "provider": "deepline_native",
                        "operation": "deepline_native_enrich_company",
                        "payload": {"domain": domain},
                    },
                )
                data = resp.json()
                company = data.get("result", {}).get("data", {}).get("output", {}).get("company", {})
                return {
                    "description": company.get("description", ""),
                    "industry": company.get("industry", ""),
                    "size": company.get("size", ""),
                    "employees_count": company.get("employees_count", 0),
                    "name": company.get("name", ""),
                    "founded": company.get("founded"),
                    "linkedin_url": company.get("linkedin_url", ""),
                    "type": company.get("type", ""),
                    "technologies": company.get("technologies", []),
                }
        except Exception as e:
            print(f"    [warn] {domain}: {e}", file=sys.stderr)
            return {}


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
    print(f"Enriching {total} companies via DeepLine (concurrency={args.concurrency})...\n")

    semaphore = asyncio.Semaphore(args.concurrency)
    results = []
    start_time = time.monotonic()

    for i, c in enumerate(companies):
        name = c.get("name", "")
        domain = c.get("domain", "")

        result = await enrich_company(domain, semaphore)
        result["company_name"] = name
        result["company_domain"] = domain
        results.append(result)

        desc = result.get("description", "")[:80]
        industry = result.get("industry", "")
        found = "Y" if desc else "N"
        print(f"  [{i+1}/{total}] [{found}] {name:35s} {industry[:30]:30s} {desc}")

    total_time = int((time.monotonic() - start_time) * 1000)
    has_desc = sum(1 for r in results if r.get("description"))

    print(f"\n{'='*60}")
    print(f"DEEPLINE ENRICHMENT COMPLETE: {total} companies in {total_time/1000:.1f}s")
    print(f"Companies with LinkedIn description: {has_desc}/{total} ({has_desc/total*100:.0f}%)")

    with open(OUT_PATH, "w") as f:
        json.dump({"results": results}, f, indent=2)
    print(f"Saved to {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
