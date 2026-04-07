/**
 * Shared CSV column mapping utilities.
 * Used by both the table builder's CSV import dialog and the /enrich wizard.
 */

export type MatchConfidence = "exact" | "fuzzy" | null;

/** A target that CSV headers can be mapped to */
export interface MappingTarget {
  id: string;        // Column ID (used as key in mapping)
  name: string;      // Display name
  type: string;      // Data type hint
  required: boolean; // Whether this must be mapped
  description: string;
}

/**
 * Normalize a string for comparison — lowercase, strip separators.
 */
export function normalize(s: string): string {
  return s.toLowerCase().replace(/[-_\s]+/g, "");
}

export const SYNONYMS: Record<string, string[]> = {
  url: ["website", "domain", "link", "homepage", "site", "web"],
  domain: ["website", "url", "companydomain", "site"],
  email: ["emailaddress", "workemail", "mail"],
  company: ["companyname", "organization", "org", "account"],
  companyname: ["company", "organization", "org"],
  name: ["fullname", "contactname", "personname"],
  fullname: ["name", "contactname"],
  firstname: ["fname", "givenname", "first"],
  lastname: ["lname", "surname", "familyname", "last"],
  query: ["searchterm", "keyword", "search", "q"],
  linkedinurl: ["linkedin", "liurl", "linkedinprofile"],
  title: ["jobtitle", "position", "role"],
};

/**
 * Auto-map CSV headers to mapping targets.
 * Returns { targetId: csvHeader } and confidence per target.
 *
 * Priority: exact match → synonym match → substring containment.
 */
export function autoMapHeaders(
  targets: MappingTarget[],
  headers: string[],
): { mappings: Record<string, string>; confidence: Record<string, MatchConfidence> } {
  const mappings: Record<string, string> = {};
  const confidence: Record<string, MatchConfidence> = {};

  for (const target of targets) {
    const targetNorm = normalize(target.id);
    const nameNorm = normalize(target.name);

    // 1. Exact match on id or name
    const exact = headers.find(
      (h) => normalize(h) === targetNorm || normalize(h) === nameNorm,
    );
    if (exact) {
      mappings[target.id] = exact;
      confidence[target.id] = "exact";
      continue;
    }

    // 2. Synonym match
    const syns = SYNONYMS[targetNorm] || SYNONYMS[nameNorm] || [];
    const synMatch = headers.find((h) => syns.includes(normalize(h)));
    if (synMatch) {
      mappings[target.id] = synMatch;
      confidence[target.id] = "fuzzy";
      continue;
    }

    // 3. Substring containment
    const subMatch = headers.find((h) => {
      const hNorm = normalize(h);
      return (
        hNorm.includes(targetNorm) || targetNorm.includes(hNorm) ||
        hNorm.includes(nameNorm) || nameNorm.includes(hNorm)
      );
    });
    if (subMatch) {
      mappings[target.id] = subMatch;
      confidence[target.id] = "fuzzy";
    }
  }

  return { mappings, confidence };
}
