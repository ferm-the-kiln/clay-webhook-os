---
phase: 04-demo-flow
plan: 01
subsystem: demo
tags: [csv, batch-api, classify, email-gen, httpx, argparse, tdd]

# Dependency graph
requires:
  - phase: 01-classify-skill
    provides: classify skill for data normalization
  - phase: 02-deepline-enrichment
    provides: batch API endpoints (POST /batch, GET /batch/{id})
  - phase: 03-batch-results-dashboard
    provides: batch results UI for viewing demo output
provides:
  - "50-row synthetic CSV with 5 quality tiers for demo"
  - "Python demo script orchestrating classify -> email-gen via batch API"
  - "Unit tests validating CSV structure and quality distribution"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: ["two-pass batch orchestration: classify then filter then email-gen", "TDD for data fixtures"]

key-files:
  created:
    - data/demo/synthetic-50.csv
    - tests/test_demo_data.py
    - scripts/demo.py
  modified: []

key-decisions:
  - "Used mock classify output in dry-run mode to simulate 60% pass rate"
  - "Fetch job results individually via GET /jobs/{id} since batch status omits result field"
  - "Force-added CSV to git despite data/ gitignore (demo data should be version-controlled)"

patterns-established:
  - "Demo scripts live in scripts/ with argparse CLI and --dry-run validation mode"

requirements-completed: [DEMO-01, DEMO-02]

# Metrics
duration: 5min
completed: 2026-03-13
---

# Phase 4 Plan 1: Demo Flow Summary

**50-row synthetic CSV with 5 quality tiers and a two-pass demo script (classify -> email-gen) using batch API with dry-run validation**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-14T00:17:30Z
- **Completed:** 2026-03-14T00:22:05Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created synthetic-50.csv with 50 companies across 5 data quality tiers (clean, good, medium, messy, sparse)
- Built 8 TDD tests validating CSV structure, column presence, industry diversity, domain realism, and quality variance
- Created demo.py orchestrator with --dry-run, --api-url, --api-key, --csv, --confidence-threshold flags
- Demo script validates payloads, submits batch jobs, polls for completion, merges classify output into email-gen input

## Task Commits

Each task was committed atomically:

1. **Task 1: Create synthetic CSV and validation tests** - `0204784` (test: failing tests, TDD RED) + `f5ec060` (feat: CSV data, TDD GREEN)
2. **Task 2: Create Python demo script** - `cdda852` (feat: demo orchestrator)

_Note: Task 1 followed TDD with separate RED and GREEN commits._

## Files Created/Modified
- `data/demo/synthetic-50.csv` - 50-row synthetic dataset with varied data quality across 5 tiers
- `tests/test_demo_data.py` - 8 unit tests validating CSV structure and quality distribution
- `scripts/demo.py` - Python demo script orchestrating classify -> email-gen via batch API

## Decisions Made
- Used mock classify output in dry-run mode (simulates ~60% pass rate) rather than requiring a live server
- Fetch individual job results via GET /jobs/{id} since GET /batch/{id} does not include the result field
- Force-added CSV to git despite data/ being gitignored -- demo data should be version-controlled

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- data/ directory is gitignored -- used `git add -f` to force-track demo CSV (not a runtime data file, belongs in version control)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Demo can be run immediately: `python scripts/demo.py --dry-run` for validation
- For live execution, start the backend (`uvicorn app.main:app --reload --port 8000`) and run `python scripts/demo.py`
- Results viewable in the batch results dashboard built in Phase 3

---
*Phase: 04-demo-flow*
*Completed: 2026-03-13*
