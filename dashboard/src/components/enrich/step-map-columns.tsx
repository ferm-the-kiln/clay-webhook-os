"use client";

import { useState, useEffect, useCallback } from "react";
import { ArrowRight, X, Check } from "lucide-react";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { autoMapHeaders, type MappingTarget, type MatchConfidence } from "@/lib/csv-utils";
import type { WorkflowTemplate } from "@/lib/types";

interface StepMapColumnsProps {
  csvHeaders: string[];
  selectedRecipes: WorkflowTemplate[];
  /** Callback with { csvHeader: roleColumnId } mapping */
  onMappingChange: (mapping: Record<string, string>, allRequiredMapped: boolean) => void;
}

export function StepMapColumns({
  csvHeaders,
  selectedRecipes,
  onMappingChange,
}: StepMapColumnsProps) {
  // Deduplicate roles across all selected recipes
  const roleMap = new Map<string, { name: string; description: string; required: boolean }>();
  for (const recipe of selectedRecipes) {
    for (const input of recipe.expected_inputs) {
      const existing = roleMap.get(input.name);
      // If any recipe requires it, it's required
      const required = input.required !== false;
      if (!existing || required) {
        roleMap.set(input.name, {
          name: input.name,
          description: input.description,
          required: existing ? existing.required || required : required,
        });
      }
    }
  }

  const targets: MappingTarget[] = Array.from(roleMap.entries()).map(([id, r]) => ({
    id,
    name: r.name,
    type: "string",
    required: r.required,
    description: r.description,
  }));

  const requiredTargets = targets.filter((t) => t.required);
  const optionalTargets = targets.filter((t) => !t.required);

  // { targetId: csvHeader }
  const [mappings, setMappings] = useState<Record<string, string>>({});
  const [confidence, setConfidence] = useState<Record<string, MatchConfidence>>({});

  // Auto-map on mount
  useEffect(() => {
    const result = autoMapHeaders(targets, csvHeaders);
    setMappings(result.mappings);
    setConfidence(result.confidence);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [csvHeaders.join(","), selectedRecipes.map((r) => r.id).join(",")]);

  // Notify parent of mapping changes
  useEffect(() => {
    const unmappedRequired = requiredTargets.filter((t) => !mappings[t.id]);
    // Build { csvHeader: roleColumnId } for the import API
    const columnMapping: Record<string, string> = {};
    for (const [targetId, csvHeader] of Object.entries(mappings)) {
      columnMapping[csvHeader] = targetId;
    }
    onMappingChange(columnMapping, unmappedRequired.length === 0);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [mappings]);

  const handleMap = useCallback((targetId: string, csvHeader: string) => {
    setMappings((prev) => ({ ...prev, [targetId]: csvHeader }));
    setConfidence((prev) => ({ ...prev, [targetId]: "exact" as MatchConfidence }));
  }, []);

  const handleClear = useCallback((targetId: string) => {
    setMappings((prev) => {
      const next = { ...prev };
      delete next[targetId];
      return next;
    });
    setConfidence((prev) => {
      const next = { ...prev };
      delete next[targetId];
      return next;
    });
  }, []);

  const mappedHeaders = new Set(Object.values(mappings));
  const unmappedHeaders = csvHeaders.filter((h) => !mappedHeaders.has(h));

  return (
    <div className="space-y-6">
      <div className="text-center space-y-1">
        <h2 className="text-lg font-semibold text-clay-100">Map your columns</h2>
        <p className="text-sm text-clay-400">
          We auto-detected most of these. Confirm or adjust.
        </p>
      </div>

      <div className="space-y-4">
        {/* Required */}
        {requiredTargets.length > 0 && (
          <div className="space-y-1.5">
            <div className="text-[10px] text-clay-500 uppercase tracking-wider font-medium">
              Required
            </div>
            {requiredTargets.map((target) => (
              <MappingRow
                key={target.id}
                target={target}
                csvHeaders={csvHeaders}
                mappedTo={mappings[target.id]}
                matchConfidence={confidence[target.id]}
                onMap={(h) => handleMap(target.id, h)}
                onClear={() => handleClear(target.id)}
              />
            ))}
          </div>
        )}

        {/* Optional */}
        {optionalTargets.length > 0 && (
          <div className="space-y-1.5">
            <div className="text-[10px] text-clay-500 uppercase tracking-wider font-medium">
              Optional
            </div>
            {optionalTargets.map((target) => (
              <MappingRow
                key={target.id}
                target={target}
                csvHeaders={csvHeaders}
                mappedTo={mappings[target.id]}
                matchConfidence={confidence[target.id]}
                onMap={(h) => handleMap(target.id, h)}
                onClear={() => handleClear(target.id)}
              />
            ))}
          </div>
        )}

        {/* Unmapped CSV columns */}
        {unmappedHeaders.length > 0 && (
          <div className="pt-3 border-t border-clay-700">
            <div className="text-[10px] text-clay-500 uppercase tracking-wider font-medium mb-1.5">
              Additional columns (imported as-is)
            </div>
            <div className="flex flex-wrap gap-1.5">
              {unmappedHeaders.map((h) => (
                <span
                  key={h}
                  className="text-[11px] px-2 py-0.5 rounded bg-clay-800 text-clay-400 border border-clay-700"
                >
                  {h}
                </span>
              ))}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

function MappingRow({
  target,
  csvHeaders,
  mappedTo,
  matchConfidence,
  onMap,
  onClear,
}: {
  target: MappingTarget;
  csvHeaders: string[];
  mappedTo: string | undefined;
  matchConfidence: MatchConfidence | undefined;
  onMap: (csvHeader: string) => void;
  onClear: () => void;
}) {
  const isMapped = !!mappedTo;

  return (
    <div
      className={`flex items-center gap-2 p-2 rounded-md border transition-colors ${
        !isMapped && target.required
          ? "border-red-500/30 bg-red-500/5"
          : isMapped
            ? "border-kiln-teal/20 bg-kiln-teal/5"
            : "border-clay-700 bg-clay-800/30"
      }`}
    >
      {/* Confidence dot */}
      <div className="w-3 flex justify-center shrink-0">
        {matchConfidence === "exact" && (
          <div className="h-2 w-2 rounded-full bg-green-400" title="Exact match" />
        )}
        {matchConfidence === "fuzzy" && (
          <div className="h-2 w-2 rounded-full bg-yellow-400" title="Fuzzy match" />
        )}
        {!matchConfidence && !isMapped && target.required && (
          <div className="h-2 w-2 rounded-full bg-red-400 animate-pulse" title="Unmapped" />
        )}
      </div>

      {/* Role info */}
      <div className="flex items-center gap-1.5 min-w-0 flex-1">
        <span className="text-xs font-mono font-medium text-clay-200 truncate">
          {target.name}
        </span>
        {target.description && (
          <span className="text-[10px] text-clay-500 truncate hidden sm:inline">
            {target.description}
          </span>
        )}
      </div>

      <ArrowRight className="h-3 w-3 text-clay-500 shrink-0" />

      {/* CSV column selector */}
      <div className="flex items-center gap-1 shrink-0">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              className={`text-xs px-2 py-1 rounded border transition-colors min-w-[140px] text-left truncate ${
                isMapped
                  ? "border-kiln-teal/30 text-kiln-teal bg-kiln-teal/5"
                  : "border-clay-600 text-clay-400 hover:text-clay-300 hover:border-clay-500"
              }`}
            >
              {mappedTo || "Select column..."}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="bg-clay-800 border-clay-600 max-h-48 overflow-auto">
            {csvHeaders.map((h) => (
              <DropdownMenuItem key={h} onClick={() => onMap(h)} className="text-xs">
                {h === mappedTo && <Check className="w-3 h-3 mr-1 text-kiln-teal" />}
                {h}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        {isMapped && (
          <button
            onClick={onClear}
            className="p-0.5 text-clay-500 hover:text-clay-300 transition-colors"
            title="Clear mapping"
          >
            <X className="h-3 w-3" />
          </button>
        )}
      </div>
    </div>
  );
}
