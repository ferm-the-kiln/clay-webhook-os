#!/usr/bin/env python3
"""Test harness for the signal-researcher skill.

Calls the webhook for 20 companies and saves results for review.
Runs requests in parallel (default 5 concurrent) for speed.

Usage:
    python scripts/test_signal_researcher.py [--url URL] [--limit N] [--company NAME] [--parallel N]
"""

import argparse
import asyncio
import json
import sys
import time
from pathlib import Path

import httpx

DEFAULT_URL = "http://localhost:8000"

TEST_COMPANIES = [
    {"company_name": "Loom", "company_domain": "loom.com", "expected_fit": "Strong"},
    {"company_name": "Mux", "company_domain": "mux.com", "expected_fit": "Strong"},
    {"company_name": "Vimeo", "company_domain": "vimeo.com", "expected_fit": "Strong"},
    {"company_name": "Brightcove", "company_domain": "brightcove.com", "expected_fit": "Strong"},
    {"company_name": "Wistia", "company_domain": "wistia.com", "expected_fit": "Strong"},
    {"company_name": "Frame.io", "company_domain": "frame.io", "expected_fit": "Strong"},
    {"company_name": "Panopto", "company_domain": "panopto.com", "expected_fit": "Strong"},
    {"company_name": "Verkada", "company_domain": "verkada.com", "expected_fit": "Moderate"},
    {"company_name": "Coursera", "company_domain": "coursera.com", "expected_fit": "Moderate"},
    {"company_name": "Descript", "company_domain": "descript.com", "expected_fit": "Moderate"},
    {"company_name": "Hudl", "company_domain": "hudl.com", "expected_fit": "Moderate"},
    {"company_name": "Databricks", "company_domain": "databricks.com", "expected_fit": "Moderate"},
    {"company_name": "Warner Bros", "company_domain": "wbd.com", "expected_fit": "Moderate"},
    {"company_name": "Synthesia", "company_domain": "synthesia.com", "expected_fit": "Moderate"},
    {"company_name": "Stripe", "company_domain": "stripe.com", "expected_fit": "Weak"},
    {"company_name": "Notion", "company_domain": "notion.so", "expected_fit": "Weak"},
    {"company_name": "Palantir", "company_domain": "palantir.com", "expected_fit": "Uncertain"},
    {"company_name": "Toast", "company_domain": "pos.toasttab.com", "expected_fit": "Weak"},
    {"company_name": "Figma", "company_domain": "figma.com", "expected_fit": "Weak"},
    {"company_name": "Scale AI", "company_domain": "scale.com", "expected_fit": "Uncertain"},
]


async def run_test(client: httpx.AsyncClient, base_url: str, company: dict, api_key: str | None = None) -> dict:
    """Run a single signal-researcher test."""
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key

    payload = {
        "skill": "signal-researcher",
        "data": {
            "company_name": company["company_name"],
            "company_domain": company["company_domain"],
            "client_slug": "twelve-labs",
        },
    }

    start = time.time()
    try:
        resp = await client.post(f"{base_url}/webhook", json=payload, headers=headers)
        elapsed = time.time() - start
        result = resp.json()
        return {
            "company": company["company_name"],
            "domain": company["company_domain"],
            "expected_fit": company["expected_fit"],
            "status_code": resp.status_code,
            "elapsed_seconds": round(elapsed, 1),
            "response": result,
            "has_error": result.get("error", False),
            "signal_count": len(result.get("signals", [])),
            "priority_tier": result.get("priority_tier", "unknown"),
            "confidence": result.get("confidence_score", 0),
        }
    except Exception as e:
        elapsed = time.time() - start
        return {
            "company": company["company_name"],
            "domain": company["company_domain"],
            "expected_fit": company["expected_fit"],
            "status_code": 0,
            "elapsed_seconds": round(elapsed, 1),
            "response": None,
            "has_error": True,
            "error": str(e),
            "signal_count": 0,
            "priority_tier": "error",
            "confidence": 0,
        }


async def run_batch(base_url: str, companies: list[dict], api_key: str | None, parallel: int) -> list[dict]:
    """Run all companies with concurrency limit."""
    semaphore = asyncio.Semaphore(parallel)
    results = []
    completed = 0
    total = len(companies)
    lock = asyncio.Lock()

    async def run_one(company: dict):
        nonlocal completed
        async with semaphore:
            async with httpx.AsyncClient(timeout=360) as client:
                result = await run_test(client, base_url, company, api_key)

            async with lock:
                completed += 1
                results.append(result)
                if result["has_error"]:
                    error_msg = result.get("error", result.get("response", {}).get("error_message", "unknown"))
                    print(f"  [{completed}/{total}] {result['company']:<20} ERROR: {error_msg}")
                else:
                    print(
                        f"  [{completed}/{total}] {result['company']:<20} "
                        f"{result['priority_tier']:<16} {result['signal_count']} signals | "
                        f"conf={result['confidence']:.2f} | {result['elapsed_seconds']:.1f}s"
                    )

    tasks = [asyncio.create_task(run_one(c)) for c in companies]
    await asyncio.gather(*tasks)

    # Sort results to match input order
    order = {c["company_name"]: i for i, c in enumerate(companies)}
    results.sort(key=lambda r: order.get(r["company"], 999))
    return results


def print_summary(results: list[dict]) -> None:
    """Print a summary table of all results."""
    print("\n" + "=" * 100)
    print(f"{'Company':<20} {'Expected':<12} {'Tier':<16} {'Signals':<8} {'Conf':<6} {'Time':<8} {'Status'}")
    print("-" * 100)

    for r in results:
        status = "ERROR" if r["has_error"] else "OK"
        print(
            f"{r['company']:<20} {r['expected_fit']:<12} {r['priority_tier']:<16} "
            f"{r['signal_count']:<8} {r['confidence']:<6.2f} {r['elapsed_seconds']:<8.1f} {status}"
        )

    print("=" * 100)

    ok = [r for r in results if not r["has_error"]]
    errors = [r for r in results if r["has_error"]]
    avg_time = sum(r["elapsed_seconds"] for r in ok) / len(ok) if ok else 0
    avg_signals = sum(r["signal_count"] for r in ok) / len(ok) if ok else 0

    print(f"\nTotal: {len(results)} | OK: {len(ok)} | Errors: {len(errors)}")
    print(f"Avg time: {avg_time:.1f}s | Avg signals: {avg_signals:.1f}")

    tiers = {}
    for r in ok:
        tier = r["priority_tier"]
        tiers[tier] = tiers.get(tier, 0) + 1
    print(f"Tiers: {tiers}")


def main():
    parser = argparse.ArgumentParser(description="Test signal-researcher skill")
    parser.add_argument("--url", default=DEFAULT_URL, help="API base URL")
    parser.add_argument("--limit", type=int, default=0, help="Limit number of companies (0=all)")
    parser.add_argument("--company", help="Test a single company by name")
    parser.add_argument("--api-key", help="API key for authentication")
    parser.add_argument("--parallel", type=int, default=5, help="Concurrent requests (default 5)")
    parser.add_argument("--output", default="data/signal_test_results.json", help="Output file")
    args = parser.parse_args()

    if args.company:
        companies = [c for c in TEST_COMPANIES if c["company_name"].lower() == args.company.lower()]
        if not companies:
            print(f"Company '{args.company}' not found in test list. Available:")
            for c in TEST_COMPANIES:
                print(f"  - {c['company_name']}")
            sys.exit(1)
    elif args.limit > 0:
        companies = TEST_COMPANIES[:args.limit]
    else:
        companies = TEST_COMPANIES

    print(f"Testing {len(companies)} companies against {args.url}")
    print(f"Skill: signal-researcher | Client: twelve-labs | Parallel: {args.parallel}\n")

    start = time.time()
    results = asyncio.run(run_batch(args.url, companies, args.api_key, args.parallel))
    total_time = time.time() - start

    output_path = Path(args.output)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(results, indent=2, default=str))
    print(f"\nResults saved to {output_path}")
    print(f"Total wall time: {total_time:.0f}s")

    print_summary(results)


if __name__ == "__main__":
    main()
