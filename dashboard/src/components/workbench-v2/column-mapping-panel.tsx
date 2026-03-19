"use client";

import type { FunctionDefinition } from "@/lib/types";
import type { ColumnMapping, MatchConfidence } from "@/hooks/use-function-workbench";
import { cn } from "@/lib/utils";
import { Badge } from "@/components/ui/badge";
import { Separator } from "@/components/ui/separator";
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";
import { ArrowRight, X } from "lucide-react";

interface ColumnMappingPanelProps {
  func: FunctionDefinition;
  csvHeaders: string[];
  mappings: ColumnMapping[];
  autoMapConfidence: Record<string, MatchConfidence>;
  onMapColumn: (csvCol: string, funcInput: string) => void;
  onClearMapping: (funcInput: string) => void;
}

export function ColumnMappingPanel({
  func,
  csvHeaders,
  mappings,
  autoMapConfidence,
  onMapColumn,
  onClearMapping,
}: ColumnMappingPanelProps) {
  const requiredInputs = func.inputs.filter((i) => i.required);
  const optionalInputs = func.inputs.filter((i) => !i.required);

  return (
    <div>
      <h3 className="text-sm font-medium text-clay-200 mb-3">Column Mapping</h3>

      {/* Required inputs */}
      {requiredInputs.length > 0 && (
        <div className="space-y-1.5 mb-3">
          <div className="text-[10px] text-clay-400 uppercase tracking-wider font-medium">
            Required Inputs
          </div>
          {requiredInputs.map((input) => (
            <MappingRow
              key={input.name}
              inputName={input.name}
              inputType={input.type}
              inputDescription={input.description}
              required
              csvHeaders={csvHeaders}
              mapping={mappings.find((m) => m.functionInput === input.name)}
              confidence={autoMapConfidence[input.name]}
              onMap={(csvCol) => onMapColumn(csvCol, input.name)}
              onClear={() => onClearMapping(input.name)}
            />
          ))}
        </div>
      )}

      {/* Separator */}
      {requiredInputs.length > 0 && optionalInputs.length > 0 && (
        <Separator className="my-3" />
      )}

      {/* Optional inputs */}
      {optionalInputs.length > 0 && (
        <div className="space-y-1.5">
          <div className="text-[10px] text-clay-400 uppercase tracking-wider font-medium">
            Optional Inputs
          </div>
          {optionalInputs.map((input) => (
            <MappingRow
              key={input.name}
              inputName={input.name}
              inputType={input.type}
              inputDescription={input.description}
              required={false}
              csvHeaders={csvHeaders}
              mapping={mappings.find((m) => m.functionInput === input.name)}
              confidence={autoMapConfidence[input.name]}
              onMap={(csvCol) => onMapColumn(csvCol, input.name)}
              onClear={() => onClearMapping(input.name)}
            />
          ))}
        </div>
      )}
    </div>
  );
}

function MappingRow({
  inputName,
  inputType,
  inputDescription,
  required,
  csvHeaders,
  mapping,
  confidence,
  onMap,
  onClear,
}: {
  inputName: string;
  inputType: string;
  inputDescription: string;
  required: boolean;
  csvHeaders: string[];
  mapping: ColumnMapping | undefined;
  confidence: MatchConfidence | undefined;
  onMap: (csvCol: string) => void;
  onClear: () => void;
}) {
  const isMapped = !!mapping;

  return (
    <div
      className={cn(
        "flex items-center gap-2 p-2 rounded-md border transition-colors",
        !isMapped && required
          ? "border-red-500/30 bg-red-500/5"
          : isMapped
            ? "border-kiln-teal/20 bg-kiln-teal/5"
            : "border-clay-700 bg-clay-800/30"
      )}
    >
      {/* Input info */}
      <div className="flex items-center gap-2 min-w-0 flex-1">
        {/* Confidence dot */}
        {confidence && (
          <div
            className={cn(
              "h-2 w-2 rounded-full shrink-0",
              confidence === "exact" && "bg-green-400",
              confidence === "fuzzy" && "bg-yellow-400",
              confidence === "manual" && "bg-clay-400"
            )}
            title={`${confidence} match`}
          />
        )}
        {!confidence && !isMapped && required && (
          <div className="h-2 w-2 rounded-full bg-red-400 animate-pulse shrink-0" />
        )}

        <span className="text-xs font-mono font-medium text-clay-100 truncate">
          {inputName}
        </span>
        <Badge variant="secondary" className="text-[9px] px-1 py-0 shrink-0">
          {inputType}
        </Badge>
        {inputDescription && (
          <span className="text-[10px] text-clay-500 truncate hidden sm:inline">
            {inputDescription}
          </span>
        )}
      </div>

      {/* Arrow */}
      <ArrowRight className="h-3 w-3 text-clay-500 shrink-0" />

      {/* CSV column selector */}
      <div className="flex items-center gap-1 shrink-0">
        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button
              className={cn(
                "text-xs px-2 py-1 rounded border transition-colors min-w-[120px] text-left",
                isMapped
                  ? "border-kiln-teal/30 text-kiln-teal bg-kiln-teal/5"
                  : "border-clay-600 text-clay-400 hover:text-clay-200 hover:border-clay-500"
              )}
            >
              {mapping ? mapping.csvColumn : "Select column..."}
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent className="bg-clay-800 border-clay-600 max-h-48 overflow-auto">
            {csvHeaders.map((h) => (
              <DropdownMenuItem
                key={h}
                onClick={() => onMap(h)}
                className="text-xs"
              >
                {h}
              </DropdownMenuItem>
            ))}
          </DropdownMenuContent>
        </DropdownMenu>

        {isMapped && (
          <button
            onClick={onClear}
            className="p-0.5 text-clay-500 hover:text-clay-200 transition-colors"
            title="Clear mapping"
          >
            <X className="h-3 w-3" />
          </button>
        )}
      </div>
    </div>
  );
}
