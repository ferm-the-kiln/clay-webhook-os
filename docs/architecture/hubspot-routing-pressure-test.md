# Pressure Test: HubSpot Parent-Child Contact Routing

> Strategy doc — stress-tests every assumption, edge case, and failure mode in the LinkedIn URL routing architecture.
> Created: 2026-03-11

## Context
The solution uses **LinkedIn Company URL** as the source of truth to route contacts away from parent companies (e.g., @nfl.com) and to the correct child/subsidiary. Clay detects mismatches, HubSpot associates + assigns owners via decision tree (Region → Type → Segment).

---

## 1. LinkedIn Company URL — Is It Actually Deterministic?

### The Assumption
"Every contact's LinkedIn profile has a company URL that uniquely identifies where they work."

### Where It Breaks

| Scenario | Frequency | Impact | Mitigation |
|----------|-----------|--------|------------|
| Contact has no LinkedIn profile | ~5-15% of B2B | Routing fails silently | Fallback: use email domain + manual review queue |
| LinkedIn shows old employer (job change lag) | ~3-5% | Wrong child association | Time-bound: only trust if LinkedIn "current" role. Clay can check start date |
| Contact's LinkedIn shows parent company, not subsidiary | Common for big enterprises | Routes to parent (the problem we're solving) | **This is the hardest edge case** — see below |
| Freelancer/consultant with @client.com email | Rare for enterprise | Wrong association | Low risk — these contacts usually have their own company on LinkedIn |
| LinkedIn URL format varies (slug changes, redirects) | Occasional | Dedup guard fails | **Normalize aggressively** — always resolve to canonical URL |

### THE BIG HOLE: LinkedIn Shows Parent, Not Subsidiary
A VP at Kansas City Chiefs might list "NFL" as their company on LinkedIn (not "Kansas City Chiefs"). In this case:
- Email domain: @nfl.com → parent
- LinkedIn company: linkedin.com/company/nfl → parent
- **Both signals point to parent. Our system has no way to detect this is wrong.**

**Verdict:** LinkedIn Company URL is *better* than email domain alone, but it's NOT a silver bullet for contacts who list the parent org on their LinkedIn.

**Possible mitigations:**
1. LinkedIn job title + company name text matching (e.g., "VP, Kansas City Chiefs" but company = NFL)
2. Manual review queue for contacts where LinkedIn URL = parent's LinkedIn URL
3. Accept this as a known gap — these contacts get parent association (same as today)

---

## 2. Dedup Guard Stress Test

### Race Condition: Two Contacts, Same New Subsidiary, Same Second
```
Contact A (Chiefs) ─→ Clay detects "new_child" ─→ HubSpot creates "Kansas City Chiefs"
Contact B (Chiefs) ─→ Clay detects "new_child" ─→ HubSpot creates "Kansas City Chiefs" (DUPLICATE!)
```

**Current mitigation:** HubSpot custom code searches for existing company by LinkedIn URL before creating.

**But what if:**
- HubSpot's search API is **eventually consistent** — Contact B's search runs before Contact A's company record is indexed
- Two workflow executions overlap within HubSpot's ~1-2 second indexing lag

**Verdict:** Real risk. HubSpot search API has a known indexing delay.

**Hardened fix options:**
1. **Mutex pattern:** Use a "creation pending" flag on a shared property. First workflow sets flag, second sees flag and waits/retries
2. **Batch dedup:** Run a nightly dedup job that merges any duplicate child companies created that day
3. **Clay-side dedup:** Clay maintains the canonical list. If Clay already tagged a company as "pending creation," subsequent contacts for the same LinkedIn URL get queued, not duplicated
4. **Accept + merge:** Let duplicates happen, run weekly cleanup. Pragmatic for low-frequency events.

**Recommendation:** Option 4 (accept + merge) for Phase 1. Frequency is low — two contacts from the same *brand new* subsidiary arriving within seconds is unlikely. Add monitoring alert for duplicate LinkedIn URLs across companies.

---

## 3. LinkedIn URL Normalization — The Devil in the Details

LinkedIn URLs come in many flavors:
```
https://www.linkedin.com/company/nfl/
https://linkedin.com/company/nfl
http://www.linkedin.com/company/nfl
https://www.linkedin.com/company/nfl/about
https://www.linkedin.com/company/12345/        ← numeric ID
https://www.linkedin.com/company/nfl-football   ← old slug after rename
```

**If Clay stores one format and HubSpot has another, the lookup FAILS silently.**

**Required normalization rules:**
1. Lowercase everything
2. Strip protocol (http/https)
3. Strip www
4. Strip trailing slash
5. Strip path after company slug (remove /about, /jobs, etc.)
6. Resolve numeric IDs to slug (or store both in lookup table)
7. Handle redirected/renamed slugs

**Verdict:** This is a "quiet killer." Must be tested with real data from Sean's HubSpot before going live. Build a normalization function that runs in both Clay and HubSpot custom code.

---

## 4. Opted-Out Domains — What Bypasses It?

### Known Bypasses
1. **HubSpot Forms** with company properties → auto-associates despite opted-out list
2. **Integrations** (Salesforce sync, Zapier, etc.) that create contacts → may bypass
3. **Manual association** by reps → overrides everything (this is fine)
4. **Contact import** via CSV → may auto-associate based on domain

### What About Existing Mis-Associations?
The current solution handles **new contacts going forward**. But what about the 1000+ contacts already mis-associated?

**Options:**
1. **Retroactive cleanup:** Run a one-time Clay table that checks all contacts under pilot parents → re-associate based on LinkedIn URL
2. **Ignore historical:** Only fix going forward. Accept existing mess.
3. **Gradual cleanup:** As contacts are touched (email opened, form submitted), re-run routing

**Recommendation:** Build the retroactive cleanup as Phase 4.5. It's the same logic as the forward-looking flow, just batch-applied.

---

## 5. Decision Tree Edge Cases

### Current Tree:
```
Region = APAC? → APAC owner
Type = Partner? → Partnership team
Industry → Segment → Segment owner
```

### What happens when:

| Scenario | Current Behavior | Problem? |
|----------|-----------------|----------|
| APAC + Partner | Routes to APAC (first match wins) | Maybe wrong — Partner team might want ownership regardless of region |
| Industry not in mapping table | No segment → no owner assigned | Contact falls through. **Must have a default/catch-all** |
| Child company has no Industry set | Can't map to segment | Same as above — needs default |
| Multiple segments per industry | Ambiguous routing | Sean's mapping must be 1:1, not 1:many |
| New subsidiary, no Type set yet | Defaults to "Sales Prospect" | Correct behavior (per PROJECT.md) |
| Contact changes companies | Old association persists | No re-routing mechanism unless contact re-enters flow |

**Critical question for Sean:** What's the priority order when multiple rules match? Is it always Region → Type → Segment, or are there exceptions?

---

## 6. Scale Concerns

| Dimension | Current | At Scale | Risk |
|-----------|---------|----------|------|
| Opted-out domains | 10-20 pilot | 100+ parents x avg 2 domains = 200+ | HubSpot UI doesn't scale for manual entry. Need API or bulk method |
| Clay lookup table rows | ~100-200 children | 1000+ across all parents | Clay handles this fine |
| HubSpot workflow executions | Pilot volume | All inbound contacts hit routing workflow | Ops Hub has execution limits per plan tier. Check with Sean |
| Custom code timeout | N/A | 20 seconds per execution | Dedup guard search must complete in <20s. Fine for single API call |
| New parent detection | Manual | Automated (Phase 5) | How often does Clay scan? Daily? Real-time? |

---

## 7. Monitoring & Observability

**The current plan has NO monitoring.** This is a gap.

Must-have alerts:
1. **Duplicate company alert** — daily check for companies sharing a LinkedIn URL
2. **Unrouted contact alert** — contacts that hit the workflow but got no owner assigned
3. **Fallback rate** — % of contacts where LinkedIn URL was missing (went to manual queue)
4. **Association override rate** — contacts re-associated by a rep within 24h of auto-routing (indicates bad routing)

---

## 8. What If Clay Enrichment Returns Wrong Data?

Clay's LinkedIn enrichment isn't perfect. Known failure modes:
- Returns parent company URL instead of subsidiary (the irony)
- Returns a different company entirely (name collision)
- Returns null (no match found)
- Returns a personal LinkedIn URL instead of company page

**Mitigation:** Confidence scoring on Clay enrichment. If enrichment confidence is low, flag for manual review instead of auto-routing.

---

## Summary: Verdict on the Architecture

### What's SOLID:
- LinkedIn URL as primary signal is significantly better than email domain alone
- Dedup guard concept is sound
- Architecture split (Clay = detection, HubSpot = association) is correct
- Decision tree is simple and maintainable

### What Needs Hardening Before Go-Live:
1. **URL normalization function** — build and test with real data (HIGH priority)
2. **Fallback for missing LinkedIn data** — manual review queue (MEDIUM priority)
3. **Monitoring/alerting** — at minimum, duplicate detection + unrouted contacts (MEDIUM)
4. **Default/catch-all in decision tree** — for unmapped industries (HIGH priority)

### What's an Acceptable Gap for Phase 1:
- Contacts who list parent on LinkedIn (no data can fix this without NLP on job title)
- Race condition duplicates (low frequency, weekly cleanup is fine)
- Historical mis-associations (Phase 4.5 retrofit)
- Form bypass of opted-out domains (document and accept)

### Key Questions for Sean Before Proceeding:
1. **Priority order:** Region → Type → Segment is strict? Or are there exceptions?
2. **Catch-all owner:** Who gets contacts that don't match any segment?
3. **Historical cleanup:** Do you want retroactive re-association or forward-only?
4. **Monitoring access:** Can we create a HubSpot report/dashboard for routing health?
5. **Industry coverage:** Is the mapping table exhaustive, or will there be gaps?
