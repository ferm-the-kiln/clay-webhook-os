"""Enrich Hologram companies from Clay CSV — name + domain only.

Usage:
    python scripts/hologram_enrich.py <csv_path> [--concurrency 3] [--limit N]

Extracts only Company Name + Company Domain from the CSV.
Stores EXCLUDE + FINAL Qualification as ground truth for accuracy measurement.
Outputs: data/hologram_enrichment.json
"""

import asyncio
import csv
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings
from app.core.domain_analyzer import analyze_domain_signals
from app.core.research_fetcher import fetch_apollo_company, fetch_parallel_qualification

OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "hologram_enrichment.json"


def load_csv(path: str) -> list[dict]:
    """Load CSV — extract name + domain + ground truth only."""
    companies = []
    with open(path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            name = row.get("Company Name", "").strip()
            domain = row.get("Company Domain", "").strip()
            domain = domain.replace("https://", "").replace("http://", "").replace("www.", "").rstrip("/")

            exclude = row.get("EXCLUDE", "").strip().lower() == "true"
            final_qual = row.get("FINAL Qualification", "").strip().lower() == "true"

            # Ground truth: Y if FINAL Qualification=true AND not excluded
            ground_truth_y = final_qual and not exclude

            if name or domain:
                companies.append({
                    "id": i + 1,
                    "name": name,
                    "domain": domain,
                    "ground_truth_y": ground_truth_y,
                    "clay_exclude": exclude,
                    "clay_final_qual": final_qual,
                })
    return companies


async def enrich_company(
    company: dict,
    parallel_key: str,
    deepline_key: str,
    semaphore: asyncio.Semaphore,
) -> dict:
    """Run Parallel Search + Apollo + Domain Analysis for one company."""
    name = company["name"]
    domain = company["domain"]

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
            "id": company["id"],
            "company_name": name,
            "company_domain": domain,
            "ground_truth_y": company["ground_truth_y"],
            "clay_exclude": company["clay_exclude"],
            "clay_final_qual": company["clay_final_qual"],
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
    args = parser.parse_args()

    companies = load_csv(args.csv_path)
    if args.limit:
        companies = companies[:args.limit]

    total = len(companies)
    ground_y = sum(1 for c in companies if c["ground_truth_y"])
    ground_n = total - ground_y

    parallel_key = settings.parallel_api_key
    deepline_key = settings.deepline_api_key

    print(f"Hologram Raw Qualification Benchmark")
    print(f"{'='*60}")
    print(f"  Companies: {total}")
    print(f"  Ground truth: {ground_y} Y / {ground_n} N")
    print(f"  Parallel: {'...'+parallel_key[-4:] if parallel_key else 'NOT SET'}")
    print(f"  Apollo/DeepLine: {'...'+deepline_key[-4:] if deepline_key else 'NOT SET'}")
    print(f"  Concurrency: {args.concurrency}")
    print(f"  Est. cost: ${total * 0.01:.2f} (Parallel) + $0.00 (Apollo)")
    print()

    semaphore = asyncio.Semaphore(args.concurrency)
    results = []
    start_time = time.monotonic()

    # Run all enrichments concurrently (bounded by semaphore)
    tasks = [
        enrich_company(c, parallel_key, deepline_key, semaphore)
        for c in companies
    ]

    for coro in asyncio.as_completed(tasks):
        result = await coro
        results.append(result)
        i = len(results)
        has_parallel = "P" if result["all_snippets"] else "-"
        has_apollo = "A" if result["apollo_desc"] else "-"
        has_da = "D" if result["domain_analysis"]["suggested_archetype"] else "-"
        gt = "Y" if result["ground_truth_y"] else "N"
        print(f"  [{i:3d}/{total}] [{has_parallel}{has_apollo}{has_da}] [{gt}] {result['company_name']:40s} {result['duration_ms']}ms")

    # Sort by original ID
    results.sort(key=lambda r: r["id"])

    total_time = int((time.monotonic() - start_time) * 1000)

    with_parallel = sum(1 for r in results if r["all_snippets"])
    with_apollo = sum(1 for r in results if r["apollo_desc"])
    with_da = sum(1 for r in results if r["domain_analysis"]["suggested_archetype"])

    print(f"\n{'='*60}")
    print(f"ENRICHMENT COMPLETE: {total} companies in {total_time/1000:.1f}s")
    print(f"  Parallel Search: {with_parallel}/{total} ({with_parallel/total*100:.0f}%)")
    print(f"  Apollo/LinkedIn: {with_apollo}/{total} ({with_apollo/total*100:.0f}%)")
    print(f"  Domain Analysis: {with_da}/{total} ({with_da/total*100:.0f}%)")

    with open(OUT_PATH, "w") as f:
        json.dump({"total": total, "results": results}, f, indent=2)
    print(f"  Saved to: {OUT_PATH}")


if __name__ == "__main__":
    asyncio.run(main())
