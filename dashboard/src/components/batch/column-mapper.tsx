"use client";

import { SKILL_FIELDS } from "@/lib/constants";

export function ColumnMapper({
  skill,
  csvHeaders,
  mapping,
  onMappingChange,
}: {
  skill: string;
  csvHeaders: string[];
  mapping: Record<string, string>;
  onMappingChange: (mapping: Record<string, string>) => void;
}) {
  const fields = SKILL_FIELDS[skill] || [];

  return (
    <div className="rounded-xl border border-zinc-800 bg-zinc-900 p-4">
      <h3 className="text-xs text-zinc-500 uppercase tracking-wide mb-3">
        Column Mapping
      </h3>
      <div className="grid grid-cols-2 gap-3">
        {fields.map((field) => (
          <div key={field} className="flex items-center gap-2">
            <span className="w-36 text-sm text-zinc-300 font-mono truncate">
              {field}
            </span>
            <select
              value={mapping[field] || ""}
              onChange={(e) =>
                onMappingChange({ ...mapping, [field]: e.target.value })
              }
              className="flex-1 rounded-lg border border-zinc-700 bg-zinc-800 px-2 py-1.5 text-sm text-zinc-100 focus:border-teal-500 focus:outline-none"
            >
              <option value="">— skip —</option>
              {csvHeaders.map((h) => (
                <option key={h} value={h}>
                  {h}
                </option>
              ))}
            </select>
          </div>
        ))}
      </div>
    </div>
  );
}

export function autoMap(
  skill: string,
  csvHeaders: string[]
): Record<string, string> {
  const fields = SKILL_FIELDS[skill] || [];
  const mapping: Record<string, string> = {};
  const normalize = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, "");

  for (const field of fields) {
    const nf = normalize(field);
    const match = csvHeaders.find((h) => normalize(h) === nf);
    if (match) mapping[field] = match;
  }
  return mapping;
}
