# Phase 1 Runbook — HubSpot + Clay Setup

**Project:** HubSpot Parent-Child Contact Routing
**Client:** 12 Labs
**Phase:** 1 — Setup & Prerequisites
**Status:** IN PROGRESS

---

## Quick Reference

| Script | What it does | When to run |
|--------|-------------|-------------|
| `01-audit-properties.sh` | Check existing properties | Day 1, before anything else |
| `01b-find-pilot-parents.sh` | Find top 20 parents by child count | Day 1-2, if Sean hasn't responded |
| `01c-verify-linkedin-data.sh` | Check if LinkedIn URLs exist on child companies | Day 1 |
| `02-create-properties.sh` | Create HubSpot property groups + custom properties | Day 1-2, after audit |
| `03-check-domain-aliases.sh` | Find alias domains for pilot parents | Day 2-3, before opted-out list |
| `04-extract-child-companies.sh` | Extract all child companies as CSV | Day 3-5 |

**Environment variable required for all scripts:**
```bash
export HUBSPOT_ACCESS_TOKEN="pat-na1-xxxxxxxxxxxx"
```

---

## Wave 1: Discovery & Verification (Day 1)

### Task 1.1: Audit Existing HubSpot Properties
**Type:** Automated (script)
**Status:** [ ] Not started | [ ] In progress | [x] Complete

```bash
export HUBSPOT_ACCESS_TOKEN="pat-na1-xxxxxxxxxxxx"
bash scripts/hubspot-setup/01-audit-properties.sh
```

**Decision Gate:** Record the result here before proceeding to Wave 2.

| Property | Object | Status | Notes |
|----------|--------|--------|-------|
| `linkedin_company_url` | Contacts | | |
| `linkedin_company_url` | Companies | | |
| `routing_tag` | Contacts | | |

**Canonical property name chosen:** `_____________________`
(If an existing variant was found, write its name here. Use THIS name everywhere downstream.)

---

### Task 1.2: Get Pilot Parent List from Sean
**Type:** Human (message Sean)
**Status:** [ ] Not started | [ ] Sent | [ ] Received | [x] Blocked — waiting on Sean

**Message to send Sean:**
> "Hey Sean — for the parent-child routing pilot, can you give me the top 10-20 parent company domains that cause the most mis-routing? (e.g., nfl.com, amazon.com). These are the ones where contacts get associated to the parent instead of the correct subsidiary."

**Fallback (if Sean doesn't respond within 2 days):**
```bash
bash scripts/hubspot-setup/01b-find-pilot-parents.sh
# Then look up domain names for top 20 parent IDs in HubSpot
```

**Pilot domain list received:**
```
(paste domains here, one per line)
```

---

### Task 1.3: Verify LinkedIn URL Data on Child Companies
**Type:** Automated (script)
**Status:** [ ] Not started | [ ] In progress | [ ] Complete

```bash
bash scripts/hubspot-setup/01c-verify-linkedin-data.sh
```

**Result:**
- [ ] LinkedIn URLs populated on most children → proceed directly to Task 4.2
- [ ] LinkedIn URLs mostly missing → Task 4.2b (Clay enrichment) needed before mapping table

---

### Task 1.4: Confirm HubSpot API Access
**Type:** Manual verification
**Status:** [ ] Not started | [ ] In progress | [ ] Complete

**Required scopes on Private App:**
- `crm.schemas.contacts.write`
- `crm.schemas.companies.write`
- `crm.objects.contacts.read`
- `crm.objects.companies.read`

**Verification:**
```bash
curl -s https://api.hubapi.com/crm/v3/properties/contacts \
  -H "Authorization: Bearer $HUBSPOT_ACCESS_TOKEN" | python3 -c "
import sys, json; d=json.load(sys.stdin)
if 'results' in d:
    print(f'Access confirmed. Total contact properties: {len(d[\"results\"])}')
else:
    print('ERROR:', d)
"
```

**Result:** ___________________________________________

---

## Wave 2: Create HubSpot Properties (Day 1-2)

**Dependency:** Tasks 1.1 and 1.4 must be complete first.

### Task 2.1 + 2.2: Create Property Groups and Custom Properties
**Type:** Automated (script)
**Status:** [ ] Not started | [ ] In progress | [ ] Complete

**IMPORTANT:** Skip if audit (Task 1.1) showed properties already exist.

```bash
# Dry run first — no API calls
DRY_RUN=true bash scripts/hubspot-setup/02-create-properties.sh

# If dry run looks right, run for real
bash scripts/hubspot-setup/02-create-properties.sh
```

**Verification (HubSpot UI):**
1. Go to Settings → Properties
2. Filter by: Object = Contacts, Group = Contact Routing
   - [ ] `linkedin_company_url` visible
   - [ ] `routing_tag` visible
3. Filter by: Object = Companies, Group = Contact Routing
   - [ ] `linkedin_company_url` visible

---

## Wave 3: Opted-Out Domains (Day 2-3)

**Dependency:** Pilot domain list from Task 1.2.

### Task 3.1: Add Pilot Domains to Opted-Out List
**Type:** MANUAL — HubSpot UI only (no API available)
**Status:** [ ] Not started | [ ] In progress | [ ] Complete

**Step 1 — Check for domain aliases:**
```bash
# Replace with your actual pilot domains
bash scripts/hubspot-setup/03-check-domain-aliases.sh nfl.com amazon.com
```

**Step 2 — Add each domain in HubSpot UI:**
1. HubSpot → Settings (gear icon)
2. Objects → Companies
3. Under "Automatic association" section
4. Click "Exclude a domain from automatic association"
5. Enter domain → Save
6. Repeat for each domain (including aliases found in step 1)

**Domains added to opted-out list:**
```
[ ] _____________________
[ ] _____________________
[ ] _____________________
[ ] _____________________
[ ] _____________________
```

---

### Task 3.2: Smoke-Test Opted-Out Domains
**Type:** MANUAL — HubSpot UI
**Status:** [ ] Not started | [ ] In progress | [ ] Complete

**Steps:**
1. In HubSpot, create a test contact:
   - Email: `test-routing-delete-me@{pilot_domain}` (e.g., `test-routing-delete-me@nfl.com`)
   - First name: `Test`
   - Last name: `Routing`
2. Open the contact record
3. Check the "Associated companies" section
4. Expected: **empty** (or only manual associations, no auto-association to NFL parent)
5. If it IS auto-associated → domain may not have been saved correctly. Check Settings again.
6. Delete the test contact after verification

**Pilot domain tested:** _____________________
**Result:** [ ] NOT auto-associated (correct) | [ ] WAS auto-associated (check settings)

---

### Task 3.3: Audit HubSpot Forms for Bypass Risk
**Type:** MANUAL — HubSpot UI
**Status:** [ ] Not started | [ ] In progress | [ ] Complete

**Steps:**
1. HubSpot → Marketing → Forms
2. For each active form, check if it includes company properties

**Forms with company properties (bypass risk):**
| Form Name | Company Properties | Mitigation |
|-----------|-------------------|------------|
| | | |

**Note:** Forms that collect company name/domain can bypass the opted-out domain list
because they trigger company creation from explicit form data, not email auto-association.

---

## Wave 4: Clay Mapping Table (Day 3-5)

**Dependency:** Wave 2 complete (properties exist), Task 1.3 complete (LinkedIn data verified).

### Task 4.1: Create Clay Lookup Table Structure
**Type:** MANUAL — Clay UI (no API for table creation)
**Status:** [ ] Not started | [ ] In progress | [ ] Complete

**Steps in Clay:**
1. Open Clay workspace
2. Create new table: **"LinkedIn URL → Company ID Mapping"**
3. Add columns:
   - `linkedin_company_url` (Text) — **this is the match key**
   - `hubspot_company_id` (Text)
   - `company_name` (Text)
   - `parent_company_name` (Text)
   - `parent_domain` (Text)
4. Set `linkedin_company_url` as the lookup key

**Clay table ID/URL:** _____________________

---

### Task 4.2: Extract Child Company Data from HubSpot
**Type:** Automated (script)
**Status:** [ ] Not started | [ ] In progress | [ ] Complete

```bash
# Using parent IDs from HubSpot (get from 01b-find-pilot-parents.sh output
# or from Sean's list + manual ID lookup)
bash scripts/hubspot-setup/04-extract-child-companies.sh 12345 67890 11111

# Or from a file (one ID per line):
bash scripts/hubspot-setup/04-extract-child-companies.sh --file parent-ids.txt
```

**Output:** `scripts/hubspot-setup/output/child-companies.csv`

**Result:**
- Total child companies extracted: _____
- Missing LinkedIn URLs: _____
- [ ] All have LinkedIn URLs → proceed to Task 4.3
- [ ] Some missing → run Task 4.2b first

---

### Task 4.2b: (If needed) Enrich Child Companies with LinkedIn URLs
**Type:** MANUAL — Clay UI
**Status:** [ ] N/A | [ ] Not started | [ ] In progress | [ ] Complete

**Only needed if Task 1.3 or 4.2 showed missing LinkedIn URLs.**

**Steps:**
1. Filter the CSV for rows with empty `linkedin_company_url`:
   ```bash
   grep "^," scripts/hubspot-setup/output/child-companies.csv > needs-enrichment.csv
   ```
2. Import `needs-enrichment.csv` into a Clay table
3. Add LinkedIn enrichment column (Clay's built-in company enrichment)
4. Run enrichment (~$0.10-0.20 per row depending on plan)
5. Export enriched data with LinkedIn URLs
6. Merge back into the main CSV

---

### Task 4.3: Populate Clay Mapping Table
**Type:** MANUAL — Clay UI (CSV import)
**Status:** [ ] Not started | [ ] In progress | [ ] Complete

**Pre-import checklist:**
- [ ] All LinkedIn URLs follow format: `https://www.linkedin.com/company/{slug}`
- [ ] No trailing slashes on URLs
- [ ] All URLs are lowercase
- [ ] No duplicate `linkedin_company_url` values in the CSV

**Import steps:**
1. Open the mapping table created in Task 4.1
2. Import CSV: `scripts/hubspot-setup/output/child-companies.csv`
3. Map columns (should match automatically)
4. Spot-check 5 rows against HubSpot for accuracy

**Spot-check results:**
| LinkedIn URL | Expected Company ID | Actual in Clay | Match? |
|-------------|---------------------|----------------|--------|
| | | | |
| | | | |
| | | | |

---

## Wave 5: Sean's Deliverables (BLOCKED — Async)

### Task 5.1: Get Industry → Segment Mapping from Sean
**Status:** BLOCKED — waiting on Sean Graham
**Expected format:**

| Industry (HubSpot) | Segment (12 Labs) |
|-------------------|-------------------|
| Broadcasting | M&E |
| Film Production | M&E |
| SaaS | SaaS/Emerging Verticals |
| Artificial Intelligence | SaaS/Emerging Verticals |

**When received:** Store the mapping in `docs/industry-segment-mapping.md`.
This will be used in Phase 3 (HubSpot decision tree workflow).

**Date received:** _____________________

---

### Task 5.2: Confirm LinkedIn URL Field Flow
**Status:** BLOCKED — waiting on Sean Graham

**Question for Sean:**
> "Does Clay currently push the LinkedIn Company URL into HubSpot as a contact property? If yes, what's the exact HubSpot property name it maps to?"

**Sean's answer:**
- [ ] YES — field name: `_____________________`
- [ ] NO — need to configure Clay → HubSpot push to include this field

**Date confirmed:** _____________________

---

## Phase 1 Completion Checklist

Run through this before declaring Phase 1 done:

- [ ] **Properties exist:** `linkedin_company_url` on Contacts + Companies, `routing_tag` on Contacts
- [ ] **Groups exist:** All properties are in the "Contact Routing" group in HubSpot UI
- [ ] **Opted-out domains active:** Pilot domains listed in HubSpot Settings → Objects → Companies
- [ ] **Smoke test passed:** Test contact with pilot domain email NOT auto-associated to parent
- [ ] **Form audit done:** Bypass risk forms documented
- [ ] **Mapping table populated:** Clay table has rows for all child companies under pilot parents
- [ ] **LinkedIn URLs normalized:** 5-entry spot-check passed
- [ ] **No duplicate properties:** Only ONE `linkedin_company_url` per object type
- [ ] **Scripts output archived:** `scripts/hubspot-setup/output/` backed up

**Wave 5 (Sean's deliverables):** Does NOT block Phase 2 start. Resolves when Sean responds.
Industry → Segment mapping is needed for Phase 3, not Phase 2.

---

## Troubleshooting

### "Property already exists with a different field type"
If audit found `linkedin_company_url` as a `url` type (not `text`):
- The `url` fieldType auto-prepends `https://` when saving, which can corrupt lookup matching.
- **Option A (preferred):** Create a new property `routing_linkedin_company_url` with `fieldType: text`.
  Use this new name in all downstream configuration.
- **Option B:** Leave existing property, but test thoroughly — some URL normalization is fine.
- Document your choice here: _____________________

### "Can't find hs_parent_company_id on any companies"
- The parent-child relationship in your HubSpot instance may use a different association type.
- Check in HubSpot UI: open a known child company, look at "Related companies" and note the label.
- Try the v4 associations API to enumerate all association types: `GET /crm/v4/associations/{fromObjectType}/{toObjectType}/labels`

### "Opted-out domain not preventing auto-association"
- Verify the domain was entered EXACTLY (no typos, no http://)
- Check HubSpot → Settings → Objects → Companies — confirm the domain appears in the list
- Forms that collect company data explicitly can still create associations. Check Task 3.3.

### "HubSpot Private App missing scopes"
- Go to HubSpot → Settings → Integrations → Private Apps
- Open the relevant app → Scopes tab
- Add missing scopes, regenerate token
- Update `HUBSPOT_ACCESS_TOKEN` with the new token

---

## Notes & Decisions

Use this section to record any decisions made during execution.

| Date | Decision | Rationale |
|------|----------|-----------|
| | | |
