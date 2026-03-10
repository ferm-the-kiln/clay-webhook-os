#!/usr/bin/env bash
# =============================================================================
# 02-create-properties.sh
# Phase 1, Wave 2 — Tasks 2.1 + 2.2: Create Property Groups + Custom Properties
#
# Creates:
#   - Property group "contact_routing" on Contacts + Companies
#   - linkedin_company_url (string/text) on Contacts
#   - linkedin_company_url (string/text) on Companies
#   - routing_tag (string/text) on Contacts
#
# IMPORTANT:
#   Run 01-audit-properties.sh FIRST to confirm these don't already exist.
#   If linkedin_company_url already exists under a different name, do NOT run
#   this script — update your runbook with the existing property name instead.
#
# Field type note: We use fieldType "text" NOT "url". The "url" fieldType
# auto-prepends "https://" and breaks lookup matching in Clay.
#
# Usage:
#   export HUBSPOT_ACCESS_TOKEN="pat-na1-xxxxxxxxxxxx"
#   bash scripts/hubspot-setup/02-create-properties.sh
#
# Dry run (shows what would be created, doesn't call API):
#   DRY_RUN=true bash scripts/hubspot-setup/02-create-properties.sh
# =============================================================================

set -euo pipefail

if [[ -z "${HUBSPOT_ACCESS_TOKEN:-}" ]]; then
  echo "ERROR: HUBSPOT_ACCESS_TOKEN is not set."
  echo "       export HUBSPOT_ACCESS_TOKEN=\"pat-na1-xxxxxxxxxxxx\""
  exit 1
fi

TOKEN="$HUBSPOT_ACCESS_TOKEN"
BASE="https://api.hubapi.com"
DRY_RUN="${DRY_RUN:-false}"

if [[ "$DRY_RUN" == "true" ]]; then
  echo "DRY RUN MODE — no API calls will be made."
fi

echo ""
echo "============================================================"
echo "  HubSpot Property Creation"
echo "  Wave 2: Groups + Properties"
echo "============================================================"
echo ""

# ----------------------------------------------------------------
# Helper: create or skip (idempotent — 409 conflict = already exists)
# ----------------------------------------------------------------
create_or_skip() {
  local label="$1"
  local method="$2"
  local url="$3"
  local body="$4"

  if [[ "$DRY_RUN" == "true" ]]; then
    echo "  [DRY RUN] Would create: ${label}"
    echo "            ${method} ${url}"
    return
  fi

  local http_status
  local response_body
  response_body=$(curl -s -w "\n%{http_code}" -X "$method" "$url" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$body")

  http_status=$(echo "$response_body" | tail -1)
  response_body=$(echo "$response_body" | head -n -1)

  case "$http_status" in
    200|201)
      echo "  [CREATED] ${label}"
      ;;
    409)
      echo "  [EXISTS]  ${label}  (already exists — skipped)"
      ;;
    *)
      echo "  [ERROR]   ${label}  HTTP ${http_status}"
      echo "  Response: $(echo "$response_body" | python3 -m json.tool 2>/dev/null || echo "$response_body")"
      ;;
  esac
}

# ================================================================
# STEP 1: Create property groups
# ================================================================
echo "=== Step 1: Property Groups ==="
echo ""

create_or_skip \
  "contacts/groups/contact_routing" \
  "POST" \
  "${BASE}/crm/v3/properties/contacts/groups" \
  '{"name": "contact_routing", "label": "Contact Routing", "displayOrder": -1}'

create_or_skip \
  "companies/groups/contact_routing" \
  "POST" \
  "${BASE}/crm/v3/properties/companies/groups" \
  '{"name": "contact_routing", "label": "Contact Routing", "displayOrder": -1}'

# ================================================================
# STEP 2: Create custom properties
# ================================================================
echo ""
echo "=== Step 2: Custom Properties ==="
echo ""

# linkedin_company_url on Contacts
create_or_skip \
  "contacts.linkedin_company_url" \
  "POST" \
  "${BASE}/crm/v3/properties/contacts" \
  '{
    "groupName": "contact_routing",
    "name": "linkedin_company_url",
    "label": "LinkedIn Company URL",
    "type": "string",
    "fieldType": "text",
    "description": "LinkedIn company page URL from enrichment. Used for parent-child routing. Format: https://www.linkedin.com/company/{slug}"
  }'

# linkedin_company_url on Companies
create_or_skip \
  "companies.linkedin_company_url" \
  "POST" \
  "${BASE}/crm/v3/properties/companies" \
  '{
    "groupName": "contact_routing",
    "name": "linkedin_company_url",
    "label": "LinkedIn Company URL",
    "type": "string",
    "fieldType": "text",
    "description": "LinkedIn company page URL. Used for child company matching and dedup guard. Format: https://www.linkedin.com/company/{slug}"
  }'

# routing_tag on Contacts
create_or_skip \
  "contacts.routing_tag" \
  "POST" \
  "${BASE}/crm/v3/properties/contacts" \
  '{
    "groupName": "contact_routing",
    "name": "routing_tag",
    "label": "Routing Tag",
    "type": "string",
    "fieldType": "text",
    "description": "Set by Clay. Values: parent | child:{company_id} | new_child"
  }'

echo ""
echo "============================================================"
echo "  Verification: confirm in HubSpot UI"
echo "  Settings → Properties → search \"linkedin_company_url\""
echo "    - Should appear under Contacts AND Companies"
echo "    - Should be in group: Contact Routing"
echo "  Settings → Properties → search \"routing_tag\""
echo "    - Should appear under Contacts"
echo "    - Should be in group: Contact Routing"
echo "============================================================"
echo ""

if [[ "$DRY_RUN" != "true" ]]; then
  echo "Running quick API verification..."
  echo ""
  for obj in contacts companies; do
    status=$(curl -s -o /dev/null -w "%{http_code}" \
      "${BASE}/crm/v3/properties/${obj}/linkedin_company_url" \
      -H "Authorization: Bearer ${TOKEN}")
    [[ "$status" == "200" ]] && echo "  [OK] ${obj}.linkedin_company_url exists" || echo "  [WARN] ${obj}.linkedin_company_url returned HTTP ${status}"
  done
  status=$(curl -s -o /dev/null -w "%{http_code}" \
    "${BASE}/crm/v3/properties/contacts/routing_tag" \
    -H "Authorization: Bearer ${TOKEN}")
  [[ "$status" == "200" ]] && echo "  [OK] contacts.routing_tag exists" || echo "  [WARN] contacts.routing_tag returned HTTP ${status}"
  echo ""
fi
