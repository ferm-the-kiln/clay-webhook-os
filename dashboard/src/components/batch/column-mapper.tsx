"use client";

import { SKILL_FIELDS } from "@/lib/constants";
import { Card, CardContent } from "@/components/ui/card";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";

function getFieldNames(skill: string): string[] {
  const raw = SKILL_FIELDS[skill] || [];
  return raw.map((f) => (typeof f === "string" ? f : f.name));
}

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
  const fields = getFieldNames(skill);

  return (
    <Card className="border-clay-800 bg-white shadow-sm">
      <CardContent className="p-4">
        <h3 className="text-xs text-clay-500 uppercase tracking-wider mb-3 font-[family-name:var(--font-sans)]">
          Column Mapping
        </h3>
        <div className="grid grid-cols-2 gap-3">
          {fields.map((field) => (
            <div key={field} className="flex items-center gap-2">
              <span className="w-36 text-sm text-clay-300 font-[family-name:var(--font-mono)] truncate">
                {field}
              </span>
              <Select
                value={mapping[field] || "__skip__"}
                onValueChange={(v) =>
                  onMappingChange({
                    ...mapping,
                    [field]: v === "__skip__" ? "" : v,
                  })
                }
              >
                <SelectTrigger className="flex-1 border-clay-700 bg-clay-850 text-clay-100 text-sm h-8 focus:ring-kiln-teal">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent className="border-clay-700 bg-clay-900">
                  <SelectItem
                    value="__skip__"
                    className="text-clay-500 focus:bg-clay-800"
                  >
                    -- skip --
                  </SelectItem>
                  {csvHeaders.map((h) => (
                    <SelectItem
                      key={h}
                      value={h}
                      className="text-clay-200 focus:bg-kiln-teal/10 focus:text-kiln-teal"
                    >
                      {h}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  );
}

export function autoMap(
  skill: string,
  csvHeaders: string[]
): Record<string, string> {
  const fields = getFieldNames(skill);
  const mapping: Record<string, string> = {};
  const normalize = (s: string) => s.toLowerCase().replace(/[^a-z0-9]/g, "");

  for (const field of fields) {
    const nf = normalize(field);
    const match = csvHeaders.find((h) => normalize(h) === nf);
    if (match) mapping[field] = match;
  }
  return mapping;
}
