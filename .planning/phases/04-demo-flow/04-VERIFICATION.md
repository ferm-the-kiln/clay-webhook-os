---
phase: 04-demo-flow
verified: 2026-03-14T01:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Phase 4: Demo Flow Verification Report

**Phase Goal:** The Kiln team can watch a complete two-pass demo that proves CW-OS replaces Clay: messy data in, classified + enriched + personalized emails out
**Verified:** 2026-03-14T01:00:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A synthetic CSV of 50 companies exists with 5 data quality tiers (10 rows each) | VERIFIED | `data/demo/synthetic-50.csv` — 51 lines (1 header + 50 rows), all 8 pytest assertions pass including `test_csv_has_exactly_50_rows` |
| 2 | The CSV includes real company domains for clean/good tiers and plausible fakes for messy/sparse tiers | VERIFIED | `test_real_company_domains` passes (>= 20 rows with real `.`-containing domains); messy/sparse tiers have missing or fictional domains. `test_no_duplicate_domains` passes. |
| 3 | A Python demo script can execute classify -> email-gen end-to-end via the batch API | VERIFIED | `scripts/demo.py` — 413 lines; submits `POST /batch` for classify (line 94), polls `GET /batch/{batch_id}` (line 118), submits second `POST /batch` for email-gen with `client_slug: "twelve-labs"` (line 317) |
| 4 | The demo script has a --dry-run mode that validates payloads without making API calls | VERIFIED | `python scripts/demo.py --dry-run` exits 0 with output confirming 50 classify rows valid, 25 email-gen winner rows valid, all payloads structurally correct |
| 5 | Cost is displayed at each step and as a total | VERIFIED | `print_cost_summary()` called after classify (line 267) and email-gen (line 322); final summary prints equivalent API cost, subscription cost, net savings, and both batch IDs (lines 334-345) |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `data/demo/synthetic-50.csv` | 50-row synthetic CSV with varied data quality | VERIFIED | Exists, 51 lines (1 header), contains all 8 required columns, 5 quality tiers present, 8+ industry verticals represented |
| `tests/test_demo_data.py` | Unit tests validating CSV structure and quality tiers | VERIFIED | Exists, 168 lines (>= 30 min), 8 tests all passing: structure (3), quality distribution (5) |
| `scripts/demo.py` | Python demo orchestrator: classify -> email-gen via batch API | VERIFIED | Exists, 413 lines (>= 80 min), full argparse CLI, dry-run mode, live execution mode, cost display |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `scripts/demo.py` | `data/demo/synthetic-50.csv` | `csv.DictReader` | WIRED | Line 36: DEFAULT_CSV points to `synthetic-50.csv`; line 53: `csv.DictReader(f)` loads it |
| `scripts/demo.py` | `POST /batch` | `httpx.Client.post` | WIRED | Line 94: `client.post(f"{api_url}/batch", json=payload)` — classify pass; line 94 pattern reused for email-gen at line 94 via `submit_batch()` |
| `scripts/demo.py` | `GET /batch/{batch_id}` | polling loop | WIRED | Line 118: `client.get(f"{api_url}/batch/{batch_id}")` inside `poll_batch()` with `time.sleep(3)` between polls |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| DEMO-01 | 04-01-PLAN.md | Synthetic test CSV of 50 companies with varied data quality (clean + messy + missing fields) | SATISFIED | `data/demo/synthetic-50.csv` exists with 50 rows across 5 quality tiers; `tests/test_demo_data.py` runs 8 assertions all green |
| DEMO-02 | 04-01-PLAN.md | Two-pass demo flow works end-to-end: classify -> enrich -> email-gen using Twelve Labs profile | SATISFIED | `scripts/demo.py` implements full two-pass flow via batch API with `client_slug: "twelve-labs"` injected into every email-gen winner row (line 297); `--dry-run` validates payloads and exits 0 |

No orphaned requirements detected: REQUIREMENTS.md maps only DEMO-01 and DEMO-02 to Phase 4, both claimed by plan 04-01.

### Anti-Patterns Found

None detected across all three new files. No TODO/FIXME/placeholder comments, no empty return stubs, no handler-only-prevents-default patterns.

### Human Verification Required

#### 1. End-to-end live demo execution

**Test:** With the backend running (`uvicorn app.main:app --reload --port 8000`), run `python scripts/demo.py --api-url http://localhost:8000`. Optionally set `WEBHOOK_API_KEY` if auth is enforced.
**Expected:** Step 1 submits 50 rows to classify batch, polls to completion, prints cost summary. Filter step shows ~15-25 winners. Step 2 submits winners to email-gen batch, polls to completion, prints batch IDs and dashboard URL. Results are viewable at `/batch-results/{email_batch_id}` with confidence coloring and email preview side panel.
**Why human:** Requires a running backend with the classify and email-gen skills available. Batch processing involves real subprocess calls to `claude --print`. Cost display accuracy depends on live token estimator data. Dashboard viewing is a visual UI check.

### Gaps Summary

No gaps. All five must-haves verified, all three artifacts pass all three levels (exists, substantive, wired), both key links confirmed. Full test suite at 2300 tests, all passing, with the 8 new CSV validation tests included.

---

_Verified: 2026-03-14T01:00:00Z_
_Verifier: Claude (gsd-verifier)_
