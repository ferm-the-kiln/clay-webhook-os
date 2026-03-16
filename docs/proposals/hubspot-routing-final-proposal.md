# HubSpot Parent-Child Routing — Final Proposal

## The Problem

When a contact works for a subsidiary (Kansas City Chiefs) but their email domain belongs to the parent (NFL), HubSpot auto-associates them to the wrong company. The wrong rep gets the lead.

**Example:** Devon Carter works for the Kansas City Chiefs, but his email is devon@nfl.com. HubSpot puts him on the NFL record. The NFL rep gets him instead of the Chiefs rep.

This happens across every parent-child relationship — not just NFL.

---

## The Strategy

Three phases, each building on the last:

1. **Discovery** — Use Claude to analyze existing HubSpot data and find all parent-child relationships. Team reviews and approves.
2. **Routing** — Build automated routing in Clay so new contacts get assigned to the right child company using LinkedIn and email data.
3. **Dedup Safety Net** — Prevent duplicate company records from being created during routing.

---

## Phase 1: Discovery (Claude-Powered)

**What happens:** We feed Claude a parent company's contact list with LinkedIn enrichment. Claude identifies which contacts likely belong to child companies.

**Output:** A review spreadsheet with one row per child company found:

| Child Company | Contacts Found | How Detected | Suggested Action | Team Notes |
|---------------|---------------|--------------|-----------------|------------|
| Kansas City Chiefs | 12 | LinkedIn URL + email domain | Create child, re-associate | *(team fills in)* |
| Dallas Cowboys | 8 | LinkedIn URL | Create child, re-associate | |
| NFL Films | 3 | Email domain only | Flag for review | |

**The team decides.** Claude suggests, humans approve. No automated changes happen until the team signs off.

**Claude's role ends here.** After Phase 1, everything is Clay + HubSpot automation. No AI in the routing loop.

---

## Phase 2: Automated Routing (Two Options)

Once parent-child relationships are established, we need to route NEW inbound contacts to the right company. We have two approaches:

---

### Option A: LinkedIn + Email (Full Signal)

**How it works:** Email domain tells us which specific entity. LinkedIn confirms confidence.

```
Contact comes in
  │
  ├── Already correctly associated? → SKIP (no action needed)
  │
  ├── Personal email? (@gmail, @yahoo) → SEND TO REP (stop)
  │
  ├── Email domain ≠ parent domain?
  │     → AUTO-ROUTE TO CHILD
  │       (LinkedIn adds confidence but email is the differentiator)
  │
  ├── Email domain = parent domain AND LinkedIn ≠ parent?
  │     → AUTO-ROUTE TO CHILD
  │       (LI overrides shared email domain)
  │
  ├── Email domain = parent AND LinkedIn = parent?
  │     ├── Job title/company mentions child? → SEND TO REP
  │     └── No child match → KEEP ON PARENT (all signals agree)
  │
  └── Not enough data?
        → SEND TO REP FOR REVIEW
```

**Every scenario:**

| Email | LinkedIn | What Happens |
|-------|----------|-------------|
| @chiefs.com | Points to Chiefs | Auto-route → Chiefs |
| @chiefs.com | Points to NFL | Auto-route → Chiefs (email differentiates) |
| @chiefs.com | Missing | Auto-route → Chiefs (email fallback) |
| @nfl.com | Points to Chiefs | Auto-route → Chiefs (LI overrides) |
| @nfl.com | Points to NFL | Keep on NFL (both agree) |
| @nfl.com | Points to NFL + title says "Chiefs" | Send to rep (title suggests subsidiary) |
| @nfl.com | Missing | Send to rep (shared domain, can't tell) |
| @gmail.com | Any | Send to rep (personal email) |
| *(any)* | Already on correct child | Skip — already correctly associated |

**Pros:** Catches ~20-30% more edge cases. Handles the "works at Chiefs but LinkedIn shows NFL" scenario.
**Cons:** A few more columns in Clay.

---

### Option B: LinkedIn Only (Simple Gate)

**How it works:** LinkedIn Company URL is the only routing signal.

```
Contact comes in
  │
  ├── Already correctly associated? → SKIP (no action needed)
  │
  ├── Personal email? (@gmail, @yahoo) → SEND TO REP (stop)
  │
  ├── No LinkedIn data? → SEND TO REP (stop)
  │
  ├── LinkedIn ≠ parent? → AUTO-ROUTE TO CHILD
  │
  └── LinkedIn = parent?
        ├── Job title/company mentions child? → SEND TO REP
        └── No child match → KEEP ON PARENT
```

**Every scenario:**

| Email | LinkedIn | What Happens |
|-------|----------|-------------|
| @chiefs.com | Points to Chiefs | Auto-route → Chiefs |
| @chiefs.com | Points to NFL | Keep on NFL (WRONG — missed) |
| @chiefs.com | Missing | Send to rep |
| @nfl.com | Points to Chiefs | Auto-route → Chiefs |
| @nfl.com | Points to NFL | Keep on parent (correct) |
| @nfl.com | Points to NFL + title says "Chiefs" | Send to rep (title suggests subsidiary) |
| @nfl.com | Missing | Send to rep |
| @gmail.com | Any | Send to rep (personal email) |
| *(any)* | Already on correct child | Skip — already correctly associated |

**Pros:** Simpler to build. Fewer columns. Easy to explain.
**Cons:** Misses cases where LinkedIn shows the parent brand but the person works at the child. Can't use email as fallback when LinkedIn is missing.

---

### Side-by-Side: What Each Option Catches

| Scenario | Option A | Option B |
|----------|----------|----------|
| Email=child, LI=child | Auto-route | Auto-route |
| Email=child, LI=parent | **Auto-route** | Keeps on parent (wrong) |
| Email=child, no LI | **Auto-route** | Send to rep |
| Email=parent, LI=child | Auto-route | Auto-route |
| Email=parent, LI=parent | Keep on parent | Keep on parent |
| Email=parent, LI=parent, title=child | **Send to rep** | **Send to rep** |
| Already correctly associated | **Skip** | **Skip** |
| Email=parent, no LI | Send to rep | Send to rep |
| Personal email | Send to rep | Send to rep |

**Option A catches 2 scenarios that Option B misses or gets wrong.**

---

## Phase 3: Dedup Safety Net

When Clay creates child companies in HubSpot, we need to make sure we don't accidentally create duplicates. Four layers of protection, each catching what the previous one might miss:

### Layer 1: Mapping Table (Instant)
Before creating any company, Clay checks its own lookup table: "Do we already have a company with this LinkedIn URL?" If yes, skip creation and just associate the contact.

### Layer 2: HubSpot Search (Pre-Create)
If the mapping table says "new company," Clay searches HubSpot before creating it. This catches companies that were created outside of Clay (manually by reps, via import, etc.).

### Layer 3: Verify After Create (Race Condition)
If two contacts for the same new subsidiary arrive at the exact same time, both might pass Layers 1 and 2 before either one creates the company. After creating, Clay immediately checks: "Did another record just get created with this same LinkedIn URL?" If yes, keep the first one, delete the duplicate.

### Layer 4: Weekly Scan (Cleanup)
A weekly automated script scans all HubSpot companies, groups them by LinkedIn URL, and flags any duplicates that slipped through. This is the safety net — catches anything the first three layers missed.

**In plain English:** We check before, we check during, we check after, and we check every week. Duplicates won't survive.

---

## What This Looks Like in Clay

### Columns needed (Option A)

| Column | Purpose |
|--------|---------|
| `work_email` | Contact's email (already exists) |
| `linkedin_company_url` | From Clay enrichment (already exists) |
| `parent_li_url` | Parent's LinkedIn URL (from HubSpot) |
| `parent_domain` | Parent's email domain (from HubSpot) |
| `email_domain` | Extracted from email (formula) |
| `is_personal_email` | Gmail/Yahoo/etc check (formula) |
| `current_company_li_url` | Contact's currently associated company LI URL (HubSpot) |
| `job_title` | Contact's job title (Clay enrichment) |
| `linkedin_company_name` | Company name from LinkedIn experience (Clay enrichment) |
| `routing_decision` | Auto-route / Keep / Send to rep / Skip (formula) |

### Columns needed (Option B)

| Column | Purpose |
|--------|---------|
| `work_email` | Contact's email (already exists) |
| `linkedin_company_url` | From Clay enrichment (already exists) |
| `parent_li_url` | Parent's LinkedIn URL (from HubSpot) |
| `is_personal_email` | Gmail/Yahoo/etc check (formula) |
| `current_company_li_url` | Contact's currently associated company LI URL (HubSpot) |
| `job_title` | Contact's job title (Clay enrichment) |
| `linkedin_company_name` | Company name from LinkedIn experience (Clay enrichment) |
| `routing_decision` | Auto-route / Keep / Send to rep / Skip (formula) |

### After routing decision

| Decision | What Clay Does |
|----------|---------------|
| **Auto-route to child** | Search HubSpot for child company → associate contact → set owner |
| **Keep on parent** | No action |
| **Send to rep** | Push to "Needs Review" list in HubSpot |

---

## What We Need From Sean

1. **Which routing option?** Option A (LinkedIn + Email) or Option B (LinkedIn Only)?
2. **Industry → Segment mapping** — needed for owner assignment after routing
3. **Confirm:** Does Clay currently push LinkedIn Company URL to HubSpot contact properties?
4. **Pilot parent company** — which parent-child group should we test first?

---

## Implementation Timeline

| Phase | What | Where | When |
|-------|------|-------|------|
| 1 | Discovery — Claude identifies parent-child relationships | Claude + spreadsheet | Week 1 |
| 2 | Build routing in Clay (Option A or B) | Clay + HubSpot API | Weeks 2-3 |
| 3 | Dedup safety net + weekly scan | Clay + script | Week 3 |
| 4 | Scale to all parent companies + monitoring | Clay | Week 4 |

---

## Three Outcomes, Always

**Pre-filter:** Contacts already correctly associated with a child company are automatically skipped — no wasted processing.

For contacts that enter the routing logic, every one ends up in one of three buckets:

| Bucket | What happens | Who handles it |
|--------|-------------|---------------|
| **Auto-routed** | Contact automatically associated with the correct child company | System (no human needed) |
| **Kept on parent** | Contact stays on the parent record — they actually work there | No action needed |
| **Sent to rep** | Contact lands in a review queue for manual routing | Rep reviews and decides |

The goal is to maximize auto-routed contacts while never making a wrong association. When in doubt, we send to a human.
