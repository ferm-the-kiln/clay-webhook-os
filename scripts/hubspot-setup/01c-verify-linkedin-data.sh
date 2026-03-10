#!/usr/bin/env bash
# =============================================================================
# 01c-verify-linkedin-data.sh
# Phase 1, Wave 1 — Task 1.3: Verify LinkedIn URL Data on Child Companies
#
# Samples 10 child companies and checks whether linkedin_company_url is
# already populated. Determines if Clay enrichment is needed before the
# mapping table can be built.
#
# Usage:
#   export HUBSPOT_ACCESS_TOKEN="pat-na1-xxxxxxxxxxxx"
#   bash scripts/hubspot-setup/01c-verify-linkedin-data.sh
#
# Optional — use a different property name if audit found a variant:
#   export LINKEDIN_PROPERTY="linkedin_company_page"
#   bash scripts/hubspot-setup/01c-verify-linkedin-data.sh
# =============================================================================

set -euo pipefail

if [[ -z "${HUBSPOT_ACCESS_TOKEN:-}" ]]; then
  echo "ERROR: HUBSPOT_ACCESS_TOKEN is not set."
  echo "       export HUBSPOT_ACCESS_TOKEN=\"pat-na1-xxxxxxxxxxxx\""
  exit 1
fi

TOKEN="$HUBSPOT_ACCESS_TOKEN"
BASE="https://api.hubapi.com"
LINKEDIN_PROP="${LINKEDIN_PROPERTY:-linkedin_company_url}"

echo ""
echo "============================================================"
echo "  Verifying LinkedIn URL Data on Child Companies"
echo "  Property checked: ${LINKEDIN_PROP}"
echo "============================================================"
echo ""

RESPONSE=$(curl -s -X POST "${BASE}/crm/v3/objects/companies/search" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d "{
    \"filterGroups\": [{
      \"filters\": [{
        \"propertyName\": \"hs_parent_company_id\",
        \"operator\": \"HAS_PROPERTY\"
      }]
    }],
    \"properties\": [\"name\", \"domain\", \"${LINKEDIN_PROP}\", \"hs_parent_company_id\"],
    \"limit\": 10
  }")

python3 - "$LINKEDIN_PROP" << 'PYEOF'
import sys, json, os

linkedin_prop = sys.argv[1]

# Read from stdin (curl response piped in via process substitution)
data = json.loads(os.environ.get('RESPONSE', '{}'))
PYEOF

# Pass response via environment variable to avoid heredoc quoting issues
export RESPONSE="$RESPONSE"
python3 - "$LINKEDIN_PROP" << 'PYEOF'
import sys, json, os

linkedin_prop = sys.argv[1]
data = json.loads(os.environ['RESPONSE'])
results = data.get('results', [])

if not results:
    print("  No child companies found (hs_parent_company_id not set on any company).")
    sys.exit(0)

with_url = 0
without_url = 0

print(f"  Sampled {len(results)} child companies:\n")
print(f"  {'Name':<35} {'Domain':<25} {'LinkedIn URL'}")
print("  " + "-" * 90)

for r in results:
    props = r.get('properties', {})
    name = (props.get('name') or '')[:34]
    domain = (props.get('domain') or '')[:24]
    linkedin = props.get(linkedin_prop) or ''

    if linkedin:
        with_url += 1
        status = linkedin[:50]
    else:
        without_url += 1
        status = '(empty)'

    print(f"  {name:<35} {domain:<25} {status}")

print()
print(f"  Summary: {with_url}/{len(results)} have LinkedIn URL populated")
print()

if without_url == 0:
    print("  RESULT: LinkedIn URLs are populated. Mapping table can be built directly.")
    print("          Proceed to Task 4.2 (extract child company data).")
elif with_url == 0:
    print("  RESULT: LinkedIn URLs are EMPTY on all sampled companies.")
    print("          You will need to run Task 4.2b (Clay enrichment) before building")
    print("          the mapping table.")
else:
    pct_missing = round(without_url / len(results) * 100)
    print(f"  RESULT: Partial data ({pct_missing}% missing). Enrichment recommended.")
    print("          Run Task 4.2b (Clay enrichment) for companies missing LinkedIn URLs.")
PYEOF

echo ""
