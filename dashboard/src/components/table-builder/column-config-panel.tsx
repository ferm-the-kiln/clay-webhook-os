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

interface ColumnConfigPanelProps {
  open: boolean;
  onClose: () => void;
  onSave: (config: Record<string, unknown>) => void;
  /** Existing column being edited (null for new) */
  editingColumn: TableColumn | null;
  /** The pre-selected tool for enrichment columns */
  selectedTool: ToolDefinition | null;
  /** Pre-selected column type for new columns */
  initialType: string | null;
  /** Available columns for "/" references (columns to the left) */
  availableColumns: TableColumn[];
}

export function ColumnConfigPanel({
  open,
  onClose,
  onSave,
  editingColumn,
  selectedTool,
  initialType,
  availableColumns,
}: ColumnConfigPanelProps) {
  const [name, setName] = useState("");
  const [columnType, setColumnType] = useState<string>("enrichment");
  const [params, setParams] = useState<Record<string, string>>({});
  const [outputKey, setOutputKey] = useState("");
  const [aiPrompt, setAiPrompt] = useState("");
  const [aiModel, setAiModel] = useState("sonnet");
  const [formula, setFormula] = useState("");
  const [condition, setCondition] = useState("");
  const [conditionLabel, setConditionLabel] = useState("");

  // Initialize from editing column or defaults
  useEffect(() => {
    if (editingColumn) {
      setName(editingColumn.name);
      setColumnType(editingColumn.column_type);
      setParams(editingColumn.params);
      setOutputKey(editingColumn.output_key || "");
      setAiPrompt(editingColumn.ai_prompt || "");
      setAiModel(editingColumn.ai_model || "sonnet");
      setFormula(editingColumn.formula || "");
      setCondition(editingColumn.condition || "");
      setConditionLabel(editingColumn.condition_label || "");
    } else {
      // New column defaults
      setName(selectedTool?.name || "");
      setColumnType(initialType || "enrichment");
      setParams({});
      setOutputKey("");
      setAiPrompt("");
      setAiModel("sonnet");
      setFormula("");
      setCondition("");
      setConditionLabel("");

      // Pre-populate params from tool inputs
      if (selectedTool?.inputs) {
        const defaultParams: Record<string, string> = {};
        for (const input of selectedTool.inputs) {
          defaultParams[input.name] = "";
        }
        setParams(defaultParams);
      }
    }
  }, [editingColumn, selectedTool, initialType]);

  const handleSave = () => {
    const config: Record<string, unknown> = {
      name: name || "Untitled Column",
      column_type: columnType,
    };

    if (columnType === "enrichment" && selectedTool) {
      config.tool = selectedTool.id;
      config.params = params;
      if (outputKey) config.output_key = outputKey;
    } else if (columnType === "ai") {
      config.ai_prompt = aiPrompt;
      config.ai_model = aiModel;
    } else if (columnType === "formula") {
      config.formula = formula;
    } else if (columnType === "gate") {
      config.condition = condition;
      if (conditionLabel) config.condition_label = conditionLabel;
    }

    onSave(config);
    onClose();
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

          {/* Enrichment params */}
          {columnType === "enrichment" && selectedTool?.inputs && (
            <div className="space-y-3">
              <Label className="text-zinc-400 text-xs">Parameters</Label>
              {selectedTool.inputs.map((input) => (
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
                </div>
              ))}
            </div>
          )}

          {/* Enrichment output key */}
          {columnType === "enrichment" && selectedTool?.outputs && selectedTool.outputs.length > 1 && (
            <div>
              <Label className="text-zinc-400 text-xs">Display Field</Label>
              <Select value={outputKey} onValueChange={setOutputKey}>
                <SelectTrigger className="mt-1.5 bg-zinc-900 border-zinc-700 text-white">
                  <SelectValue placeholder="Select output field" />
                </SelectTrigger>
                <SelectContent className="bg-zinc-900 border-zinc-700">
                  {selectedTool.outputs.map((out) => (
                    <SelectItem key={out.key} value={out.key} className="text-zinc-300">
                      {out.key}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
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

          {/* Save button */}
          <div className="pt-4 flex gap-2">
            <Button
              variant="outline"
              className="flex-1 border-zinc-700 text-zinc-300"
              onClick={onClose}
            >
              Cancel
            </Button>
            <Button
              className="flex-1 bg-kiln-teal text-black hover:bg-kiln-teal/90"
              onClick={handleSave}
            >
              {editingColumn ? "Update Column" : "Add Column"}
            </Button>
          </div>
        </div>
      </SheetContent>
    </Sheet>
  );
}
