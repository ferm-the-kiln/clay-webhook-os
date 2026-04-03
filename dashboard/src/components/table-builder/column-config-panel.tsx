"use client";

import { useState, useEffect } from "react";
import {
  Sheet,
  SheetContent,
  SheetHeader,
  SheetTitle,
  SheetDescription,
} from "@/components/ui/sheet";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
const Label = ({ className, children, ...props }: React.LabelHTMLAttributes<HTMLLabelElement> & { className?: string }) => (
  <label className={className} {...props}>{children}</label>
);
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import {
  Search,
  Brain,
  Calculator,
  Filter,
  Type,
} from "lucide-react";
import type { TableColumn, ToolDefinition } from "@/lib/types";
import { ColumnReferenceInput } from "./column-reference-input";
import { OutputFieldSelector } from "./output-field-selector";
import { autoMapInputs } from "@/lib/auto-map-inputs";

interface ColumnConfigPanelProps {
  open: boolean;
  onClose: () => void;
  onSave: (config: Record<string, unknown>) => Promise<string | void>;
  /** Existing column being edited (null for new) */
  editingColumn: TableColumn | null;
  /** The pre-selected tool for enrichment columns */
  selectedTool: ToolDefinition | null;
  /** Pre-selected column type for new columns */
  initialType: string | null;
  /** Available columns for "/" references (columns to the left) */
  availableColumns: TableColumn[];
  /** Pre-filled params from suggestion bar auto-mapping */
  initialParams?: Record<string, string>;
}

export function ColumnConfigPanel({
  open,
  onClose,
  onSave,
  editingColumn,
  selectedTool,
  initialType,
  availableColumns,
  initialParams,
}: ColumnConfigPanelProps) {
  const [name, setName] = useState("");
  const [columnType, setColumnType] = useState<string>("enrichment");
  const [params, setParams] = useState<Record<string, string>>({});
  const [outputKey, setOutputKey] = useState("");
  const [selectedOutputs, setSelectedOutputs] = useState<string[]>([]);
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiModel, setAiModel] = useState("sonnet");
  const [formula, setFormula] = useState("");
  const [condition, setCondition] = useState("");
  const [conditionLabel, setConditionLabel] = useState("");
  const [autoMapped, setAutoMapped] = useState(false);
  const [saving, setSaving] = useState(false);

  // Initialize from editing column or defaults
  useEffect(() => {
    if (editingColumn) {
      setName(editingColumn.name);
      setColumnType(editingColumn.column_type);
      setParams(editingColumn.params);
      setOutputKey(editingColumn.output_key || "");
      setSelectedOutputs(editingColumn.output_key ? [editingColumn.output_key] : []);
      setAiPrompt(editingColumn.ai_prompt || "");
      setAiModel(editingColumn.ai_model || "sonnet");
      setFormula(editingColumn.formula || "");
      setCondition(editingColumn.condition || "");
      setConditionLabel(editingColumn.condition_label || "");
      setAutoMapped(false);
    } else {
      // New column defaults
      setName(selectedTool?.name || "");
      setColumnType(initialType || "enrichment");
      setOutputKey("");
      setAiPrompt("");
      setAiModel("sonnet");
      setFormula("");
      setCondition("");
      setConditionLabel("");

      // Pre-select first output by default
      if (selectedTool?.outputs && selectedTool.outputs.length > 0) {
        setSelectedOutputs([selectedTool.outputs[0].key]);
      } else {
        setSelectedOutputs([]);
      }

      // Pre-populate params from tool inputs with auto-mapping
      if (selectedTool?.inputs) {
        // Start with initialParams if provided (from suggestions bar)
        if (initialParams && Object.keys(initialParams).length > 0) {
          const merged: Record<string, string> = {};
          for (const input of selectedTool.inputs) {
            merged[input.name] = initialParams[input.name] || "";
          }
          setParams(merged);
          setAutoMapped(true);
        } else {
          // Auto-map by fuzzy matching column names
          const mapped = autoMapInputs(selectedTool.inputs, availableColumns);
          const defaultParams: Record<string, string> = {};
          for (const input of selectedTool.inputs) {
            defaultParams[input.name] = mapped[input.name] || "";
          }
          setParams(defaultParams);
          setAutoMapped(Object.keys(mapped).length > 0);
        }
      } else {
        setParams({});
        setAutoMapped(false);
      }
    }
  }, [editingColumn, selectedTool, initialType, availableColumns, initialParams]);

  const handleToggleOutput = (key: string) => {
    setSelectedOutputs((prev) => {
      if (prev.includes(key)) {
        // Don't allow deselecting the last one
        if (prev.length <= 1) return prev;
        return prev.filter((k) => k !== key);
      }
      return [...prev, key];
    });
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      const config: Record<string, unknown> = {
        name: name || "Untitled Column",
        column_type: columnType,
      };

      if (columnType === "enrichment" && selectedTool) {
        config.tool = selectedTool.id;
        config.params = params;
        // Use first selected output as the primary display field
        if (selectedOutputs.length > 0) {
          config.output_key = selectedOutputs[0];
        }
      } else if (columnType === "ai") {
        config.ai_prompt = aiPrompt;
        config.ai_model = aiModel;
      } else if (columnType === "formula") {
        config.formula = formula;
      } else if (columnType === "gate") {
        config.condition = condition;
        if (conditionLabel) config.condition_label = conditionLabel;
      }

      // Save the parent column and get its ID back
      const parentColId = await onSave(config);

      // Create child columns for additional selected outputs
      if (
        parentColId &&
        columnType === "enrichment" &&
        selectedOutputs.length > 1
      ) {
        for (let i = 1; i < selectedOutputs.length; i++) {
          const outputKey = selectedOutputs[i];
          await onSave({
            name: outputKey,
            column_type: "formula",
            parent_column_id: parentColId,
            extract_path: outputKey,
            formula: `{{${parentColId}}}`,
          });
        }
      }

      onClose();
    } finally {
      setSaving(false);
    }
  };

  const typeIcon =
    columnType === "enrichment" ? <Search className="w-4 h-4 text-blue-400" /> :
    columnType === "ai" ? <Brain className="w-4 h-4 text-purple-400" /> :
    columnType === "formula" ? <Calculator className="w-4 h-4 text-teal-400" /> :
    columnType === "gate" ? <Filter className="w-4 h-4 text-amber-400" /> :
    <Type className="w-4 h-4 text-zinc-400" />;

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent
        side="right"
        className="w-[400px] bg-zinc-950 border-zinc-800 text-white overflow-y-auto"
      >
        <SheetHeader className="mb-6">
          <SheetTitle className="flex items-center gap-2 text-white">
            {typeIcon}
            {editingColumn ? "Edit Column" : "Configure Column"}
          </SheetTitle>
          <SheetDescription className="text-zinc-500">
            {selectedTool
              ? `${selectedTool.name} — ${selectedTool.description}`
              : columnType === "ai"
                ? "Describe what you want the AI to do"
                : columnType === "formula"
                  ? "Compute a value from other columns"
                  : columnType === "gate"
                    ? "Filter rows by condition"
                    : "Configure this column"}
          </SheetDescription>
        </SheetHeader>

        <div className="space-y-5">
          {/* Column name */}
          <div>
            <Label className="text-zinc-400 text-xs">Column Name</Label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Email Address"
              className="mt-1.5 bg-zinc-900 border-zinc-700 text-white"
            />
          </div>

          {/* Auto-mapped banner */}
          {columnType === "enrichment" && autoMapped && !editingColumn && (
            <div className="flex items-center justify-between px-3 py-2 rounded-md bg-kiln-teal/5 border border-kiln-teal/20">
              <span className="text-xs text-kiln-teal">
                Inputs auto-mapped from your columns
              </span>
              <button
                onClick={() => {
                  if (selectedTool?.inputs) {
                    const empty: Record<string, string> = {};
                    for (const input of selectedTool.inputs) {
                      empty[input.name] = "";
                    }
                    setParams(empty);
                  }
                  setAutoMapped(false);
                }}
                className="text-[10px] text-zinc-500 hover:text-zinc-300 underline"
              >
                Clear
              </button>
            </div>
          )}

          {/* Enrichment params */}
          {columnType === "enrichment" && selectedTool?.inputs && (
            <div className="space-y-3">
              <Label className="text-zinc-400 text-xs">Parameters</Label>
              {selectedTool.inputs.map((input) => {
                const isEmpty = !params[input.name];
                return (
                  <div key={input.name}>
                    <label className="text-xs text-zinc-500 mb-1 block">
                      {input.name}
                      {input.type && (
                        <span className="text-zinc-600 ml-1">({input.type})</span>
                      )}
                    </label>
                    <ColumnReferenceInput
                      value={params[input.name] || ""}
                      onChange={(val) =>
                        setParams((p) => ({ ...p, [input.name]: val }))
                      }
                      availableColumns={availableColumns}
                      placeholder={`Type / to reference a column`}
                    />
                    {isEmpty && (
                      <p className="text-[10px] text-amber-500/70 mt-1">
                        Map a column to this input
                      </p>
                    )}
                  </div>
                );
              })}
            </div>
          )}

          {/* Enrichment output fields */}
          {columnType === "enrichment" && selectedTool?.outputs && selectedTool.outputs.length > 1 && (
            <OutputFieldSelector
              outputs={selectedTool.outputs}
              selectedOutputs={selectedOutputs}
              onToggle={handleToggleOutput}
            />
          )}

          {/* AI prompt */}
          {columnType === "ai" && (
            <>
              <div>
                <Label className="text-zinc-400 text-xs">Prompt</Label>
                <Textarea
                  value={aiPrompt}
                  onChange={(e) => setAiPrompt(e.target.value)}
                  placeholder="e.g. Based on the company description, score their fit for IoT solutions from 1-10"
                  className="mt-1.5 bg-zinc-900 border-zinc-700 text-white min-h-[100px]"
                />
                <p className="text-xs text-zinc-600 mt-1">
                  Type / to reference other column values
                </p>
              </div>
              <div>
                <Label className="text-zinc-400 text-xs">Model</Label>
                <Select value={aiModel} onValueChange={setAiModel}>
                  <SelectTrigger className="mt-1.5 bg-zinc-900 border-zinc-700 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-zinc-900 border-zinc-700">
                    <SelectItem value="sonnet" className="text-zinc-300">Sonnet (fast)</SelectItem>
                    <SelectItem value="opus" className="text-zinc-300">Opus (best)</SelectItem>
                    <SelectItem value="haiku" className="text-zinc-300">Haiku (cheapest)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </>
          )}

          {/* Formula */}
          {columnType === "formula" && (
            <div>
              <Label className="text-zinc-400 text-xs">Formula</Label>
              <ColumnReferenceInput
                value={formula}
                onChange={setFormula}
                availableColumns={availableColumns}
                placeholder="e.g. /First Name + ' ' + /Last Name"
                multiline
              />
            </div>
          )}

          {/* Gate condition */}
          {columnType === "gate" && (
            <>
              <div>
                <Label className="text-zinc-400 text-xs">Condition</Label>
                <ColumnReferenceInput
                  value={condition}
                  onChange={setCondition}
                  availableColumns={availableColumns}
                  placeholder="e.g. /employee_count >= 50"
                />
              </div>
              <div>
                <Label className="text-zinc-400 text-xs">Label (optional)</Label>
                <Input
                  value={conditionLabel}
                  onChange={(e) => setConditionLabel(e.target.value)}
                  placeholder="e.g. Only companies with 50+ employees"
                  className="mt-1.5 bg-zinc-900 border-zinc-700 text-white"
                />
              </div>
            </>
          )}

          {/* Only Run If — for enrichment and AI columns */}
          {(columnType === "enrichment" || columnType === "ai") && (
            <div className="border-t border-zinc-800 pt-4">
              <button
                className="flex items-center gap-2 text-xs text-zinc-400 hover:text-zinc-300 w-full"
                onClick={() => setCondition(condition ? "" : " ")}
              >
                <div
                  className={`w-3.5 h-3.5 rounded border ${
                    condition
                      ? "bg-amber-500/20 border-amber-500 text-amber-400"
                      : "border-zinc-600"
                  } flex items-center justify-center text-[8px]`}
                >
                  {condition ? "✓" : ""}
                </div>
                Only run if condition is met
              </button>
              {condition && (
                <div className="mt-2">
                  <ColumnReferenceInput
                    value={condition}
                    onChange={setCondition}
                    availableColumns={availableColumns}
                    placeholder="e.g. /domain is not empty"
                  />
                </div>
              )}
            </div>
          )}

          {/* Save button */}
          <div className="pt-4 flex gap-2">
            <Button
              variant="outline"
              className="flex-1 border-zinc-700 text-zinc-300"
              onClick={onClose}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button
              className="flex-1 bg-kiln-teal text-black hover:bg-kiln-teal/90"
              onClick={handleSave}
              disabled={saving}
            >
              {saving
                ? "Adding..."
                : editingColumn
                  ? "Update Column"
                  : selectedOutputs.length > 1
                    ? `Add ${selectedOutputs.length} Columns`
                    : "Add Column"}
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
