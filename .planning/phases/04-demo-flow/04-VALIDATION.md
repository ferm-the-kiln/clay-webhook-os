---
phase: 4
slug: demo-flow
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-13
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x (existing, 2292 tests passing) |
| **Config file** | `tests/conftest.py` |
| **Quick run command** | `source .venv/bin/activate && python -m pytest tests/ --tb=short -q` |
| **Full suite command** | `source .venv/bin/activate && python -m pytest tests/ --tb=short` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `source .venv/bin/activate && python -m pytest tests/ --tb=short -q`
- **After every plan wave:** Run `source .venv/bin/activate && python -m pytest tests/ --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | DEMO-01 | unit | `python -m pytest tests/test_demo_data.py -v` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | DEMO-02 | manual + smoke | `python scripts/demo.py --dry-run` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `data/demo/synthetic-50.csv` — 50-row CSV with varied data quality (DEMO-01)
- [ ] `scripts/demo.py` — Python demo script orchestrating classify -> email-gen (DEMO-02)
- [ ] `tests/test_demo_data.py` — Validates CSV structure (50 rows, required columns, data quality tiers)

*Existing test infrastructure covers framework needs — no new framework install required.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| End-to-end demo produces emails viewable in dashboard | DEMO-02 | Requires running backend + dashboard + real API calls | 1. Start backend (`uvicorn app.main:app`), 2. Run `python scripts/demo.py`, 3. Open batch results in dashboard, 4. Verify confidence coloring and email preview |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
