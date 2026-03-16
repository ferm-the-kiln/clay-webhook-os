# HubSpot Parent-Child — Two Proposals

**Prepared for:** Sean Graham & 12 Labs Team
**Date:** March 11, 2026
**From:** Fermin

---

## The Problem

When contacts share a parent company email domain (e.g., @nfl.com), HubSpot auto-associates them to the parent company. But many of these contacts actually work for subsidiaries or child companies (e.g., Kansas City Chiefs, Dallas Cowboys). This means:

- Contacts sitting on the wrong company record
- Reps not knowing who actually belongs to which team/subsidiary
- Owner assignment based on incorrect company data

We're solving this in two stages: clean up what's already there, then change how new contacts get routed going forward.

---

---

# Proposal 1: Migration — Clean Up Existing Records

**Goal:** Take what's currently in HubSpot and move companies and contacts into the correct parent-child associations.

---

## Step 1: Discovery & Flagging

We use Claude and Clay together to analyze existing HubSpot records and flag which companies should be parents, which should be children, and which should be merged.

**How we detect it:**

| Signal | What It Tells Us |
|--------|-----------------|
| **Company Type** | Is this a subsidiary, division, or brand? |
| **Segment** | Enterprise vs. mid-market — helps determine if it warrants its own record |
| **Company Size** | Employee count signals whether a child is big enough to stand alone |
| **Unique Domain** | Does the child have its own email domain (e.g., @chiefs.com vs. @nfl.com)? |
| **Unique LinkedIn URL** | Does the child have its own LinkedIn company page? Strongest signal. |

**What Claude does:**

For each parent company, Claude analyzes its contacts and cross-references LinkedIn data, job titles, and company names to identify child companies grouped under that parent. It outputs a recommendation for each: **create as child**, **merge with parent**, or **needs team decision**.

## Step 2: Google Sheet for Team Review

The output is a shared Google Sheet — one row per company — with recommendations and conflict highlights.

**Example output (NFL):**

| Company | Contacts | Detection Method | Recommendation | Conflicts | Team Decision |
|---------|----------|-----------------|---------------|-----------|---------------|
| Kansas City Chiefs | 12 | LinkedIn URL + job titles | Create as child | None | *(team fills in)* |
| Dallas Cowboys | 8 | LinkedIn URL + unique domain | Create as child | 2 contacts owned by different reps | |
| NFL Films | 3 | LinkedIn URL | Team decision | Small entity — merge or keep? | |
| NFL Network | 2 | Job title only | Team decision | Currently owned by media team rep | |

**What gets highlighted as a conflict:**

- **Ownership conflicts** — Two reps own contacts that will move to the same child company. Who gets ownership?
- **Merge conflicts** — A company marked for merging has contacts with activity history on both records. Which record survives?
- **Ambiguous entities** — Small divisions where it's unclear if they need their own record (e.g., NFL Films — 3 contacts, is it worth a separate company?)

The sheet includes a **Notes** column for the team to add context only they would know. The system recommends — humans decide.

## Step 3: Automated Execution

Once the team returns the approved Google Sheet, Clay handles all the HubSpot updates automatically:

1. **Creates child company records** — via HubSpot API, with parent-child association set
2. **Re-associates contacts** — moves contacts from the parent to the correct child company
3. **Handles merges** — for companies marked "merge," consolidates records and preserves activity history
4. **Builds a mapping table** — a running list of parent → child LinkedIn URL mappings that Proposal 2 uses for ongoing routing

**No manual HubSpot work required.** The team reviews and decides, Clay executes.

**Dedup protection during execution:**

When creating child companies at scale, duplicates can slip through. We prevent this with three checks:

1. **Before creating** — Clay checks its mapping table and searches HubSpot. If the company already exists, skip creation and just associate the contact.
2. **After creating** — Clay verifies no duplicate was just created by another concurrent process.
3. **Weekly scan** — Automated script catches anything that slipped through the first two checks.

## Edge Cases

**The NFL problem:** A contact lists "NFL" on LinkedIn even though they work for the Kansas City Chiefs. Their job title says "Director of Entertainment Teams - Kansas City Chiefs."

- **For migration:** Claude catches these via job title analysis and flags them in the Google Sheet.
- **Pragmatic default:** If detection is uncertain, the contact stays on the parent record. The job title is visible to reps, so they can manually re-associate if needed.

## What We Need From the Team (Proposal 1)

1. **List of parent companies** to start the discovery analysis (or we can pull the top companies by child count from HubSpot)
2. **Time to review** the Google Sheet and make approve/merge/flag decisions per row
3. **Ownership rules** — when two reps own contacts moving to the same child, who gets it?

## Timeline (Proposal 1)

| Phase | What | Effort |
|-------|------|--------|
| Discovery | Claude analyzes parents, outputs Google Sheet | ~1 week |
| Team Review | Team reviews, marks decisions, resolves conflicts | Team's pace |
| Execution | Clay creates associations and merges via HubSpot API | ~1 week |

---

---

# Proposal 2: Enrichment Process — Route New Contacts Correctly

**Goal:** Change the current enrichment process so that when new contacts get added to HubSpot, they automatically land on the correct child or parent company — not just wherever the email domain points.

---

## The Problem Today

Contact-to-company association currently relies on:
- Email domain (unreliable for parent-child — @nfl.com goes to NFL, not Kansas City Chiefs)
- Company info from imported spreadsheets (may be outdated or generic)

This means every new contact under a parent-child structure risks landing on the wrong company.

## The Fix: LinkedIn First, Email as Fallback

When a new contact enters the system, Clay enriches them and routes based on **LinkedIn data as the primary signal**, with work email as a fallback.

**Priority order:**

| Priority | Signal | Why |
|----------|--------|-----|
| **1st** | **LinkedIn Company URL** | Exact match against the mapping table. Most reliable — no fuzzy matching needed. |
| **2nd** | **LinkedIn Company Name** | If the LinkedIn URL doesn't match a known child, check the company name. Catches subsidiaries not yet in our mapping table. |
| **Fallback** | **Work Email Domain** | Only used when LinkedIn data is missing or inconclusive. This is the current behavior, but now it's intentionally last — not the default. |

## How Routing Works

```
New contact enters HubSpot
  |
  |-- Has LinkedIn Company URL?
  |     |-- Matches a known child in mapping table?
  |     |     YES --> Associate to that child company
  |     |     NO  --> Check LinkedIn company name...
  |     |
  |     |-- LinkedIn company name matches a known child?
  |           YES --> Associate to that child company
  |           NO  --> Check work email domain (fallback)
  |
  |-- No LinkedIn data?
  |     |-- Has work email?
  |     |     |-- Email domain matches a known child domain?
  |     |           YES --> Associate to that child company
  |     |           NO  --> Keep on parent (email = parent domain)
  |     |
  |     |-- No work email either?
  |           --> Flag for manual review
  |
  |-- Confidence too low on any match?
        --> Flag for rep review (task created in HubSpot)
```

## Every Scenario

| LinkedIn | Email | What Happens |
|----------|-------|-------------|
| Points to Chiefs (URL match) | @chiefs.com | Auto-route to Chiefs |
| Points to Chiefs (URL match) | @nfl.com | Auto-route to Chiefs (LinkedIn wins) |
| Points to Chiefs (name match) | @nfl.com | Auto-route to Chiefs |
| Points to NFL | @chiefs.com | Auto-route to Chiefs (email fallback differentiates) |
| Points to NFL | @nfl.com | Keep on NFL (both agree — they actually work at HQ) |
| Points to NFL + title mentions Chiefs | @nfl.com | Flag for rep review |
| Missing | @chiefs.com | Auto-route to Chiefs (email fallback) |
| Missing | @nfl.com | Keep on parent (can't differentiate) |
| Missing | @gmail.com | Flag for rep review (personal email) |

## What This Looks Like in Clay

| Column | Purpose |
|--------|---------|
| `linkedin_company_url` | From Clay enrichment — primary routing signal |
| `linkedin_company_name` | Company name from contact's current LinkedIn experience |
| `work_email` | Contact's work email — fallback signal |
| `email_domain` | Extracted from work email (formula) |
| `is_personal_email` | Gmail/Yahoo/etc. check (formula) |
| `mapping_table_match` | Lookup against parent-child mapping table |
| `routing_decision` | Auto-route / Keep on parent / Flag for review (formula) |
| `routing_confidence` | High / Medium / Low based on which signal matched |
| `job_title` | For edge case detection (title mentions child company) |

## Ongoing Monitoring

Once routing is live, two automations keep it honest:

1. **Mismatch alert** — When a contact's job title contains a known child company name but they're associated with the parent → HubSpot creates a task for the rep to review.

2. **Re-association audit** — Weekly report showing contacts whose company association was manually changed by a rep. High volume of manual changes = signal that routing needs tuning for that parent.

## What We Need From the Team (Proposal 2)

1. **Confirm** that Clay currently pushes LinkedIn Company URL to HubSpot contact properties (or we add this)
2. **Industry-to-Segment mapping** — needed for owner assignment after routing
3. **Pilot parent company** — which parent-child group should we test the new enrichment flow on first?

## Timeline (Proposal 2)

| Phase | What | Effort |
|-------|------|--------|
| Build routing logic | Clay columns + formulas + mapping table lookup | ~1 week |
| Pilot test | Run on one parent-child group, verify accuracy | 3-5 days |
| Scale | Roll out to all parent companies | ~1 week |
| Monitoring | Mismatch alerts + weekly audit | 2-3 days |

---

---

## How the Two Proposals Connect

Proposal 1 creates the **mapping table** (parent → child LinkedIn URL mappings) that Proposal 2 uses for ongoing routing. They're designed to run in sequence:

1. **Proposal 1 first** — clean up existing records, build the mapping table
2. **Proposal 2 second** — change the enrichment process so new contacts route correctly from day one

The mapping table is the bridge. As new child companies are discovered (either through Proposal 1's migration or organically), they get added to the table and Proposal 2 automatically picks them up.

---

## Next Steps

1. Align on both proposals
2. Start Proposal 1 with the top parent companies (we can pull these from HubSpot or the team provides a list)
3. Team reviews the Google Sheet, resolves conflicts
4. Clay executes the approved migrations
5. Build Proposal 2 routing using the mapping table from step 4
6. Pilot on one parent-child group, then scale
