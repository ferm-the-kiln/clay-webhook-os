"""Run Parallel Search + Apollo enrichment for a CSV of companies.

Usage:
    python scripts/run_enrichment.py <csv_path> [--concurrency N] [--parallel-only]

Reads CSV with columns: name/company_name + domain/company_domain
Outputs enrichment data to data/qualification_enrichment.json
"""

import asyncio
import csv
import json
import sys
import time
from pathlib import Path

import httpx

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.core.domain_analyzer import analyze_domain_signals
from app.core.research_fetcher import fetch_apollo_company, fetch_parallel_qualification

OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "qualification_enrichment.json"


def load_csv(path: str) -> list[dict]:
    """Load CSV and normalize column names."""
    companies = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            name = row.get("name") or row.get("company_name") or row.get("Name") or row.get("Company Name") or row.get("Company") or ""
            domain = row.get("domain") or row.get("company_domain") or row.get("Domain") or row.get("Website") or row.get("website") or ""
            # Clean domain (remove https://, www., trailing /)
            domain = domain.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")
            if name or domain:
                companies.append({"name": name.strip(), "domain": domain.strip()})
    return companies


async def enrich_company(
    name: str,
    domain: str,
    parallel_key: str,
    deepline_key: str,
    semaphore: asyncio.Semaphore,
) -> dict:
    """Run Parallel Search + Apollo + Domain Analysis for one company."""
    async with semaphore:
        start = time.monotonic()

        # Domain analysis (instant, no API)
        da = analyze_domain_signals(name, domain)

        # Parallel Search + Apollo in parallel
        tasks = []
        if parallel_key:
            tasks.append(fetch_parallel_qualification(name, domain, parallel_key))
        if deepline_key and domain:
            tasks.append(fetch_apollo_company(domain, deepline_key))

        results = await asyncio.gather(*tasks, return_exceptions=True)

        parallel_result = {}
        apollo_result = {}
        idx = 0
        if parallel_key:
            parallel_result = results[idx] if not isinstance(results[idx], Exception) else {}
            if isinstance(results[idx], Exception):
                print(f"    [warn] Parallel failed for {name}: {results[idx]}", file=sys.stderr)
            idx += 1
        if deepline_key and domain:
            apollo_result = results[idx] if not isinstance(results[idx], Exception) else {}
            if isinstance(results[idx], Exception):
                print(f"    [warn] Apollo failed for {name}: {results[idx]}", file=sys.stderr)

        duration_ms = int((time.monotonic() - start) * 1000)

        return {
            "company_name": name,
            "company_domain": domain,
            "all_snippets": parallel_result.get("all_snippets", ""),
            "parallel": parallel_result,
            "apollo_desc": apollo_result.get("description", "") or "",
            "apollo_industry": apollo_result.get("industry", "") or "",
            "apollo_keywords": apollo_result.get("keywords", []) or [],
            "domain_analysis": {
                "suggested_archetype": da.suggested_archetype,
                "is_hard_exclusion": da.is_hard_exclusion,
                "keyword_matches": da.keyword_matches,
                "reasoning": da.reasoning,
            },
            "duration_ms": duration_ms,
        }


async def main():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("csv_path", help="Path to CSV file")
    parser.add_argument("--concurrency", type=int, default=3)
    parser.add_argument("--limit", type=int, default=0)
    parser.add_argument("--output", type=str, default=str(OUT_PATH))
    args = parser.parse_args()

    companies = load_csv(args.csv_path)
    if args.limit:
        companies = companies[:args.limit]

    total = len(companies)
    parallel_key = settings.parallel_api_key
    deepline_key = settings.deepline_api_key

    print(f"Enriching {total} companies from {args.csv_path}")
    print(f"  Parallel: {'...'+parallel_key[-4:] if parallel_key else 'NOT SET'}")
    print(f"  Apollo/DeepLine: {'...'+deepline_key[-4:] if deepline_key else 'NOT SET'}")
    print(f"  Concurrency: {args.concurrency}")
    print(f"  Est. cost: ${total * 0.01:.2f} (Parallel) + $0.00 (Apollo)")
    print()

    semaphore = asyncio.Semaphore(args.concurrency)
    results = []
    start_time = time.monotonic()

    for i, c in enumerate(companies):
        result = await enrich_company(
            c["name"], c["domain"], parallel_key, deepline_key, semaphore,
        )
        results.append(result)

        has_parallel = "P" if result["all_snippets"] else "-"
        has_apollo = "A" if result["apollo_desc"] else "-"
        has_da = "D" if result["domain_analysis"]["suggested_archetype"] else "-"
        print(f"  [{i+1}/{total}] [{has_parallel}{has_apollo}{has_da}] {c['name']:40s} {result['duration_ms']}ms")

    total_time = int((time.monotonic() - start_time) * 1000)

    with_parallel = sum(1 for r in results if r["all_snippets"])
    with_apollo = sum(1 for r in results if r["apollo_desc"])

    print(f"\n{'='*60}")
    print(f"ENRICHMENT COMPLETE: {total} companies in {total_time/1000:.1f}s")
    print(f"  Parallel Search: {with_parallel}/{total} ({with_parallel/total*100:.0f}%)")
    print(f"  Apollo/LinkedIn: {with_apollo}/{total} ({with_apollo/total*100:.0f}%)")

    out_path = Path(args.output)
    with open(out_path, "w") as f:
        json.dump({"total": total, "results": results}, f, indent=2)
    print(f"  Saved to: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
