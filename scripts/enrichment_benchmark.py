"""Enrichment waterfall benchmark against 251 closed-won companies.

Runs the full fetch_qualification_waterfall() for each company and tracks:
- Per-source hit rate (which sources return data)
- Overall accuracy (how many get qualified as Y)
- Source contribution (which sources found evidence others missed)

Usage:
    python scripts/enrichment_benchmark.py [--limit N] [--output PATH]
"""

import asyncio
import json
import sys
import time
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings  # noqa: E402
from app.core.research_fetcher import (  # noqa: E402
    fetch_qualification_waterfall,
    quick_qualify_check,
)

CW_PATH = Path(__file__).resolve().parent.parent / "data" / "cw_companies.json"
OUT_PATH = Path(__file__).resolve().parent.parent / "data" / "cw_waterfall_results.json"


def _normalize_company(raw: dict) -> dict:
    """Map CW data fields to webhook field names."""
    return {
        "company_name": raw.get("company_name") or raw.get("name", ""),
        "company_domain": raw.get("company_domain") or raw.get("domain", ""),
        "company_description": raw.get("company_description") or raw.get("description") or raw.get("leadiq_desc", ""),
        "notes": raw.get("notes", ""),
        "industry": raw.get("industry", ""),
    }


async def benchmark_company(
    company: dict,
    serper_key: str,
    tavily_key: str,
    parallel_key: str,
    semaphore: asyncio.Semaphore,
    skip_quick_qualify: bool = False,
) -> dict:
    """Run waterfall for a single company."""
    company = _normalize_company(company)
    name = company.get("company_name", "")
    domain = company.get("company_domain", "")

    async with semaphore:
        start = time.monotonic()

        # Check quick-qualify first (unless disabled)
        qq_verdict, qq_confidence = (None, 0.0)
        quick_qualified = False
        if not skip_quick_qualify:
            qq_verdict, qq_confidence = quick_qualify_check(company, name, domain)
            quick_qualified = qq_verdict is not None and qq_confidence >= 0.8

        waterfall_result = {}
        if not quick_qualified:
            try:
                waterfall_result = await fetch_qualification_waterfall(
                    company_name=name,
                    company_domain=domain,
                    serper_key=serper_key,
                    tavily_key=tavily_key,
                    parallel_key=parallel_key,
                )
            except Exception as e:
                print(f"  [error] {name}: {e}", file=sys.stderr)
                waterfall_result = {"error": str(e)}

        duration_ms = int((time.monotonic() - start) * 1000)

        return {
            "company_name": name,
            "company_domain": domain,
            "quick_qualified": quick_qualified,
            "quick_verdict": qq_verdict,
            "quick_confidence": qq_confidence,
            "source_coverage": waterfall_result.get("source_coverage", {}),
            "sources_with_data": waterfall_result.get("sources_with_data", 0),
            "domain_analysis": waterfall_result.get("domain_analysis", {}),
            "all_snippets_len": len(waterfall_result.get("all_snippets", "")),
            "all_snippets": waterfall_result.get("all_snippets", ""),
            "duration_ms": duration_ms,
        }


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Enrichment waterfall benchmark")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of companies (0=all)")
    parser.add_argument("--output", type=str, default=str(OUT_PATH), help="Output JSON path")
    parser.add_argument("--concurrency", type=int, default=3, help="Max concurrent waterfall runs")
    parser.add_argument("--parallel-only", action="store_true", help="Only use Parallel Search (no Serper/Tavily)")
    parser.add_argument("--no-quick-qualify", action="store_true", help="Skip quick-qualify — run waterfall on ALL companies")
    args = parser.parse_args()

    if not CW_PATH.exists():
        print(f"Error: {CW_PATH} not found. Need closed-won company data.", file=sys.stderr)
        sys.exit(1)

    serper_key = settings.serper_api_key
    tavily_key = settings.tavily_api_key
    parallel_key = settings.parallel_api_key
    if not parallel_key and not serper_key:
        print("Error: PARALLEL_API_KEY or SERPER_API_KEY must be set in .env", file=sys.stderr)
        sys.exit(1)

    with open(CW_PATH) as f:
        companies = json.load(f)

    if args.limit:
        companies = companies[:args.limit]

    total = len(companies)
    print(f"Benchmarking {total} companies (concurrency={args.concurrency})...")
    if args.parallel_only:
        serper_key = ""
        tavily_key = ""
        print("MODE: Parallel-only (no Serper/Tavily)")

    print(f"Parallel key: {'...'+parallel_key[-4:] if parallel_key else 'not set'}")
    print(f"Serper key: {'...'+serper_key[-4:] if serper_key else 'not set'}")
    print(f"Tavily key: {'...'+tavily_key[-4:] if tavily_key else 'not set'}")

    semaphore = asyncio.Semaphore(args.concurrency)
    results = []
    start_time = time.monotonic()

    for i, company in enumerate(companies):
        result = await benchmark_company(company, serper_key, tavily_key, parallel_key, semaphore, skip_quick_qualify=args.no_quick_qualify)
        results.append(result)

        name = company.get("company_name", "?")
        sources = result["sources_with_data"]
        qq = " (quick-qualified)" if result["quick_qualified"] else ""
        print(f"  [{i+1}/{total}] {name}: {sources} sources, {result['duration_ms']}ms{qq}")

    total_time = int((time.monotonic() - start_time) * 1000)

    # Compute stats
    quick_qualified_count = sum(1 for r in results if r["quick_qualified"])
    waterfall_count = total - quick_qualified_count

    source_hits = {
        "parallel": 0, "serper": 0, "tavily": 0, "homepage": 0,
        "domain_analysis": 0, "linkedin": 0, "job_postings": 0,
        "archetype_followup": 0,
    }
    for r in results:
        for source, hit in r.get("source_coverage", {}).items():
            if hit and source in source_hits:
                source_hits[source] += 1

    summary = {
        "total_companies": total,
        "quick_qualified": quick_qualified_count,
        "waterfall_run": waterfall_count,
        "total_duration_ms": total_time,
        "avg_duration_ms": total_time // total if total else 0,
        "source_hit_rates": {
            source: {
                "hits": count,
                "rate": round(count / waterfall_count * 100, 1) if waterfall_count else 0,
            }
            for source, count in source_hits.items()
        },
    }

    output = {"summary": summary, "results": results}

    out_path = Path(args.output)
    with open(out_path, "w") as f:
        json.dump(output, f, indent=2)

    print(f"\n{'='*60}")
    print(f"BENCHMARK COMPLETE: {total} companies in {total_time/1000:.1f}s")
    print(f"Quick-qualified: {quick_qualified_count}/{total} ({quick_qualified_count/total*100:.0f}%)")
    print(f"Waterfall runs:  {waterfall_count}/{total}")
    print(f"\nSource hit rates (of {waterfall_count} waterfall runs):")
    for source, stats in summary["source_hit_rates"].items():
        print(f"  {source:20s}: {stats['hits']:3d} ({stats['rate']:.1f}%)")
    print(f"\nResults saved to: {out_path}")


if __name__ == "__main__":
    asyncio.run(main())
