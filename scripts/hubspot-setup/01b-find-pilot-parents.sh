#!/usr/bin/env bash
# =============================================================================
# 01b-find-pilot-parents.sh
# Phase 1, Wave 1 — Task 1.2b: Identify Pilot Parents via API (Fallback)
#
# Use this if Sean doesn't provide a pilot domain list within 2 days.
# Queries HubSpot for all child companies (have hs_parent_company_id set),
# groups them by parent, and ranks parents by child count.
# Top 20 = your pilot list.
#
# Output: pilot-parents.json and pilot-parents-summary.txt
#
# Usage:
#   export HUBSPOT_ACCESS_TOKEN="pat-na1-xxxxxxxxxxxx"
#   bash scripts/hubspot-setup/01b-find-pilot-parents.sh
# =============================================================================

set -euo pipefail

if [[ -z "${HUBSPOT_ACCESS_TOKEN:-}" ]]; then
  echo "ERROR: HUBSPOT_ACCESS_TOKEN is not set."
  echo "       export HUBSPOT_ACCESS_TOKEN=\"pat-na1-xxxxxxxxxxxx\""
  exit 1
fi

TOKEN="$HUBSPOT_ACCESS_TOKEN"
BASE="https://api.hubapi.com"
OUTPUT_DIR="scripts/hubspot-setup/output"
mkdir -p "$OUTPUT_DIR"

echo ""
echo "============================================================"
echo "  Finding Pilot Parent Companies (Fallback Script)"
echo "  Querying for companies with hs_parent_company_id set"
echo "============================================================"
echo ""

# ----------------------------------------------------------------
# Paginate through all child companies (10K result cap per query)
# Each page = 200 results. Collects: name, domain, parent_id
# ----------------------------------------------------------------
ALL_CHILDREN_FILE="$OUTPUT_DIR/all-children-raw.json"
echo "[]" > "$ALL_CHILDREN_FILE"

after=""
page=1
total_fetched=0

while true; do
  echo "  Fetching page ${page}..."

  if [[ -z "$after" ]]; then
    BODY='{
      "filterGroups": [{
        "filters": [{
          "propertyName": "hs_parent_company_id",
          "operator": "HAS_PROPERTY"
        }]
      }],
      "properties": ["name", "domain", "hs_parent_company_id"],
      "limit": 200
    }'
  else
    BODY="{
      \"filterGroups\": [{
        \"filters\": [{
          \"propertyName\": \"hs_parent_company_id\",
          \"operator\": \"HAS_PROPERTY\"
        }]
      }],
      \"properties\": [\"name\", \"domain\", \"hs_parent_company_id\"],
      \"limit\": 200,
      \"after\": \"${after}\"
    }"
  fi

  RESPONSE=$(curl -s -X POST "${BASE}/crm/v3/objects/companies/search" \
    -H "Authorization: Bearer ${TOKEN}" \
    -H "Content-Type: application/json" \
    -d "$BODY")

  # Check for API error
  if echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); exit(0 if 'results' in d else 1)" 2>/dev/null; then
    COUNT=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(len(d.get('results', [])))")
    total_fetched=$((total_fetched + COUNT))

    # Append to accumulated results
    python3 -c "
import sys, json
with open('${ALL_CHILDREN_FILE}', 'r') as f:
    existing = json.load(f)
new_data = json.loads(sys.stdin.read())
existing.extend(new_data.get('results', []))
with open('${ALL_CHILDREN_FILE}', 'w') as f:
    json.dump(existing, f)
" <<< "$RESPONSE"

    # Check for next page cursor
    NEXT=$(echo "$RESPONSE" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('paging', {}).get('next', {}).get('after', ''))" 2>/dev/null || echo "")

    if [[ -z "$NEXT" ]] || [[ "$COUNT" -eq 0 ]]; then
      echo "  Done. Total child companies fetched: ${total_fetched}"
      break
    fi

    after="$NEXT"
    page=$((page + 1))
  else
    echo "  ERROR: Unexpected API response."
    echo "$RESPONSE" | python3 -m json.tool
    exit 1
  fi
done

# ----------------------------------------------------------------
# Rank parents by child count, output top 20
# ----------------------------------------------------------------
SUMMARY_FILE="$OUTPUT_DIR/pilot-parents-summary.txt"
JSON_FILE="$OUTPUT_DIR/pilot-parents-ranked.json"

python3 - "$ALL_CHILDREN_FILE" "$SUMMARY_FILE" "$JSON_FILE" << 'PYEOF'
import sys, json
from collections import Counter, defaultdict

children_file = sys.argv[1]
summary_file = sys.argv[2]
json_file = sys.argv[3]

with open(children_file) as f:
    children = json.load(f)

# Count children per parent ID
parent_counts = Counter()
parent_children = defaultdict(list)
for c in children:
    props = c.get('properties', {})
    parent_id = props.get('hs_parent_company_id')
    if parent_id:
        parent_counts[parent_id] += 1
        parent_children[parent_id].append({
            'id': c['id'],
            'name': props.get('name', ''),
            'domain': props.get('domain', '')
        })

# Top 20 parents
ranked = sorted(parent_counts.items(), key=lambda x: x[1], reverse=True)[:20]

result = []
for parent_id, count in ranked:
    result.append({
        'parent_hubspot_id': parent_id,
        'child_count': count,
        'sample_children': parent_children[parent_id][:3]
    })

with open(json_file, 'w') as f:
    json.dump(result, f, indent=2)

# Human-readable summary
with open(summary_file, 'w') as f:
    f.write("Top 20 Parent Companies by Child Count\n")
    f.write("=" * 60 + "\n\n")
    f.write(f"{'Rank':<5} {'Parent HubSpot ID':<22} {'Child Count':<14} Sample Children\n")
    f.write("-" * 80 + "\n")
    for i, (parent_id, count) in enumerate(ranked, 1):
        samples = parent_children[parent_id][:2]
        sample_names = ', '.join(s['name'] or s['domain'] or s['id'] for s in samples)
        f.write(f"{i:<5} {parent_id:<22} {count:<14} {sample_names}\n")

    f.write(f"\nTotal child companies found: {len(children)}\n")
    f.write(f"Total parent companies: {len(parent_counts)}\n")
    f.write("\nNEXT STEP: Look up each parent ID in HubSpot to get their domain.\n")
    f.write("  curl -s https://api.hubapi.com/crm/v3/objects/companies/{ID}?properties=name,domain ...\n")

print(f"Ranked {len(ranked)} parents. Top parent has {ranked[0][1] if ranked else 0} children.")
PYEOF

echo ""
echo "Results written to:"
echo "  $JSON_FILE"
echo "  $SUMMARY_FILE"
echo ""
cat "$SUMMARY_FILE"
echo ""
echo "NOTE: Use the parent IDs above to look up domains in HubSpot,"
echo "      then provide that domain list to Task 3.1 (opted-out domains)."
echo ""
