import type { FilterCondition } from "./table-filter-types";
import type { TableRow } from "@/lib/types";

/**
 * Applies all enabled filter conditions to rows (AND logic).
 */
export function applyFilters(
  rows: TableRow[],
  filters: FilterCondition[],
): TableRow[] {
  const active = filters.filter((f) => f.enabled && f.columnId);
  if (active.length === 0) return rows;
  return rows.filter((row) => active.every((f) => matchesCondition(row, f)));
}

function matchesCondition(row: TableRow, filter: FilterCondition): boolean {
  const rawValue = row[`${filter.columnId}__value`];
  const cellStr = normalize(rawValue);

  switch (filter.operator) {
    case "equals":
      return cellStr === normalize(filter.value);
    case "not_equals":
      return cellStr !== normalize(filter.value);
    case "contains":
      return cellStr.includes(normalize(filter.value));
    case "contains_any_of": {
      const tokens = filter.value
        .split(",")
        .map((t) => t.trim().toLowerCase());
      return tokens.some((t) => t && cellStr.includes(t));
    }
    case "does_not_contain":
      return !cellStr.includes(normalize(filter.value));
    case "does_not_contain_any_of": {
      const tokens = filter.value
        .split(",")
        .map((t) => t.trim().toLowerCase());
      return tokens.every((t) => !t || !cellStr.includes(t));
    }
    case "is_empty":
      return rawValue === null || rawValue === undefined || rawValue === "";
    case "is_not_empty":
      return rawValue !== null && rawValue !== undefined && rawValue !== "";
    default:
      return true;
  }
}

function normalize(v: unknown): string {
  if (v === null || v === undefined) return "";
  if (typeof v === "object") return JSON.stringify(v).toLowerCase();
  return String(v).toLowerCase();
}
