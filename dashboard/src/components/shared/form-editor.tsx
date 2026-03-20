"use client";

import { useState, useEffect, useCallback } from "react";
import { cn } from "@/lib/utils";
import { Textarea } from "@/components/ui/textarea";
import { fetchClients } from "@/lib/api";
import type { ClientSummary } from "@/lib/types";
import type { SkillFieldMeta } from "@/lib/constants";
import { SKILL_FIELDS } from "@/lib/constants";

const SIGNAL_TYPES = [
  { value: "expansion", label: "Expansion" },
  { value: "funding", label: "Funding" },
  { value: "leadership", label: "Leadership Change" },
  { value: "technology", label: "Tech Migration" },
  { value: "competitive", label: "Competitor Displacement" },
  { value: "product_launch", label: "Product Launch" },
  { value: "promotion", label: "Promotion" },
  { value: "referral", label: "Referral" },
];

const SEQUENCE_TYPES = [
  { value: "cold", label: "Cold Outbound" },
  { value: "linkedin-first", label: "LinkedIn-First" },
  { value: "warm-intro", label: "Warm Intro" },
];

const INDUSTRIES = [
  "AI / Machine Learning",
  "Cloud Infrastructure",
  "Cybersecurity",
  "Data Analytics",
  "Developer Tools",
  "E-Commerce",
  "EdTech",
  "Fintech / APIs",
  "HealthTech",
  "HR Tech / SaaS",
  "MarTech",
  "Observability / SaaS",
  "Productivity / SaaS",
  "Sales Tech",
  "Video Communication / SaaS",
  "Video Platform / SaaS",
];

function toLabel(fieldName: string): string {
  return fieldName
    .replace(/_/g, " ")
    .replace(/\b\w/g, (c) => c.toUpperCase());
}

export function FormEditor({
  dataJson,
  onDataChange,
  skill,
  isSequenceLab = false,
}: {
  dataJson: string;
  onDataChange: (v: string) => void;
  skill: string;
  isSequenceLab?: boolean;
}) {
  const [clients, setClients] = useState<ClientSummary[]>([]);

  // Load clients for dropdown
  useEffect(() => {
    fetchClients()
      .then((r) => setClients(r.clients))
      .catch(() => setClients([]));
  }, []);

  // Parse current JSON
  let data: Record<string, unknown> = {};
  try {
    data = JSON.parse(dataJson);
  } catch {
    // Invalid JSON — show empty form
  }

  // Get field definitions for current skill
  const fields: SkillFieldMeta[] = SKILL_FIELDS[skill] ?? [];

  // Also collect any extra fields not in the schema
  const knownFieldNames = new Set(fields.map((f) => f.name));
  const extraFields = Object.keys(data).filter(
    (k) => !knownFieldNames.has(k) && k !== "_meta"
  );

  const updateField = useCallback(
    (field: string, value: unknown) => {
      let current: Record<string, unknown> = {};
      try {
        current = JSON.parse(dataJson);
      } catch {
        // start fresh
      }
      if (value === "" || value === undefined) {
        delete current[field];
      } else {
        current[field] = value;
      }
      onDataChange(JSON.stringify(current, null, 2));
    },
    [dataJson, onDataChange]
  );

  const renderField = (field: SkillFieldMeta) => {
    const value = (data[field.name] as string | number) ?? "";

    // Special dropdowns
    if (field.name === "signal_type") {
      return (
        <div key={field.name} className="space-y-1">
          <label className="text-xs font-medium text-clay-300">
            {toLabel(field.name)}
            {field.required && <span className="text-red-400 ml-0.5">*</span>}
          </label>
          <select
            value={String(value)}
            onChange={(e) => updateField(field.name, e.target.value)}
            className="w-full rounded-lg border border-clay-700 bg-clay-800 text-clay-200 text-sm px-3 py-2 outline-none focus:border-kiln-teal"
          >
            <option value="">Select signal type...</option>
            {SIGNAL_TYPES.map((st) => (
              <option key={st.value} value={st.value}>
                {st.label}
              </option>
            ))}
          </select>
        </div>
      );
    }

    if (field.name === "sequence_type") {
      return (
        <div key={field.name} className="space-y-1">
          <label className="text-xs font-medium text-clay-300">
            {toLabel(field.name)}
          </label>
          <select
            value={String(value)}
            onChange={(e) => updateField(field.name, e.target.value)}
            className="w-full rounded-lg border border-clay-700 bg-clay-800 text-clay-200 text-sm px-3 py-2 outline-none focus:border-kiln-teal"
          >
            {SEQUENCE_TYPES.map((st) => (
              <option key={st.value} value={st.value}>
                {st.label}
              </option>
            ))}
          </select>
        </div>
      );
    }

    if (field.name === "client_slug") {
      return (
        <div key={field.name} className="space-y-1">
          <label className="text-xs font-medium text-clay-300">Client</label>
          <select
            value={String(value)}
            onChange={(e) => updateField(field.name, e.target.value)}
            className="w-full rounded-lg border border-clay-700 bg-clay-800 text-clay-200 text-sm px-3 py-2 outline-none focus:border-kiln-teal"
          >
            <option value="">Select client...</option>
            {clients.map((c) => (
              <option key={c.slug} value={c.slug}>
                {c.name ?? c.slug}
              </option>
            ))}
          </select>
        </div>
      );
    }

    if (field.name === "industry") {
      return (
        <div key={field.name} className="space-y-1">
          <label className="text-xs font-medium text-clay-300">Industry</label>
          <select
            value={String(value)}
            onChange={(e) => updateField(field.name, e.target.value)}
            className="w-full rounded-lg border border-clay-700 bg-clay-800 text-clay-200 text-sm px-3 py-2 outline-none focus:border-kiln-teal"
          >
            <option value="">Select industry...</option>
            {INDUSTRIES.map((ind) => (
              <option key={ind} value={ind}>
                {ind}
              </option>
            ))}
            {/* Allow custom value if not in list */}
            {value && !INDUSTRIES.includes(String(value)) && (
              <option value={String(value)}>{String(value)}</option>
            )}
          </select>
          <input
            type="text"
            value={String(value)}
            onChange={(e) => updateField(field.name, e.target.value)}
            placeholder="Or type custom..."
            className="w-full rounded-lg border border-clay-700 bg-clay-950 text-clay-200 text-xs px-3 py-1.5 outline-none focus:border-kiln-teal/50"
          />
        </div>
      );
    }

    // Textarea for long-form fields
    if (
      field.type === "textarea" ||
      field.name === "signal_detail" ||
      field.name.includes("detail") ||
      field.name.includes("notes") ||
      field.name.includes("summary")
    ) {
      return (
        <div key={field.name} className="space-y-1">
          <label className="text-xs font-medium text-clay-300">
            {toLabel(field.name)}
            {field.required && <span className="text-red-400 ml-0.5">*</span>}
          </label>
          <textarea
            value={String(value)}
            onChange={(e) => updateField(field.name, e.target.value)}
            placeholder={field.placeholder}
            rows={3}
            className="w-full rounded-lg border border-clay-700 bg-clay-950 text-clay-200 text-sm px-3 py-2 outline-none focus:border-kiln-teal/50 resize-none leading-relaxed"
          />
        </div>
      );
    }

    // Number input
    if (field.type === "number") {
      return (
        <div key={field.name} className="space-y-1">
          <label className="text-xs font-medium text-clay-300">
            {toLabel(field.name)}
            {field.required && <span className="text-red-400 ml-0.5">*</span>}
          </label>
          <input
            type="number"
            value={value === "" ? "" : Number(value)}
            onChange={(e) =>
              updateField(
                field.name,
                e.target.value ? Number(e.target.value) : ""
              )
            }
            placeholder={field.placeholder}
            className="w-full rounded-lg border border-clay-700 bg-clay-950 text-clay-200 text-sm px-3 py-2 outline-none focus:border-kiln-teal/50"
          />
        </div>
      );
    }

    // Default: text input
    return (
      <div key={field.name} className="space-y-1">
        <label className="text-xs font-medium text-clay-300">
          {toLabel(field.name)}
          {field.required && <span className="text-red-400 ml-0.5">*</span>}
        </label>
        <input
          type="text"
          value={String(value)}
          onChange={(e) => updateField(field.name, e.target.value)}
          placeholder={field.placeholder}
          className="w-full rounded-lg border border-clay-700 bg-clay-950 text-clay-200 text-sm px-3 py-2 outline-none focus:border-kiln-teal/50"
        />
      </div>
    );
  };

  // Sequence Lab gets sequence_type if not already in fields
  const showSequenceType =
    isSequenceLab && !fields.some((f) => f.name === "sequence_type");

  return (
    <div className="space-y-3 overflow-y-auto h-full pr-1">
      {/* Sequence type quick selector for Sequence Lab */}
      {showSequenceType && (
        <div className="space-y-1">
          <label className="text-xs font-medium text-clay-300">
            Sequence Type
          </label>
          <select
            value={(data.sequence_type as string) ?? "cold"}
            onChange={(e) => updateField("sequence_type", e.target.value)}
            className="w-full rounded-lg border border-clay-700 bg-clay-800 text-clay-200 text-sm px-3 py-2 outline-none focus:border-kiln-teal"
          >
            {SEQUENCE_TYPES.map((st) => (
              <option key={st.value} value={st.value}>
                {st.label}
              </option>
            ))}
          </select>
        </div>
      )}

      {/* Render known fields */}
      {fields.map(renderField)}

      {/* Render extra fields from data that aren't in the schema */}
      {extraFields.length > 0 && (
        <div className="pt-2 border-t border-clay-700/50 space-y-3">
          <p className="text-[10px] text-clay-300 uppercase tracking-wider font-medium">
            Additional Fields
          </p>
          {extraFields.map((key) => {
            const val = data[key];
            return (
              <div key={key} className="space-y-1">
                <label className="text-xs font-medium text-clay-300">
                  {toLabel(key)}
                </label>
                {typeof val === "string" && val.length > 80 ? (
                  <textarea
                    value={String(val)}
                    onChange={(e) => updateField(key, e.target.value)}
                    rows={2}
                    className="w-full rounded-lg border border-clay-700 bg-clay-950 text-clay-200 text-sm px-3 py-2 outline-none focus:border-kiln-teal/50 resize-none"
                  />
                ) : (
                  <input
                    type="text"
                    value={String(val ?? "")}
                    onChange={(e) => updateField(key, e.target.value)}
                    className="w-full rounded-lg border border-clay-700 bg-clay-950 text-clay-200 text-sm px-3 py-2 outline-none focus:border-kiln-teal/50"
                  />
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* No fields fallback */}
      {fields.length === 0 && extraFields.length === 0 && (
        <div className="text-center py-6 text-clay-300 text-xs">
          <p>No field definitions found for this skill.</p>
          <p className="mt-1">Switch to JSON mode to enter data.</p>
        </div>
      )}
    </div>
  );
}
