#!/usr/bin/env python3
"""
Clay Webhook OS — Demo Script

Two-pass demo: classify messy CSV data, then generate personalized emails
for high-confidence winners. Proves CW-OS replaces Clay end-to-end.

Usage:
    # Dry run (no API calls)
    python scripts/demo.py --dry-run

    # Against local server
    python scripts/demo.py --api-url http://localhost:8000

    # Against production
    python scripts/demo.py --api-url https://clay.nomynoms.com --api-key YOUR_KEY
"""

import argparse
import csv
import json
import os
import sys
import time
from pathlib import Path

try:
    import httpx
except ImportError:
    print("ERROR: httpx is required. Install with: pip install httpx")
    sys.exit(1)


# -- Defaults -----------------------------------------------------------------

DEFAULT_CSV = str(Path(__file__).parent.parent / "data" / "demo" / "synthetic-50.csv")
DEFAULT_API_URL = "http://localhost:8000"
DEFAULT_CONFIDENCE_THRESHOLD = 0.7
POLL_INTERVAL_SECONDS = 3
POLL_TIMEOUT_SECONDS = 300  # 5 min max wait per batch


# -- Helpers -------------------------------------------------------------------

def load_csv(csv_path: str) -> list[dict]:
    """Load CSV rows via DictReader."""
    path = Path(csv_path)
    if not path.exists():
        print(f"ERROR: CSV file not found: {csv_path}")
        sys.exit(1)

    with open(path, newline="", encoding="utf-8") as f:
        rows = list(csv.DictReader(f))

    if not rows:
        print("ERROR: CSV file is empty")
        sys.exit(1)

    return rows


def print_header(text: str) -> None:
    """Print a section header."""
    width = 60
    print()
    print("=" * width)
    print(f"  {text}")
    print("=" * width)
    print()


def print_cost_summary(label: str, batch_status: dict) -> None:
    """Print cost breakdown from a batch status response."""
    cost = batch_status.get("cost", {})
    tokens = batch_status.get("tokens", {})
    total_rows = batch_status.get("total_rows", 0)
    completed = batch_status.get("completed", 0)
    failed = batch_status.get("failed", 0)

    print(f"  {label} Cost Summary:")
    print(f"    Rows: {completed} completed, {failed} failed (of {total_rows})")
    print(f"    Tokens: ~{tokens.get('total_est', 0):,} total "
          f"({tokens.get('input_est', 0):,} in / {tokens.get('output_est', 0):,} out)")
    print(f"    Equivalent API cost: ${cost.get('equivalent_api_usd', 0):.4f}")
    print(f"    Subscription cost:   ${cost.get('subscription_usd', 0):.6f}")
    print(f"    Net savings:         ${cost.get('net_savings_usd', 0):.4f}")
    print()


def submit_batch(client: httpx.Client, api_url: str, payload: dict) -> str:
    """POST /batch and return batch_id."""
    # Equivalent curl:
    # curl -X POST {api_url}/batch -H "Content-Type: application/json" -d '{payload}'
    resp = client.post(f"{api_url}/batch", json=payload, timeout=30)
    data = resp.json()

    if data.get("error"):
        print(f"ERROR: Batch submission failed: {data.get('error_message')}")
        sys.exit(1)

    batch_id = data["batch_id"]
    total = data["total_rows"]
    print(f"  Submitted batch {batch_id} ({total} rows)")
    return batch_id


def poll_batch(client: httpx.Client, api_url: str, batch_id: str) -> dict:
    """Poll GET /batch/{batch_id} until done. Returns final status."""
    # Equivalent curl:
    # curl {api_url}/batch/{batch_id}
    start = time.time()
    while True:
        elapsed = time.time() - start
        if elapsed > POLL_TIMEOUT_SECONDS:
            print(f"ERROR: Batch {batch_id} timed out after {POLL_TIMEOUT_SECONDS}s")
            sys.exit(1)

        resp = client.get(f"{api_url}/batch/{batch_id}", timeout=30)
        status = resp.json()

        if status.get("error"):
            print(f"ERROR: Batch status check failed: {status.get('error_message')}")
            sys.exit(1)

        completed = status.get("completed", 0)
        total = status.get("total_rows", 0)
        done = status.get("done", False)

        print(f"  Polling... {completed}/{total} complete", end="")
        if done:
            print(" -- DONE")
            return status
        else:
            print(f" (elapsed: {elapsed:.0f}s)")
            time.sleep(POLL_INTERVAL_SECONDS)


def fetch_job_results(client: httpx.Client, api_url: str, batch_status: dict) -> list[dict]:
    """Fetch full results for each job in the batch via GET /jobs/{job_id}."""
    # Equivalent curl:
    # curl {api_url}/jobs/{job_id}
    results = []
    jobs = batch_status.get("jobs", [])
    for job in jobs:
        job_id = job["id"]
        if job["status"] != "completed":
            continue
        resp = client.get(f"{api_url}/jobs/{job_id}", timeout=30)
        job_data = resp.json()
        results.append(job_data)
    return results


# -- Dry Run -------------------------------------------------------------------

def dry_run(rows: list[dict], confidence_threshold: float) -> None:
    """Validate payloads and show what would happen, no API calls."""
    print_header("DRY RUN MODE -- No API calls will be made")

    # Step 1: Classify payload
    print("STEP 1: Classify")
    print(f"  Rows to classify: {len(rows)}")

    classify_payload = {
        "skill": "classify",
        "rows": rows,
    }

    # Validate payload structure
    assert isinstance(classify_payload["skill"], str)
    assert isinstance(classify_payload["rows"], list)
    assert len(classify_payload["rows"]) == len(rows)

    print(f"  Payload valid: skill='classify', {len(rows)} rows")
    print(f"  Sample row: {json.dumps(rows[0], indent=2)[:200]}...")
    print()

    # Step 2: Simulate classify results for email-gen pass
    # Mock: assume ~60% pass the confidence threshold
    mock_winners = []
    for i, row in enumerate(rows):
        # Simulate: clean/good tiers (first 20) pass, medium partially, messy/sparse fail
        if i < 15:
            mock_confidence = 0.85
        elif i < 25:
            mock_confidence = 0.72
        elif i < 35:
            mock_confidence = 0.55
        else:
            mock_confidence = 0.3

        if mock_confidence >= confidence_threshold:
            merged = {**row}
            merged["title_normalized"] = "Director"  # mock classify output
            merged["industry_normalized"] = row.get("industry", "SaaS") or "SaaS"
            merged["client_slug"] = "twelve-labs"
            mock_winners.append(merged)

    print("STEP 2: Email Gen (filtered by confidence)")
    print(f"  Confidence threshold: {confidence_threshold}")
    print(f"  Simulated winners: {len(mock_winners)} of {len(rows)}")

    email_payload = {
        "skill": "email-gen",
        "rows": mock_winners,
    }

    assert isinstance(email_payload["skill"], str)
    assert isinstance(email_payload["rows"], list)
    for winner in mock_winners:
        assert "client_slug" in winner, "Missing client_slug in email-gen row"
        assert winner["client_slug"] == "twelve-labs"

    print(f"  Payload valid: skill='email-gen', {len(mock_winners)} rows")
    if mock_winners:
        print(f"  Sample winner row: {json.dumps(mock_winners[0], indent=2)[:200]}...")
    print()

    # Cost estimates (rough, based on haiku for classify, sonnet for email-gen)
    classify_cost_per_row = 0.001  # ~$0.001 per row with haiku
    emailgen_cost_per_row = 0.01   # ~$0.01 per row with sonnet
    classify_total = classify_cost_per_row * len(rows)
    emailgen_total = emailgen_cost_per_row * len(mock_winners)
    total_cost = classify_total + emailgen_total

    print_header("COST ESTIMATE (approximate API equivalent)")
    print(f"  Classify:  {len(rows)} rows x ${classify_cost_per_row:.3f} = ${classify_total:.3f}")
    print(f"  Email-gen: {len(mock_winners)} rows x ${emailgen_cost_per_row:.3f} = ${emailgen_total:.3f}")
    print(f"  ----------------------------------------")
    print(f"  Total estimated: ${total_cost:.3f}")
    print(f"  (With Max subscription: $0.00 -- flat rate)")
    print()

    print("DRY RUN COMPLETE -- all payloads valid")
    print(f"  To run for real: python scripts/demo.py --api-url http://localhost:8000")


# -- Live Run ------------------------------------------------------------------

def live_run(
    rows: list[dict],
    api_url: str,
    api_key: str | None,
    confidence_threshold: float,
) -> None:
    """Execute the full two-pass demo against a running server."""
    headers = {}
    if api_key:
        headers["x-api-key"] = api_key

    client = httpx.Client(headers=headers)

    try:
        # ---- Step 1: Classify ----
        print_header("STEP 1: Classify (all rows)")

        classify_payload = {
            "skill": "classify",
            "rows": rows,
        }

        print(f"  Submitting {len(rows)} rows to classify...")
        classify_batch_id = submit_batch(client, api_url, classify_payload)

        print("  Waiting for completion...")
        classify_status = poll_batch(client, api_url, classify_batch_id)
        print_cost_summary("Classify", classify_status)

        # Fetch classify results
        print("  Fetching classify results...")
        classify_results = fetch_job_results(client, api_url, classify_status)
        print(f"  Got results for {len(classify_results)} jobs")

        # ---- Filter winners ----
        print_header(f"FILTERING (confidence >= {confidence_threshold})")

        winners = []
        for job_result in classify_results:
            result = job_result.get("result", {})
            if not result:
                continue

            confidence = result.get("overall_confidence_score", 0.0)
            if confidence >= confidence_threshold:
                # Find matching original row by row_id
                row_id = job_result.get("row_id", "")
                try:
                    row_idx = int(row_id)
                    original_row = rows[row_idx] if row_idx < len(rows) else {}
                except (ValueError, IndexError):
                    original_row = {}

                # Merge original data + classify output
                merged = {**original_row}
                merged["title_normalized"] = result.get("title_normalized", "")
                merged["industry_normalized"] = result.get("industry_normalized", "")
                merged["client_slug"] = "twelve-labs"
                winners.append(merged)

        print(f"  Winners: {len(winners)} of {len(classify_results)} "
              f"(threshold: {confidence_threshold})")

        if not winners:
            print("\n  No rows passed the confidence threshold. Demo complete.")
            print(f"\n  Classify batch: {classify_batch_id}")
            return

        # ---- Step 2: Email Gen ----
        print_header("STEP 2: Email Gen (winners only)")

        email_payload = {
            "skill": "email-gen",
            "rows": winners,
        }

        print(f"  Submitting {len(winners)} rows to email-gen...")
        email_batch_id = submit_batch(client, api_url, email_payload)

        print("  Waiting for completion...")
        email_status = poll_batch(client, api_url, email_batch_id)
        print_cost_summary("Email Gen", email_status)

        # ---- Final Summary ----
        print_header("DEMO COMPLETE")

        classify_cost = classify_status.get("cost", {}).get("equivalent_api_usd", 0)
        email_cost = email_status.get("cost", {}).get("equivalent_api_usd", 0)
        total_cost = classify_cost + email_cost

        classify_sub = classify_status.get("cost", {}).get("subscription_usd", 0)
        email_sub = email_status.get("cost", {}).get("subscription_usd", 0)
        total_sub = classify_sub + email_sub

        print(f"  TOTAL COST SUMMARY:")
        print(f"    Equivalent API cost: ${total_cost:.4f}")
        print(f"    Subscription cost:   ${total_sub:.6f}")
        print(f"    Net savings:         ${total_cost - total_sub:.4f}")
        print()
        print(f"  BATCH IDs (view in dashboard):")
        print(f"    Classify:  {classify_batch_id}")
        print(f"    Email-gen: {email_batch_id}")
        print()
        dashboard_base = "https://dashboard-beta-sable-36.vercel.app"
        print(f"  VIEW RESULTS:")
        print(f"    {dashboard_base}/batch-results/{email_batch_id}")
        print()

    finally:
        client.close()


# -- Main ----------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="CW-OS Demo: Classify -> Email Gen (two-pass batch pipeline)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python scripts/demo.py --dry-run
  python scripts/demo.py --api-url http://localhost:8000
  python scripts/demo.py --api-url https://clay.nomynoms.com --api-key $WEBHOOK_API_KEY
        """,
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate payloads without making API calls",
    )
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"API base URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--api-key",
        default=os.environ.get("WEBHOOK_API_KEY"),
        help="API key (default: reads from WEBHOOK_API_KEY env var)",
    )
    parser.add_argument(
        "--csv",
        default=DEFAULT_CSV,
        help=f"Path to CSV file (default: {DEFAULT_CSV})",
    )
    parser.add_argument(
        "--confidence-threshold",
        type=float,
        default=DEFAULT_CONFIDENCE_THRESHOLD,
        help=f"Minimum classify confidence for email-gen (default: {DEFAULT_CONFIDENCE_THRESHOLD})",
    )

    args = parser.parse_args()

    print_header("CW-OS Demo: Classify -> Email Gen")
    print(f"  CSV: {args.csv}")
    print(f"  API: {args.api_url}")
    print(f"  Confidence threshold: {args.confidence_threshold}")
    print(f"  Mode: {'DRY RUN' if args.dry_run else 'LIVE'}")

    # Load CSV
    rows = load_csv(args.csv)
    print(f"  Loaded {len(rows)} rows from CSV")

    if args.dry_run:
        dry_run(rows, args.confidence_threshold)
    else:
        if not args.api_key:
            print("\n  WARNING: No API key provided. Set WEBHOOK_API_KEY or use --api-key")
        live_run(rows, args.api_url, args.api_key, args.confidence_threshold)


if __name__ == "__main__":
    main()
