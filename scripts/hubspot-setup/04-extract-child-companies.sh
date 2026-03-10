#!/usr/bin/env bash
# =============================================================================
# 04-extract-child-companies.sh
# Phase 1, Wave 4 — Task 4.2: Extract Child Company Data from HubSpot
#
# For each pilot parent company ID, fetches all child companies and their
# LinkedIn URLs. Outputs a CSV ready to import into the Clay mapping table.
#
# Usage:
#   export HUBSPOT_ACCESS_TOKEN="pat-na1-xxxxxxxxxxxx"
#
#   # Option A: Pass parent IDs as arguments
#   bash scripts/hubspot-setup/04-extract-child-companies.sh 12345 67890 11111
#
#   # Option B: Provide parent IDs in a file (one per line)
#   bash scripts/hubspot-setup/04-extract-child-companies.sh --file parent-ids.txt
#
# Optional: override LinkedIn property name if audit found a different one
#   export LINKEDIN_PROPERTY="linkedin_company_page"
#
# Output: scripts/hubspot-setup/output/child-companies.csv
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
OUTPUT_DIR="scripts/hubspot-setup/output"
OUTPUT_CSV="$OUTPUT_DIR/child-companies.csv"
mkdir -p "$OUTPUT_DIR"

# ----------------------------------------------------------------
# Parse arguments
# ----------------------------------------------------------------
PARENT_IDS=()
if [[ $# -eq 0 ]]; then
  echo "ERROR: Provide parent company IDs as arguments or use --file option."
  echo "       bash 04-extract-child-companies.sh 12345 67890"
  echo "       bash 04-extract-child-companies.sh --file parent-ids.txt"
  exit 1
elif [[ "$1" == "--file" ]]; then
  FILE="$2"
  if [[ ! -f "$FILE" ]]; then
    echo "ERROR: File not found: $FILE"
    exit 1
  fi
  while IFS= read -r line; do
    [[ -n "$line" && ! "$line" =~ ^# ]] && PARENT_IDS+=("$line")
  done < "$FILE"
else
  PARENT_IDS=("$@")
fi

echo ""
echo "============================================================"
echo "  Child Company Data Extraction"
echo "  Extracting children for ${#PARENT_IDS[@]} parent companies"
echo "  LinkedIn property: ${LINKEDIN_PROP}"
echo "  Output: ${OUTPUT_CSV}"
echo "============================================================"
echo ""

# CSV header
echo "linkedin_company_url,hubspot_company_id,company_name,parent_company_name,parent_domain" > "$OUTPUT_CSV"

# Accumulate rows in a temp JSON file for Python processing
TEMP_ROWS="$OUTPUT_DIR/.rows_temp.json"
echo "[]" > "$TEMP_ROWS"

for parent_id in "${PARENT_IDS[@]}"; do
  echo "Processing parent ID: ${parent_id}"

  # ---- Get parent company details ----
  PARENT_RESP=$(curl -s \
    "${BASE}/crm/v3/objects/companies/${parent_id}?properties=name,domain" \
    -H "Authorization: Bearer ${TOKEN}")

  PARENT_NAME=$(echo "$PARENT_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('properties',{}).get('name','') or '')" 2>/dev/null || echo "")
  PARENT_DOMAIN=$(echo "$PARENT_RESP" | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('properties',{}).get('domain','') or '')" 2>/dev/null || echo "")
  echo "  Parent: ${PARENT_NAME} (${PARENT_DOMAIN})"

  # ---- Get child company IDs via associations API (v4) ----
  ASSOC_RESP=$(curl -s \
    "${BASE}/crm/v4/objects/companies/${parent_id}/associations/companies" \
    -H "Authorization: Bearer ${TOKEN}")

  CHILD_IDS=$(echo "$ASSOC_RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
results = d.get('results', [])
# Filter to only child relationships (type label contains 'child')
child_ids = []
for r in results:
    labels = [t.get('label','').lower() for t in r.get('associationTypes',[])]
    if any('child' in l for l in labels):
        child_ids.append(str(r['toObjectId']))
print('\n'.join(child_ids))
" 2>/dev/null || echo "")

  if [[ -z "$CHILD_IDS" ]]; then
    # Fallback: get all associated companies (some HubSpot instances don't label parent/child)
    CHILD_IDS=$(echo "$ASSOC_RESP" | python3 -c "
import sys, json
d = json.load(sys.stdin)
results = d.get('results', [])
ids = [str(r['toObjectId']) for r in results]
print('\n'.join(ids))
" 2>/dev/null || echo "")
    echo "  Note: Association type labels not found — using all associated companies as children."
  fi

  CHILD_COUNT=$(echo "$CHILD_IDS" | grep -c . 2>/dev/null || echo 0)
  echo "  Found ${CHILD_COUNT} child companies"

  if [[ "$CHILD_COUNT" -eq 0 ]]; then
    echo "  Skipping (no children found)"
    continue
  fi

  # ---- Fetch each child's properties ----
  while IFS= read -r child_id; do
    [[ -z "$child_id" ]] && continue

    CHILD_RESP=$(curl -s \
      "${BASE}/crm/v3/objects/companies/${child_id}?properties=name,domain,${LINKEDIN_PROP}" \
      -H "Authorization: Bearer ${TOKEN}")

    # Append to temp rows
    python3 - "$child_id" "$parent_id" "$PARENT_NAME" "$PARENT_DOMAIN" "$LINKEDIN_PROP" << 'PYEOF'
import sys, json, os

child_id, parent_id, parent_name, parent_domain, linkedin_prop = sys.argv[1:]

data = json.loads(os.environ['CHILD_RESP'])
props = data.get('properties', {})
child_name = (props.get('name') or '').replace('"', '""')
child_domain = props.get('domain') or ''
linkedin_url = (props.get(linkedin_prop) or '').strip().rstrip('/')

# Normalize: ensure https://www.linkedin.com/company/ format
if linkedin_url and 'linkedin.com/company/' in linkedin_url:
    if not linkedin_url.startswith('http'):
        linkedin_url = 'https://' + linkedin_url
    if 'linkedin.com/company/' in linkedin_url and not '//www.' in linkedin_url:
        linkedin_url = linkedin_url.replace('linkedin.com/', 'www.linkedin.com/')
    linkedin_url = linkedin_url.rstrip('/')

# Write CSV row (quote fields that may contain commas)
def csv_field(s):
    if ',' in s or '"' in s:
        return f'"{s}"'
    return s

row = ','.join([
    csv_field(linkedin_url),
    csv_field(child_id),
    csv_field(child_name),
    csv_field(parent_name),
    csv_field(parent_domain)
])
print(row)
PYEOF

  done <<< "$CHILD_IDS"

  echo ""

done | tee -a "$OUTPUT_CSV" | grep -v "^$" | wc -l | xargs -I{} echo "  Total rows added to CSV: {}"

echo ""

# ---- Summary ----
TOTAL_ROWS=$(wc -l < "$OUTPUT_CSV")
TOTAL_ROWS=$((TOTAL_ROWS - 1))  # subtract header
MISSING_LINKEDIN=$(tail -n +2 "$OUTPUT_CSV" | python3 -c "
import sys, csv
reader = csv.reader(sys.stdin)
missing = sum(1 for row in reader if not row[0].strip())
print(missing)
")

echo "============================================================"
echo "  Extraction Complete"
echo "  Total child companies: ${TOTAL_ROWS}"
echo "  Missing LinkedIn URLs: ${MISSING_LINKEDIN}"
if [[ "$MISSING_LINKEDIN" -gt 0 ]]; then
  echo ""
  echo "  ACTION REQUIRED: ${MISSING_LINKEDIN} companies have no LinkedIn URL."
  echo "  Run Task 4.2b (Clay enrichment) for those companies before importing."
  echo "  Filter them out: grep '^,' ${OUTPUT_CSV}"
fi
echo ""
echo "  Output: ${OUTPUT_CSV}"
echo "  Next step: import into Clay mapping table (Task 4.3)"
echo "============================================================"
echo ""
