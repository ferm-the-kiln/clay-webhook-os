"use client";

import { useState, useEffect, useCallback } from "react";
import { SKILL_FIELDS, type SkillFieldMeta } from "@/lib/constants";
import { Card, CardContent } from "@/components/ui/card";
import { Textarea } from "@/components/ui/textarea";
import { Code, ListChecks } from "lucide-react";

function parseJsonError(message: string): string {
  const posMatch = message.match(/position (\d+)/);
  if (posMatch) return `Invalid JSON at position ${posMatch[1]}`;
  const lineMatch = message.match(/line (\d+) column (\d+)/);
  if (lineMatch) return `Invalid JSON at line ${lineMatch[1]}, column ${lineMatch[2]}`;
  return message.replace(/^(SyntaxError: )?/, "Invalid JSON: ");
}

function FormFields({
  fields,
  values,
  onChange,
}: {
  fields: SkillFieldMeta[];
  values: Record<string, unknown>;
  onChange: (updated: Record<string, unknown>) => void;
}) {
  const handleFieldChange = (name: string, value: string | number) => {
    onChange({ ...values, [name]: value === "" ? undefined : value });
  };

  return (
    <div className="space-y-3 p-4">
      {fields.map((f) => {
        const val = values[f.name];
        const strVal = val !== undefined && val !== null ? String(val) : "";
        return (
          <div key={f.name}>
            <label className="block text-xs text-clay-200 mb-1 font-[family-name:var(--font-sans)]">
              {f.name.replace(/_/g, " ")}
              {f.required && <span className="text-kiln-coral ml-0.5">*</span>}
            </label>
            {f.type === "textarea" ? (
              <textarea
                value={strVal}
                onChange={(e) => handleFieldChange(f.name, e.target.value)}
                placeholder={f.placeholder}
                rows={3}
                className="w-full rounded-md border border-clay-700 bg-clay-800 px-3 py-2 text-sm text-clay-100 placeholder:text-clay-300 focus:border-kiln-teal focus:outline-none resize-y"
              />
            ) : (
              <input
                type={f.type === "number" ? "number" : "text"}
                value={strVal}
                onChange={(e) =>
                  handleFieldChange(
                    f.name,
                    f.type === "number" && e.target.value ? Number(e.target.value) : e.target.value
                  )
                }
                placeholder={f.placeholder}
                className="w-full rounded-md border border-clay-700 bg-clay-800 px-3 py-2 text-sm text-clay-100 placeholder:text-clay-300 focus:border-kiln-teal focus:outline-none"
              />
            )}
          </div>
        );
      })}
    </div>
  );
}

export function FormEditor({
  value,
  onChange,
  skill,
}: {
  value: string;
  onChange: (v: string) => void;
  skill: string;
}) {
  const fields = SKILL_FIELDS[skill];
  const hasForm = !!fields;
  const [mode, setMode] = useState<"form" | "json">(hasForm ? "form" : "json");
  const [error, setError] = useState<string | null>(null);

  // Reset to form mode when skill changes and has fields
  useEffect(() => {
    setMode(SKILL_FIELDS[skill] ? "form" : "json");
  }, [skill]);

  useEffect(() => {
    try {
      JSON.parse(value);
      setError(null);
    } catch (e) {
      setError(parseJsonError((e as Error).message));
    }
  }, [value]);

  const parsedValues = useCallback((): Record<string, unknown> => {
    try {
      return JSON.parse(value);
    } catch {
      return {};
    }
  }, [value]);

  const handleFormChange = (updated: Record<string, unknown>) => {
    // Remove undefined values
    const clean: Record<string, unknown> = {};
    for (const [k, v] of Object.entries(updated)) {
      if (v !== undefined) clean[k] = v;
    }
    onChange(JSON.stringify(clean, null, 2));
  };

  return (
    <div className="flex-1 flex flex-col">
      <div className="flex items-center justify-between mb-1.5">
        <label className="text-xs text-clay-200 uppercase tracking-wider font-[family-name:var(--font-sans)]">
          Data {mode === "json" ? "(JSON)" : "(Form)"}
        </label>
        <div className="flex items-center gap-1">
          {error && mode === "json" && (
            <span className="text-xs text-kiln-coral truncate max-w-[200px] mr-2" title={error}>
              {error}
            </span>
          )}
          {hasForm && (
            <>
              <button
                onClick={() => setMode("form")}
                className={`p-1 rounded transition-colors ${
                  mode === "form" ? "text-kiln-teal bg-kiln-teal/10" : "text-clay-200 hover:text-clay-300"
                }`}
                title="Form mode"
              >
                <ListChecks className="h-3.5 w-3.5" />
              </button>
              <button
                onClick={() => setMode("json")}
                className={`p-1 rounded transition-colors ${
                  mode === "json" ? "text-kiln-teal bg-kiln-teal/10" : "text-clay-200 hover:text-clay-300"
                }`}
                title="JSON mode"
              >
                <Code className="h-3.5 w-3.5" />
              </button>
            </>
          )}
        </div>
      </div>
      <Card
        className={`flex-1 border-clay-700 bg-clay-800 ${
          error && mode === "json" ? "border-kiln-coral/50" : ""
        }`}
      >
        <CardContent className="p-0 h-full">
          {mode === "form" && fields ? (
            <div className="overflow-auto max-h-[400px]">
              <FormFields
                fields={fields}
                values={parsedValues()}
                onChange={handleFormChange}
              />
            </div>
          ) : (
            <textarea
              value={value}
              onChange={(e) => onChange(e.target.value)}
              spellCheck={false}
              className="w-full h-full min-h-[200px] max-h-[400px] rounded-lg bg-transparent px-4 py-3 font-[family-name:var(--font-mono)] text-sm text-clay-100 focus:outline-none resize-y placeholder:text-clay-300"
              placeholder='{ "key": "value" }'
            />
          )}
        </CardContent>
      </Card>
    </div>
  );
}
