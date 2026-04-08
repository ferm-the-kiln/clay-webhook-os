export type FilterOperator =
  | "equals"
  | "not_equals"
  | "contains"
  | "contains_any_of"
  | "does_not_contain"
  | "does_not_contain_any_of"
  | "is_empty"
  | "is_not_empty";

export interface FilterCondition {
  id: string;
  columnId: string;
  operator: FilterOperator;
  value: string;
  enabled: boolean;
}

export const VALUE_LESS_OPERATORS: FilterOperator[] = [
  "is_empty",
  "is_not_empty",
];

export const OPERATOR_LABELS: Record<FilterOperator, string> = {
  equals: "equal to",
  not_equals: "not equal to",
  contains: "contains",
  contains_any_of: "contains any of",
  does_not_contain: "does not contain",
  does_not_contain_any_of: "does not contain any of",
  is_empty: "is empty",
  is_not_empty: "is not empty",
};
