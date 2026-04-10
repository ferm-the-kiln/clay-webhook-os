const TEXT_FIELD_PRIORITY = [
  "summary",
  "content",
  "answer",
  "result",
  "text",
  "research",
  "output",
  "message",
  "description",
  "value",
];

export function extractPreviewText(value: unknown): string {
  if (value === null || value === undefined) return "";
  if (typeof value === "string") return value;
  if (typeof value === "number" || typeof value === "boolean") return String(value);

  if (Array.isArray(value)) {
    if (value.length === 0) return "";
    const first = value[0];
    if (typeof first === "string") return value.slice(0, 3).join(", ");
    return `${value.length} item${value.length === 1 ? "" : "s"}`;
  }

  if (typeof value === "object") {
    const obj = value as Record<string, unknown>;
    for (const key of TEXT_FIELD_PRIORITY) {
      const v = obj[key];
      if (typeof v === "string" && v.trim()) return v;
    }
    for (const [, v] of Object.entries(obj)) {
      if (typeof v === "string" && v.trim()) return v;
    }
    const keys = Object.keys(obj);
    return `${keys.length} field${keys.length === 1 ? "" : "s"}`;
  }

  return String(value);
}
