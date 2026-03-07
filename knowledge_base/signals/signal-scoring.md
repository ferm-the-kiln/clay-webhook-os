---
name: SIGNAL_SCORING
description: Signal weighting, decay rules, and stacking logic for ICP scoring
domain: methodology
node_type: framework
status: validated
last_updated: 2026-03-07
tags:
  - methodology
  - signals
  - scoring
  - icp
topics:
  - lead-scoring
  - signal-analysis
  - account-prioritization
related_concepts:
  - "[[signal-taxonomy]]"
  - "[[signal-openers]]"
  - "[[icp-scorer]]"
---

# Signal Scoring Framework

Signals tell you WHEN to reach out. ICP tells you WHO to reach out to. This
framework combines both — weighting signals by strength, applying time decay,
and stacking multiple signals for compound scoring.

## Signal Strength Tiers

### Strong Signals (Base: 25-30 points)

| Signal | Points | Why Strong |
|--------|--------|------------|
| Funding round (Series A+) | 30 | Confirmed budget + growth mandate |
| Leadership change (VP+) | 28 | New decision-maker, open to vendors |
| Acquisition (acquirer side) | 25 | Stack consolidation, new budget |
| Tech stack change (your category) | 25 | Actively evaluating alternatives |

Strong signals indicate active buying motion or organizational change that
creates budget and urgency. A single strong signal is enough to trigger
outreach.

### Moderate Signals (Base: 15-20 points)

| Signal | Points | Why Moderate |
|--------|--------|--------------|
| Hiring surge (3+ roles, relevant function) | 20 | Investing in function, pain is real |
| Product launch | 18 | New demand gen needs |
| Geographic expansion | 18 | Net-new pipeline requirements |
| Partnership announcement | 15 | Adjacent needs emerge |
| Tech stack change (adjacent category) | 15 | Evaluating workflows broadly |

Moderate signals suggest investment and growth but don't confirm active
buying intent. Best when combined with a second signal or strong ICP fit.

### Weak Signals (Base: 5-10 points)

| Signal | Points | Why Weak |
|--------|--------|----------|
| Single job posting (relevant function) | 10 | Could be backfill, not growth |
| Press/media mention | 8 | Awareness, not intent |
| Conference speaking/attending | 7 | Industry engagement |
| Social media activity (relevant topics) | 5 | Interest, not action |
| Website traffic increase | 5 | Noisy, many false positives |

Weak signals add context but should never drive outreach alone. Use them to
enrich an account that already has moderate or strong signals.

## Time Decay Rules

Signals lose relevance over time. Apply decay multipliers to the base score.

| Days Since Signal | Multiplier | Effective Range |
|-------------------|------------|-----------------|
| 0-7 days | 1.0x | Full strength |
| 8-14 days | 0.9x | Still hot |
| 15-30 days | 0.7x | Warm, act now |
| 31-60 days | 0.4x | Cooling fast |
| 61-90 days | 0.2x | Stale — reference carefully |
| 90+ days | 0.0x | Dead signal — do not reference |

**Exceptions to decay:**
- Leadership changes decay slower (0.7x at 60 days) because the evaluation
  window for new execs extends 90-120 days.
- Acquisitions decay slower (0.5x at 90 days) because integration timelines
  run 6-12 months.
- Hiring surges refresh if new postings appear — reset the clock.

## Stacking Rules

Multiple signals on the same account compound. This is where real
prioritization happens.

### Compound Scoring Formula

```
account_signal_score = sum(signal_base * decay_multiplier) * stack_bonus
```

| Active Signals | Stack Bonus | Logic |
|----------------|-------------|-------|
| 1 signal | 1.0x | No bonus |
| 2 signals | 1.3x | Two signals confirm intent |
| 3 signals | 1.6x | High-confidence account |
| 4+ signals | 2.0x (cap) | Maximum compound — diminishing returns |

### High-Value Combinations

These specific stacks get an extra boost because they indicate a clear buying
motion:

| Combination | Extra Bonus | Interpretation |
|-------------|-------------|----------------|
| Funding + Hiring | +10 | Deploying capital into growth |
| Leadership change + Tech change | +10 | New leader evaluating stack |
| Funding + Leadership change | +8 | New money + new decision-maker |
| Product launch + Hiring (marketing) | +8 | Building demand gen muscle |
| Expansion + Hiring (sales) | +8 | Building pipeline in new market |

## Combining with ICP Score

Signal score and ICP score are separate dimensions. Combine them for final
account priority.

```
priority_score = (icp_score * 0.5) + (signal_score * 0.5)
```

| Priority Tier | Score Range | Action |
|---------------|-------------|--------|
| Tier 1 — Now | 75-100 | Immediate personalized outreach |
| Tier 2 — Soon | 50-74 | Outreach within 7 days |
| Tier 3 — Watch | 25-49 | Add to nurture sequence |
| Tier 4 — Pass | 0-24 | Do not contact — wait for signals |

**Weighting adjustment:** If your campaign is signal-first (trigger-based),
shift to 0.4 ICP / 0.6 signal. If your campaign is ICP-first (account-based),
shift to 0.6 ICP / 0.4 signal.

## Implementation Notes

- Signal data sources: Clay, Bombora, Builtwith, LinkedIn Sales Nav, Google
  Alerts, Crunchbase, job board scrapers.
- Refresh signal data weekly. Stale data produces stale scores.
- Log signal-to-meeting conversion rates by signal type. After 90 days,
  re-calibrate base points using actual performance data.
- Treat this framework as a starting point. Every ICP and market will skew
  the weights differently.

## Evidence

[VERIFIED: Scoring model derived from Predictable Revenue, TOPO, and Forrester research]
[VALIDATED: Calibrated across signal-triggered campaigns at The Kiln]
