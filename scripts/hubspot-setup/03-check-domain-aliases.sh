#!/usr/bin/env bash
# =============================================================================
# 03-check-domain-aliases.sh
# Phase 1, Wave 3 — Task 3.1 support: Check Additional Domains on Parent Companies
#
# HubSpot stores alternate domains in hs_additional_domains. Before adding
# a parent to the opted-out list, check if they have aliases that also need
# to be excluded (e.g., amazon.com also has amazon.co.uk, amazon.de, etc.)
#
# Usage:
#   export HUBSPOT_ACCESS_TOKEN="pat-na1-xxxxxxxxxxxx"
#   bash scripts/hubspot-setup/03-check-domain-aliases.sh amazon.com nfl.com
#
# Or pipe from a file:
#   cat pilot-domains.txt | xargs bash scripts/hubspot-setup/03-check-domain-aliases.sh
# =============================================================================

set -euo pipefail

if [[ -z "${HUBSPOT_ACCESS_TOKEN:-}" ]]; then
  echo "ERROR: HUBSPOT_ACCESS_TOKEN is not set."
  echo "       export HUBSPOT_ACCESS_TOKEN=\"pat-na1-xxxxxxxxxxxx\""
  exit 1
fi

if [[ $# -eq 0 ]]; then
  echo "Usage: bash 03-check-domain-aliases.sh domain1.com domain2.com ..."
  echo "       bash 03-check-domain-aliases.sh amazon.com nfl.com"
  exit 1
fi

TOKEN="$HUBSPOT_ACCESS_TOKEN"
BASE="https://api.hubapi.com"

echo ""
echo "============================================================"
echo "  Domain Alias Check"
echo "  Checking hs_additional_domains for each pilot domain"
echo "============================================================"
echo ""

ALL_DOMAINS=()

for domain in "$@"; do
  echo "--- ${domain} ---"

  RESPONSE=$(curl -s -X POST "${BASE}/crm/v3/objects/companies/search" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "{
      \"filterGroups\": [{
        \"filters\": [{
          \"propertyName\": \"domain\",
          \"operator\": \"EQ\",
          \"value\": \"${domain}\"
        }]
      }],
      \"properties\": [\"name\", \"domain\", \"hs_additional_domains\"],
      \"limit\": 1
    }")

  python3 - "$domain" << 'PYEOF'
import sys, json, os

primary_domain = sys.argv[1]
data = json.loads(os.environ['RESPONSE'])
results = data.get('results', [])

if not results:
    print(f"  No HubSpot company found for domain: {primary_domain}")
    # Still add the primary domain
    print(f"  ADD TO OPTED-OUT LIST: {primary_domain}")
else:
    r = results[0]
    props = r.get('properties', {})
    name = props.get('name', '(unknown)')
    additional = props.get('hs_additional_domains', '') or ''

    print(f"  Company: {name} (ID: {r['id']})")
    print(f"  Primary domain: {primary_domain}")

    if additional:
        aliases = [a.strip() for a in additional.split(';') if a.strip()]
        print(f"  Additional domains ({len(aliases)}): {', '.join(aliases)}")
        print()
        print(f"  ADD ALL TO OPTED-OUT LIST:")
        print(f"    {primary_domain}")
        for a in aliases:
            print(f"    {a}")
    else:
        print(f"  No additional domains found.")
        print(f"  ADD TO OPTED-OUT LIST: {primary_domain}")
PYEOF

  echo ""
done

echo "============================================================"
echo "  Add ALL listed domains to:"
echo "  HubSpot → Settings → Objects → Companies"
echo "  → Automatic association → Exclude a domain"
echo "============================================================"
echo ""
echo "  NOTE: There is no API for opted-out domains. This is a"
echo "        manual UI step — no script can automate it."
echo ""
