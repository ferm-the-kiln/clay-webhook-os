# HubSpot Parent-Child Routing — Data Decision Flow

> **Running example:** NFL (parent) → Kansas City Chiefs (child)
> **Parent record in HubSpot:** LinkedIn = `linkedin.com/company/nfl`, domain = `nfl.com`

---

## Two Options

We're evaluating two approaches. Both start with the same gate (personal email filter) but differ in how they use LinkedIn and email domain data.

| | Option A | Option B |
|---|---|---|
| **Name** | LinkedIn + Email (Full Signal) | LinkedIn Only (Simple Gate) |
| **How it works** | Email domain is the primary differentiator, LinkedIn confirms confidence | LinkedIn is the only routing signal |
| **Strength** | Catches more edge cases (~20-30% more) | Simpler to build and explain |
| **Weakness** | More columns in Clay, slightly more complex | Misses cases where LI shows parent but person works at child |

---

## Shared: Personal Email Gate

Both options start here. If the contact uses a personal email, stop — send to a human.

```
Personal email? (@gmail, @yahoo, @hotmail, @outlook)
  └── Yes → SEND TO REP FOR REVIEW (stop here)
  └── No  → Continue to Option A or B
```

---

# Option A: LinkedIn + Email (Full Signal)

**Core idea:** LinkedIn tells us the corporate family. Email domain tells us which entity.

### Why both signals matter

A Chiefs employee might have:
- LinkedIn → `linkedin.com/company/nfl` (shows the parent brand)
- Email → devon@chiefs.com (shows the actual entity)

With only LinkedIn, that person stays on NFL. Wrong. The email domain is what catches it.

### Decision flow

```
Step 1: Does email domain match the parent?
  │
  ├── No (e.g. @chiefs.com ≠ @nfl.com)
  │     └── LinkedIn also ≠ parent?  → AUTO-ROUTE TO CHILD (high confidence)
  │     └── LinkedIn = parent?       → AUTO-ROUTE TO CHILD (medium confidence)
  │     └── No LinkedIn?             → AUTO-ROUTE TO CHILD (email fallback)
  │
  ├── Yes (e.g. @nfl.com = @nfl.com)
  │     └── LinkedIn also = parent?  → KEEP ON PARENT
  │     └── LinkedIn ≠ parent?       → AUTO-ROUTE TO CHILD (LI overrides shared domain)
  │     └── No LinkedIn?             → SEND TO REP (can't tell — shared domain)
```

### Every scenario

| # | Email | LinkedIn | Decision | Why |
|---|-------|----------|----------|-----|
| 1 | @chiefs.com | Points to Chiefs | **Auto-route → Chiefs** | Both signals say child |
| 2 | @chiefs.com | Points to NFL | **Auto-route → Chiefs** | Email differentiates — LI just shows parent brand |
| 3 | @chiefs.com | *(missing)* | **Auto-route → Chiefs** | Email maps to known child |
| 4 | @nfl.com | Points to Chiefs | **Auto-route → Chiefs** | LI overrides shared parent domain |
| 5 | @nfl.com | Points to NFL | **Keep on parent** | Both signals agree — actual parent employee |
| 6 | @nfl.com | *(missing)* | **Send to rep** | Could be parent or subsidiary with shared domain |
| 7 | @gmail.com | *(any)* | **Send to rep** | Personal email gate caught it |

### Clay formula

```
IF is_personal_email → "SEND TO REP"
IF email ≠ parent    → "AUTO-ROUTE TO CHILD"
IF email = parent AND linkedin ≠ parent → "AUTO-ROUTE TO CHILD"
IF email = parent AND linkedin = parent → "KEEP ON PARENT"
Everything else      → "SEND TO REP"
```

### What it catches that Option B misses

- **Row #2** — Devon with @chiefs.com but LinkedIn showing NFL → Option B keeps him on NFL. Option A routes him correctly.
- **Row #3** — Tyler with @chiefs.com but no LinkedIn → Option B sends to rep. Option A routes him automatically.

---

# Option B: LinkedIn Only (Simple Gate)

**Core idea:** LinkedIn Company URL is the only routing signal. If it doesn't match the parent, route to child. If it does or is missing, keep on parent or flag for review.

### Decision flow

```
Step 1: Is there a LinkedIn Company URL?
  │
  ├── No  → SEND TO REP (not enough data)
  │
  ├── Yes → Does it match the parent?
  │     └── Yes → KEEP ON PARENT
  │     └── No  → AUTO-ROUTE TO CHILD
```

### Every scenario

| # | Email | LinkedIn | Decision | Why |
|---|-------|----------|----------|-----|
| 1 | @chiefs.com | Points to Chiefs | **Auto-route → Chiefs** | LI says child |
| 2 | @chiefs.com | Points to NFL | **Keep on parent** | LI says parent (WRONG — missed) |
| 3 | @chiefs.com | *(missing)* | **Send to rep** | No LI data |
| 4 | @nfl.com | Points to Chiefs | **Auto-route → Chiefs** | LI says child |
| 5 | @nfl.com | Points to NFL | **Keep on parent** | LI says parent (correct) |
| 6 | @nfl.com | *(missing)* | **Send to rep** | No LI data |
| 7 | @gmail.com | *(any)* | **Send to rep** | Personal email gate caught it |

### Clay formula

```
IF is_personal_email → "SEND TO REP"
IF no linkedin       → "SEND TO REP"
IF linkedin ≠ parent → "AUTO-ROUTE TO CHILD"
IF linkedin = parent → "KEEP ON PARENT"
```

### What it misses

- **Row #2** — person with @chiefs.com email but LinkedIn showing NFL parent brand. Option B incorrectly keeps them on NFL.
- **Row #3** — person with @chiefs.com email but no LinkedIn. Option B can't route them at all.

---

# Side-by-Side Comparison

| Scenario | Option A (LI + Email) | Option B (LI Only) | Difference |
|----------|----------------------|--------------------|----|
| Email=child, LI=child | Auto-route | Auto-route | Same |
| Email=child, LI=parent | **Auto-route** | Keep on parent | **A catches it, B misses** |
| Email=child, no LI | **Auto-route** | Send to rep | **A catches it, B can't** |
| Email=parent, LI=child | Auto-route | Auto-route | Same |
| Email=parent, LI=parent | Keep on parent | Keep on parent | Same |
| Email=parent, no LI | Send to rep | Send to rep | Same |
| Personal email | Send to rep | Send to rep | Same |

**Bottom line:** Option A catches 2 additional scenarios that Option B sends to manual review or gets wrong.

---

## Clay Table Columns

### Both options need

| Column | What It Is | How You Get It |
|--------|-----------|----------------|
| `work_email` | Contact's email | Already in Clay |
| `linkedin_company_url` | Company URL from contact's LinkedIn | Clay enrichment |
| `parent_li_url` | Parent company's LinkedIn URL | From HubSpot record |

### Option A also needs

| Column | What It Is | How You Get It |
|--------|-----------|----------------|
| `parent_domain` | Parent company's email domain | From HubSpot record |
| `email_domain` | Extracted from work_email | `SPLIT(work_email, "@")[1]` |
| `is_personal_email` | Gmail/Yahoo/etc check | Formula |
| `email_matches_parent` | Domain comparison | Formula |

### Option B just needs

| Column | What It Is | How You Get It |
|--------|-----------|----------------|
| `is_personal_email` | Gmail/Yahoo/etc check | Formula |
| `li_matches_parent` | URL comparison | Formula |

---

## What Happens After Routing (Both Options)

| Decision | Action |
|----------|--------|
| **Auto-route to child** | Clay pushes contact to HubSpot, associates with child company |
| **Keep on parent** | No action — contact stays where it is |
| **Send to rep** | Contact lands in a "Needs Review" list in HubSpot for manual routing |
