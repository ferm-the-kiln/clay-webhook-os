# Phase 1: Setup & Prerequisites - Research

**Researched:** 2026-03-10
**Domain:** HubSpot CRM APIs + Clay Data Platform
**Confidence:** HIGH (HubSpot APIs well-documented, Clay UI-only for some operations)

## Summary

Phase 1 involves preparing HubSpot and Clay for the parent-child contact routing workflow. The core work is: (1) creating three custom HubSpot properties via the Properties API v3, (2) configuring opted-out domains via the HubSpot UI (no API available), (3) building a LinkedIn URL to Company ID lookup table in Clay, and (4) identifying pilot parent companies using the HubSpot Search API.

The HubSpot Properties API v3 is straightforward and well-documented. The biggest surprise is that opted-out domain management is **UI-only** -- there is no API endpoint to add/remove domains from the exclusion list. This means that task must be done manually through HubSpot Settings. Clay lookup tables also require manual setup through the Clay UI (table creation, webhook URL generation), but can be populated via CSV import or webhook pushes.

**Primary recommendation:** Start with the three HubSpot property creations (fully automatable via API), then manually configure opted-out domains and Clay lookup table structure. The Industry-to-Segment mapping is blocked on Sean and should not gate other work.

## Standard Stack

### Core (APIs and Tools)

| Tool | Version/API | Purpose | Why Standard |
|------|-------------|---------|--------------|
| HubSpot Properties API | v3 | Create custom properties on Contacts and Companies | Official CRM API, REST-based |
| HubSpot Search API | v3 | Query companies to find pilot parents | Filter/sort companies by properties |
| HubSpot Associations API | v4 | Query parent-child company relationships | Required for reading child associations |
| Clay Lookup Tables | Current | LinkedIn URL to Company ID mapping | Native Clay feature for cross-table enrichment |
| Clay CSV Import | Current | Bulk populate lookup table | Fastest way to seed initial mapping data |

### Supporting

| Tool | Purpose | When to Use |
|------|---------|-------------|
| HubSpot Property Groups API | v3 | Create custom group for routing properties | Optional: organizes properties under a dedicated group |
| Clay Webhooks | Push data into tables | Future: auto-update lookup table when HubSpot creates new children |
| HubSpot Companies API | v3 | Read company records, get LinkedIn URLs | Extracting existing data for mapping table |

### Not Needed

| Tool | Why Not |
|------|---------|
| HubSpot v2 APIs | Deprecated, v3 covers all needed operations |
| External enrichment APIs | Clay already enriches LinkedIn data |
| Custom code actions | Phase 1 is setup only, no workflow logic yet |

## Architecture Patterns

### HubSpot Property Design

Three properties to create:

```
Contacts:
  linkedin_company_url    → type: string, fieldType: text
  routing_tag             → type: string, fieldType: text

Companies:
  linkedin_company_url    → type: string, fieldType: text
```

**IMPORTANT: Use `type: string` + `fieldType: text` for LinkedIn URLs, NOT `fieldType: url`.**

Rationale: The `url` fieldType auto-prepends `https://` and applies URL validation that can reject valid LinkedIn URL variations. Using `text` gives full control over the stored value and avoids validation edge cases. The URL will be used as a **lookup key**, not as a clickable link, so text is the correct choice.

### Property Group Strategy

Create a dedicated property group for routing properties:

```
Group name: "contact_routing"
Group label: "Contact Routing"
```

This keeps routing properties organized separately from standard contact/company info, making them easy to identify in the HubSpot UI and in API queries.

### routing_tag Value Format

```
parent              → Contact matches parent company domain, no mismatch
child:{hubspot_id}  → Contact matched to existing child company
new_child           → Mismatch detected, no child found in lookup
```

This is a free-text field (not an enumeration) because `child:{id}` values are dynamic. The field is set by Clay before pushing to HubSpot.

### Clay Lookup Table Structure

```
Table name: "LinkedIn URL → Company ID Mapping"

Columns:
  linkedin_company_url    → Text (match key, normalized)
  hubspot_company_id      → Text (HubSpot Company ID)
  company_name            → Text (human-readable reference)
  parent_company_name     → Text (which parent this child belongs to)
  parent_domain           → Text (the shared email domain)
```

Match key: `linkedin_company_url` (normalized to lowercase, trailing slashes stripped)

### Pilot Parent Identification Strategy

Since HubSpot Search API cannot sort by "number of child companies" or "number of associated contacts" directly, the approach is:

1. Use HubSpot Search API to find all companies that HAVE the `hs_parent_company_id` property set (these are children)
2. Aggregate by parent company ID client-side
3. Rank parents by number of children
4. Cross-reference with known problematic domains (nfl.com, amazon.com, etc.)

Alternative (faster for pilot): Sean likely already knows the top 10-20 problematic parent domains from support tickets and rep complaints. Ask Sean first before scripting.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Domain exclusion management | Custom workflow to intercept associations | HubSpot opted-out domains (UI setting) | Native feature, tested, maintained by HubSpot |
| LinkedIn URL enrichment | Scraping or API calls to LinkedIn | Clay's built-in LinkedIn enrichment | Clay already does this in their enrichment flow |
| Parent-child company hierarchy | Custom property tracking parent IDs | HubSpot native parent-child associations | Built-in, definition IDs 13/14, read-only `hs_parent_company_id` |
| Lookup table matching | Custom database or API service | Clay Lookup Rows enrichment | Native Clay feature, handles matching/normalization |
| Company dedup by domain | Custom dedup logic | HubSpot's `domain` as unique identifier | HubSpot uses domain as primary company dedup key |

**Key insight:** Phase 1 is pure setup -- creating properties, configuring settings, populating lookup data. There is zero custom code to write. Everything uses native HubSpot and Clay features.

## Common Pitfalls

### Pitfall 1: URL Field Type for LinkedIn URLs
**What goes wrong:** Using `fieldType: "url"` auto-prepends `https://` and applies strict URL validation. LinkedIn URLs may come in as `linkedin.com/company/x` (no scheme) or `https://www.linkedin.com/company/x` (with www) -- the auto-prepend creates `https://linkedin.com/company/x` vs `https://https://www.linkedin.com/company/x`.
**Why it happens:** "url" seems like the obvious choice for a URL field.
**How to avoid:** Use `type: "string"` + `fieldType: "text"`. Normalize all LinkedIn URLs to a canonical form (`https://www.linkedin.com/company/{slug}`) in Clay before storing.
**Warning signs:** Lookup misses on LinkedIn URLs that should match.

### Pitfall 2: Opted-Out Domains Don't Block Form Submissions
**What goes wrong:** Contacts submitted through HubSpot forms that include company properties still get auto-associated to the parent company, even if the domain is opted out.
**Why it happens:** HubSpot's form submission logic bypasses the opted-out domains setting when company properties are included in the form.
**How to avoid:** Audit all HubSpot forms that capture contacts for pilot parent domains. Remove company properties from those forms, or use contact-level custom properties instead.
**Warning signs:** Contacts from opted-out domains still appearing associated to parent companies after form submissions.

### Pitfall 3: Property Group Must Exist Before Properties
**What goes wrong:** API call to create a property with a non-existent `groupName` fails silently or returns an error.
**Why it happens:** Property groups are not auto-created -- you must create the group first via `POST /crm/v3/properties/{objectType}/groups`.
**How to avoid:** Create the property group before creating any properties that reference it.
**Warning signs:** 400 errors on property creation API calls.

### Pitfall 4: LinkedIn URL Normalization
**What goes wrong:** The same company has multiple LinkedIn URL formats across different sources: `linkedin.com/company/twelveLabs`, `https://www.linkedin.com/company/twelve-labs/`, `https://linkedin.com/company/twelve-labs`.
**Why it happens:** Different enrichment sources format LinkedIn URLs differently.
**How to avoid:** Define a canonical format early (e.g., `https://www.linkedin.com/company/{slug}` in lowercase, no trailing slash). Apply normalization in Clay before writing to the lookup table and before matching.
**Warning signs:** Lookup table has duplicate entries for the same company with different URL formats.

### Pitfall 5: Opted-Out Domains Is UI-Only
**What goes wrong:** Planning assumes you can script/automate adding 100+ domains to the exclusion list.
**Why it happens:** No API endpoint exists for managing opted-out domains.
**How to avoid:** Plan for manual UI work. For Phase 1 pilot (10-20 domains), manual entry is fine. For Phase 4 scale-up (100+ domains), budget time for manual domain entry or investigate workarounds (browser automation, HubSpot support request).
**Warning signs:** Searching for an API endpoint that doesn't exist.

### Pitfall 6: Clay Table/Webhook Creation Requires UI
**What goes wrong:** Planning assumes Clay tables and webhook URLs can be created programmatically.
**Why it happens:** Clay is primarily a graphical tool with no public API for table management.
**How to avoid:** Create the lookup table manually in Clay UI. Data can be populated via CSV import or webhook, but the table structure must be set up by hand.
**Warning signs:** Trying to automate Clay table creation.

### Pitfall 7: HubSpot Search API 10,000 Result Limit
**What goes wrong:** If there are more than 10,000 child companies in HubSpot, pagination beyond 10,000 returns a 400 error.
**Why it happens:** HubSpot Search API hard caps at 10,000 total results per query.
**How to avoid:** Use filters to narrow queries (e.g., filter by domain, by parent company ID). For the pilot (10-20 parents), this won't be an issue.
**Warning signs:** 400 errors when paginating through large result sets.

## Code Examples

### Create Property Group (do this first)

```bash
# Source: HubSpot Properties API v3 docs
# Create property group for contacts
curl --request POST \
  --url https://api.hubapi.com/crm/v3/properties/contacts/groups \
  --header 'Authorization: Bearer <ACCESS_TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
    "name": "contact_routing",
    "label": "Contact Routing",
    "displayOrder": -1
  }'

# Create same group for companies
curl --request POST \
  --url https://api.hubapi.com/crm/v3/properties/companies/groups \
  --header 'Authorization: Bearer <ACCESS_TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
    "name": "contact_routing",
    "label": "Contact Routing",
    "displayOrder": -1
  }'
```

### Create linkedin_company_url on Contacts

```bash
# Source: HubSpot Properties API v3 docs
curl --request POST \
  --url https://api.hubapi.com/crm/v3/properties/contacts \
  --header 'Authorization: Bearer <ACCESS_TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
    "groupName": "contact_routing",
    "name": "linkedin_company_url",
    "label": "LinkedIn Company URL",
    "type": "string",
    "fieldType": "text",
    "description": "LinkedIn company page URL from enrichment. Used for parent-child routing."
  }'
```

### Create linkedin_company_url on Companies

```bash
# Source: HubSpot Properties API v3 docs
curl --request POST \
  --url https://api.hubapi.com/crm/v3/properties/companies \
  --header 'Authorization: Bearer <ACCESS_TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
    "groupName": "contact_routing",
    "name": "linkedin_company_url",
    "label": "LinkedIn Company URL",
    "type": "string",
    "fieldType": "text",
    "description": "LinkedIn company page URL. Used for child company matching and dedup guard."
  }'
```

### Create routing_tag on Contacts

```bash
# Source: HubSpot Properties API v3 docs
curl --request POST \
  --url https://api.hubapi.com/crm/v3/properties/contacts \
  --header 'Authorization: Bearer <ACCESS_TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
    "groupName": "contact_routing",
    "name": "routing_tag",
    "label": "Routing Tag",
    "type": "string",
    "fieldType": "text",
    "description": "Set by Clay. Values: parent | child:{company_id} | new_child"
  }'
```

### Check if Property Already Exists

```bash
# Source: HubSpot Properties API v3 docs
# Check contacts for linkedin_company_url
curl --request GET \
  --url https://api.hubapi.com/crm/v3/properties/contacts/linkedin_company_url \
  --header 'Authorization: Bearer <ACCESS_TOKEN>'

# 200 = exists, 404 = does not exist
```

### Search for Companies with Child Companies (Pilot Identification)

```bash
# Source: HubSpot Search API v3 docs
# Find companies that have the hs_parent_company_id set (i.e., they ARE children)
curl --request POST \
  --url https://api.hubapi.com/crm/v3/objects/companies/search \
  --header 'Authorization: Bearer <ACCESS_TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
    "filterGroups": [
      {
        "filters": [
          {
            "propertyName": "hs_parent_company_id",
            "operator": "HAS_PROPERTY"
          }
        ]
      }
    ],
    "properties": ["name", "domain", "hs_parent_company_id", "linkedin_company_url"],
    "limit": 200
  }'
```

### Get Child Companies for a Specific Parent

```bash
# Source: HubSpot Associations API v4 docs
# Get all company associations for a parent company
curl --request GET \
  --url https://api.hubapi.com/crm/v4/objects/companies/{parentCompanyId}/associations/companies \
  --header 'Authorization: Bearer <ACCESS_TOKEN>'

# Response includes associationTypes with typeId 13 (parent->child) or 14 (child->parent)
```

### Search Companies by Domain

```bash
# Source: HubSpot Search API v3 docs
# Find the parent company for a specific domain
curl --request POST \
  --url https://api.hubapi.com/crm/v3/objects/companies/search \
  --header 'Authorization: Bearer <ACCESS_TOKEN>' \
  --header 'Content-Type: application/json' \
  --data '{
    "filterGroups": [
      {
        "filters": [
          {
            "propertyName": "domain",
            "operator": "EQ",
            "value": "nfl.com"
          }
        ]
      }
    ],
    "properties": ["name", "domain", "hs_parent_company_id", "linkedin_company_url"],
    "limit": 10
  }'
```

## Task-by-Task Analysis

### Task 1: Add HubSpot Properties (UNBLOCKED - Can Do Now)

**Approach:** Three API calls to create properties + two calls to create property groups.

**Execution order:**
1. Create `contact_routing` property group on Contacts object
2. Create `contact_routing` property group on Companies object
3. Check if `linkedin_company_url` exists on Contacts (GET) -- skip if 200
4. Create `linkedin_company_url` on Contacts (POST)
5. Check if `linkedin_company_url` exists on Companies (GET) -- skip if 200
6. Create `linkedin_company_url` on Companies (POST)
7. Check if `routing_tag` exists on Contacts (GET) -- skip if 200
8. Create `routing_tag` on Contacts (POST)

**Authentication:** Requires HubSpot Private App token with `crm.schemas.contacts.write` and `crm.schemas.companies.write` scopes.

**Risk:** LOW. Standard API operations, well-documented, idempotent if property already exists (409 Conflict).

### Task 2: Opted-Out Domains (UNBLOCKED - Can Do Now)

**Approach:** Manual UI configuration. No API available.

**Steps:**
1. Navigate to HubSpot Settings > Objects > Companies
2. Under automatic association, click "Exclude a domain out of automatic association"
3. Enter each pilot domain (e.g., `nfl.com`, `amazon.com`)
4. Click Save

**Limit:** Up to 1,000 domains can be excluded. Plenty for the 100+ parent companies.

**Caveat:** Form submissions with company properties bypass this setting. Audit forms.

**Risk:** MEDIUM. The form submission bypass is a known gotcha. Needs form audit.

### Task 3: Clay Mapping Table (PARTIALLY UNBLOCKED)

**Approach:** Create table in Clay UI, populate via CSV import.

**Steps:**
1. Create a new table in Clay workspace (manual, UI only)
2. Define columns: `linkedin_company_url`, `hubspot_company_id`, `company_name`, `parent_company_name`, `parent_domain`
3. For each pilot parent: use HubSpot Associations API to get child company IDs
4. For each child company: use HubSpot Companies API to get `linkedin_company_url` property value
5. Export as CSV with columns matching Clay table
6. Import CSV into Clay table

**Dependency:** Requires Task 1 complete (linkedin_company_url property must exist on Companies).
Also requires existing child companies to already have LinkedIn URLs populated. If they don't, Clay enrichment needs to run first.

**Risk:** MEDIUM. The LinkedIn URL may not be populated on existing child companies. May need a Clay enrichment run on companies before the mapping table can be built.

### Task 4: Pilot Parent Identification (UNBLOCKED - Can Do Now)

**Approach:** Combination of HubSpot API queries and stakeholder input.

**Fast path:** Ask Sean for the top 10-20 domains that cause the most routing problems. He likely knows them from rep complaints.

**Data-driven path:**
1. Search HubSpot for all companies with `hs_parent_company_id` set (these are children)
2. Group by `hs_parent_company_id` to find parents with the most children
3. Cross-reference with known enterprise shared-domain companies

**Risk:** LOW. Even without API data, Sean can provide the pilot list manually.

### Task 5: Industry-to-Segment Mapping (BLOCKED on Sean)

**Approach:** This is a lookup table that maps HubSpot Industry values to 12 Labs' internal Segments (e.g., "Media & Entertainment", "SaaS/Emerging Verticals").

**Expected format:**
```
Industry (HubSpot)     → Segment (12 Labs)
Broadcasting           → M&E
Film Production        → M&E
SaaS                   → SaaS/Emerging
Artificial Intelligence → SaaS/Emerging
...
```

**Where it would live:** Could be:
- A Clay lookup table (if routing decision is in Clay)
- A HubSpot property (if routing decision is in Ops Hub workflow)
- Per the architecture, routing decision tree runs in HubSpot Ops Hub -- so this mapping likely becomes a workflow branch or custom code action in HubSpot

**Risk:** HIGH (blocked). Cannot proceed without Sean's input. However, this does NOT block Tasks 1-4.

## What Can Be Done NOW vs. What's Blocked

### Unblocked (Start Immediately)
| Task | What | Effort |
|------|------|--------|
| 1. HubSpot Properties | Create 3 properties + 2 groups via API | 30 min |
| 2. Opted-Out Domains | Manual UI configuration | 15 min (once pilot list is known) |
| 4. Pilot Parent ID | Ask Sean OR query HubSpot API | 1-2 hours |

### Partially Unblocked
| Task | What | Blocker |
|------|------|---------|
| 3. Clay Mapping Table | Structure can be created now, population depends on LinkedIn URLs existing on child companies | Need to verify LinkedIn URL data exists on companies |

### Blocked
| Task | What | Blocker |
|------|------|---------|
| 5. Industry-Segment Map | Need Sean's mapping | Waiting on Sean Graham |

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| HubSpot Properties API v1/v2 | Properties API v3 | 2022+ | Unified endpoint, consistent JSON format |
| Associations API v3 | Associations API v4 | 2023+ | Labeled associations, batch operations, higher limits |
| Company search by domain (v1) | Search API v3 with domain filter | 2022+ | POST-based, filter groups, 10K result cap |
| Manual parent-child setup only | API-managed parent-child (defId 13/14) | Sept 2018 | Programmatic parent-child relationship management |

**Deprecated/outdated:**
- HubSpot Properties API v1/v2 -- fully replaced by v3
- `companies/v2/domains/{domain}/companies` endpoint -- use Search API v3 with domain filter instead

## Open Questions

1. **Does `linkedin_company_url` already exist on any HubSpot objects?**
   - What we know: Sean needs to confirm if Clay already pushes this field
   - What's unclear: The exact property name if it exists (could be `linkedin_company_page`, `company_linkedin_url`, etc.)
   - Recommendation: Use HubSpot API to list all properties on Contacts and Companies, search for any containing "linkedin" in the name. Do this before creating properties to avoid duplicates.

2. **Are LinkedIn URLs populated on existing child companies?**
   - What we know: Clay enriches new companies with LinkedIn data
   - What's unclear: Whether historical child companies have this data
   - Recommendation: Query a sample of child companies via API to check. If not populated, a Clay enrichment run on existing companies is needed before the mapping table can be built.

3. **What HubSpot Private App exists for API access?**
   - What we know: API calls require authentication
   - What's unclear: Whether 12 Labs has an existing private app with the needed scopes, or if one needs to be created
   - Recommendation: Ask Sean. Creating a private app takes 5 minutes but requires Super Admin access.

4. **Multiple domains per parent company?**
   - What we know: Some parents have multiple domains (amazon.com + amazon.co.jp)
   - What's unclear: How HubSpot stores these -- `hs_additional_domains` field uses semicolons
   - Recommendation: When building the opted-out domains list, check for `hs_additional_domains` on each parent company and add ALL domains to the exclusion list.

5. **Form submissions bypassing opted-out domains?**
   - What we know: Forms with company properties bypass the setting
   - What's unclear: Which forms 12 Labs uses and whether they include company properties
   - Recommendation: Audit all active HubSpot forms for pilot parent domains before going live.

## Sources

### Primary (HIGH confidence)
- [HubSpot Properties API v3 Guide](https://developers.hubspot.com/docs/api-reference/crm-properties-v3/guide) - Property creation endpoints, types, fieldTypes
- [HubSpot CRM Search API Guide](https://developers.hubspot.com/docs/api-reference/search/guide) - Search endpoints, filter operators, pagination limits
- [HubSpot Associations API v4 Guide](https://developers.hubspot.com/docs/api-reference/crm-associations-v4/guide) - Parent-child association types (13/14), batch operations
- [HubSpot Auto-Association Settings](https://knowledge.hubspot.com/object-settings/automatically-create-and-associate-companies-with-contacts) - Opted-out domains feature, limitations
- [HubSpot Property Field Types](https://knowledge.hubspot.com/properties/property-field-types-in-hubspot) - URL vs text fieldType details

### Secondary (MEDIUM confidence)
- [Clay Lookup Rows Documentation](https://university.clay.com/docs/lookup-rows) - Lookup table matching, configuration
- [Clay CSV Import Documentation](https://university.clay.com/docs/csv-import-overview) - CSV import into tables
- [Clay HTTP API Integration](https://university.clay.com/docs/http-api-integration-overview) - Webhook-based table population
- [HubSpot Parent-Child Associations Changelog](https://developers.hubspot.com/changelog/2018-9-11-parent-child-associations) - Definition IDs 13/14 for parent-child

### Tertiary (LOW confidence)
- [HubSpot Community: Form submissions bypass opted-out domains](https://community.hubspot.com/t5/CRM/Form-Submissions-amp-Email-Domains/m-p/868574) - Confirmed by multiple users but no official KB article
- [HubSpot Community: No API for opted-out domains](https://community.hubspot.com/t5/APIs-Integrations/Black-List-domain-to-avoid-automatic-association-with-company/m-p/710625) - Confirmed by community, no official statement

## Metadata

**Confidence breakdown:**
- HubSpot Properties API: HIGH - Official docs, well-documented, stable API
- HubSpot Search API: HIGH - Official docs, clear examples
- HubSpot Associations API: HIGH - Official docs, v4 is current
- Opted-out domains: HIGH for feature existence, MEDIUM for limitations (form bypass from community)
- Clay lookup tables: MEDIUM - Documentation exists but less detailed than HubSpot
- Clay API capabilities: MEDIUM - Confirmed UI-only for table creation
- Industry-Segment mapping format: LOW - Speculative, blocked on Sean

**Research date:** 2026-03-10
**Valid until:** 2026-04-10 (HubSpot APIs are stable, Clay may release API features)
