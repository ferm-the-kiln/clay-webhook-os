import type { TableColumn } from "./types";

interface ToolInput {
  name: string;
  type: string;
}

/**
 * Synonym table: tool input name → likely column names
 */
const SYNONYMS: Record<string, string[]> = {
  url: ["website", "domain", "link", "homepage", "site", "web"],
  domain: ["website", "url", "company_domain", "site"],
  website: ["url", "domain", "link", "homepage", "site"],
  email: ["email_address", "work_email", "personal_email", "mail"],
  company: ["company_name", "organization", "org", "account"],
  company_name: ["company", "organization", "org", "account"],
  name: ["full_name", "contact_name", "person_name"],
  full_name: ["name", "contact_name", "person_name"],
  first_name: ["fname", "given_name", "first"],
  last_name: ["lname", "surname", "family_name", "last"],
  query: ["search_term", "keyword", "search", "q"],
  linkedin_url: ["linkedin", "li_url", "linkedin_profile"],
  linkedin: ["linkedin_url", "li_url", "linkedin_profile"],
  title: ["job_title", "position", "role"],
  phone: ["phone_number", "mobile", "cell", "telephone"],
  location: ["city", "address", "region", "geo"],
};

/**
 * Normalize a string for comparison: lowercase, strip underscores/hyphens/spaces
 */
function normalize(s: string): string {
  return s.toLowerCase().replace(/[-_\s]+/g, "");
}

/**
 * Auto-map tool inputs to available columns by fuzzy name matching.
 * Returns a Record<inputName, "{{column_id}}"> for matched inputs.
 */
export function autoMapInputs(
  toolInputs: ToolInput[],
  availableColumns: TableColumn[],
): Record<string, string> {
  const result: Record<string, string> = {};
  const inputCols = availableColumns.filter(
    (c) => c.column_type === "input" || c.column_type === "static",
  );

  if (inputCols.length === 0) return result;

  for (const input of toolInputs) {
    const match = findBestMatch(input.name, inputCols);
    if (match) {
      result[input.name] = `{{${match.id}}}`;
    }
  }

  // Single-candidate fallback: if exactly 1 unmapped required input and exactly 1 input column
  if (toolInputs.length === 1 && inputCols.length === 1 && !result[toolInputs[0].name]) {
    result[toolInputs[0].name] = `{{${inputCols[0].id}}}`;
  }

  return result;
}

function findBestMatch(
  inputName: string,
  columns: TableColumn[],
): TableColumn | null {
  const normalizedInput = normalize(inputName);

  // 1. Exact name match (case-insensitive, normalized)
  for (const col of columns) {
    if (normalize(col.name) === normalizedInput || normalize(col.id) === normalizedInput) {
      return col;
    }
  }

  // 2. Synonym match
  const synonyms = SYNONYMS[inputName.toLowerCase()] || [];
  for (const col of columns) {
    const colNorm = normalize(col.name);
    const colIdNorm = normalize(col.id);
    for (const syn of synonyms) {
      if (colNorm === normalize(syn) || colIdNorm === normalize(syn)) {
        return col;
      }
    }
  }

  // 3. Substring containment (either direction)
  for (const col of columns) {
    const colNorm = normalize(col.name);
    const colIdNorm = normalize(col.id);
    if (
      colNorm.includes(normalizedInput) ||
      normalizedInput.includes(colNorm) ||
      colIdNorm.includes(normalizedInput) ||
      normalizedInput.includes(colIdNorm)
    ) {
      return col;
    }
  }

  return null;
}
