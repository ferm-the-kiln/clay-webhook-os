#!/usr/bin/env bash
# =============================================================================
# 01-audit-properties.sh
# Phase 1, Wave 1 — Task 1.1: Audit Existing HubSpot Properties
#
# Checks whether linkedin_company_url and routing_tag already exist on
# Contacts and/or Companies objects in HubSpot. Run this BEFORE running
# 02-create-properties.sh to avoid creating duplicates.
#
# Usage:
#   export HUBSPOT_ACCESS_TOKEN="pat-na1-xxxxxxxxxxxx"
#   bash scripts/hubspot-setup/01-audit-properties.sh
# =============================================================================

set -euo pipefail

if [[ -z "${HUBSPOT_ACCESS_TOKEN:-}" ]]; then
  echo "ERROR: HUBSPOT_ACCESS_TOKEN is not set."
  echo "       export HUBSPOT_ACCESS_TOKEN=\"pat-na1-xxxxxxxxxxxx\""
  exit 1
fi

TOKEN="$HUBSPOT_ACCESS_TOKEN"
BASE="https://api.hubapi.com"

echo ""
echo "============================================================"
echo "  HubSpot Property Audit"
echo "  Checking: linkedin_company_url, routing_tag"
echo "============================================================"
echo ""

# ----------------------------------------------------------------
# Helper: check if a specific property exists (200 = yes, 404 = no)
# ----------------------------------------------------------------
check_property() {
  local object_type="$1"
  local property_name="$2"
  local http_status

  http_status=$(curl -s -o /dev/null -w "%{http_code}" \
    "${BASE}/crm/v3/properties/${object_type}/${property_name}" \
    -H "Authorization: Bearer ${TOKEN}")

  if [[ "$http_status" == "200" ]]; then
    echo "  [EXISTS]  ${object_type}.${property_name}"
  elif [[ "$http_status" == "404" ]]; then
    echo "  [MISSING] ${object_type}.${property_name}  → needs creation"
  else
    echo "  [ERROR]   ${object_type}.${property_name}  → HTTP ${http_status}"
  fi
}

# ----------------------------------------------------------------
# Helper: find all LinkedIn-related properties (catch naming variants)
# ----------------------------------------------------------------
find_linkedin_properties() {
  local object_type="$1"
  echo ""
  echo "--- LinkedIn-related properties on ${object_type} ---"
  curl -s "${BASE}/crm/v3/properties/${object_type}" \
    -H "Authorization: Bearer ${TOKEN}" | \
    python3 -c "
import sys, json
data = json.load(sys.stdin)
results = data.get('results', [])
matches = [p for p in results if 'linkedin' in p['name'].lower() or 'linkedin' in p['label'].lower()]
if matches:
    for p in matches:
        print(f\"  name={p['name']}  label={p['label']}  type={p['type']}  fieldType={p['fieldType']}\")
else:
    print('  (none found)')
"
}

# ----------------------------------------------------------------
# Check required properties
# ----------------------------------------------------------------
echo "=== Checking required properties ==="
echo ""
check_property "contacts"  "linkedin_company_url"
check_property "companies" "linkedin_company_url"
check_property "contacts"  "routing_tag"

# ----------------------------------------------------------------
# Scan for LinkedIn naming variants (to avoid duplicates)
# ----------------------------------------------------------------
echo ""
echo "=== Scanning for LinkedIn naming variants ==="
find_linkedin_properties "contacts"
find_linkedin_properties "companies"

# ----------------------------------------------------------------
# Check property groups
# ----------------------------------------------------------------
echo ""
echo "=== Checking contact_routing property group ==="
for obj in contacts companies; do
  status=$(curl -s -o /dev/null -w "%{http_code}" \
    "${BASE}/crm/v3/properties/${obj}/groups/contact_routing" \
    -H "Authorization: Bearer ${TOKEN}")
  if [[ "$status" == "200" ]]; then
    echo "  [EXISTS]  ${obj}/groups/contact_routing"
  else
    echo "  [MISSING] ${obj}/groups/contact_routing  → needs creation (HTTP ${status})"
  fi
done

echo ""
echo "============================================================"
echo "  DECISION GATE (read before proceeding to Wave 2):"
echo "  - If linkedin_company_url exists under a different name,"
echo "    use THAT name everywhere. Do NOT create a duplicate."
echo "  - Document the canonical property name in your runbook."
echo "============================================================"
echo ""
