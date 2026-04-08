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
  Unplug,
  Shuffle,
  Link2,
  Terminal,
  ChevronDown,
  Plus,
  X,
} from "lucide-react";
import type { TableColumn, TableSummary, ToolDefinition, HttpColumnConfig, ErrorHandlingConfig } from "@/lib/types";
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

  // HTTP config state
  const [httpMethod, setHttpMethod] = useState("GET");
  const [httpUrl, setHttpUrl] = useState("");
  const [httpHeaders, setHttpHeaders] = useState<[string, string][]>([]);
  const [httpBody, setHttpBody] = useState("");
  const [httpExtract, setHttpExtract] = useState("$");
  const [httpIfEmpty, setHttpIfEmpty] = useState("");

  // Lookup config state
  const [lookupSourceTable, setLookupSourceTable] = useState("");
  const [lookupMatchColumn, setLookupMatchColumn] = useState("");
  const [lookupMatchValue, setLookupMatchValue] = useState("");
  const [lookupMatchOperator, setLookupMatchOperator] = useState("equals");
  const [lookupReturnColumn, setLookupReturnColumn] = useState("");
  const [lookupReturnType, setLookupReturnType] = useState("value");

  // Script config state
  const [scriptLanguage, setScriptLanguage] = useState("python");
  const [scriptCode, setScriptCode] = useState("");
  const [scriptExtract, setScriptExtract] = useState("");

  // Error handling state
  const [errorOnError, setErrorOnError] = useState("skip");
  const [errorFallbackValue, setErrorFallbackValue] = useState("");
  const [errorMaxRetries, setErrorMaxRetries] = useState(0);
  const [errorRetryBackoff, setErrorRetryBackoff] = useState("exponential");
  const [showErrorHandling, setShowErrorHandling] = useState(false);

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
      // HTTP
      if (editingColumn.http_config) {
        setHttpMethod(editingColumn.http_config.method);
        setHttpUrl(editingColumn.http_config.url);
        setHttpHeaders(Object.entries(editingColumn.http_config.headers));
        setHttpBody(typeof editingColumn.http_config.body === "string" ? editingColumn.http_config.body : editingColumn.http_config.body ? JSON.stringify(editingColumn.http_config.body) : "");
        setHttpExtract(editingColumn.http_config.extract);
        setHttpIfEmpty(editingColumn.http_config.if_empty || "");
      }
      // Lookup
      if (editingColumn.lookup_config) {
        setLookupSourceTable(editingColumn.lookup_config.source_table_id);
        setLookupMatchColumn(editingColumn.lookup_config.match_column);
        setLookupMatchValue(editingColumn.lookup_config.match_value);
        setLookupMatchOperator(editingColumn.lookup_config.match_operator);
        setLookupReturnColumn(editingColumn.lookup_config.return_column || "");
        setLookupReturnType(editingColumn.lookup_config.return_type);
      }
      // Script
      if (editingColumn.script_config) {
        setScriptLanguage(editingColumn.script_config.language);
        setScriptCode(editingColumn.script_config.code);
        setScriptExtract(editingColumn.script_config.extract || "");
      }
      // Error handling
      if (editingColumn.error_handling) {
        setErrorOnError(editingColumn.error_handling.on_error);
        setErrorFallbackValue(editingColumn.error_handling.fallback_value || "");
        setErrorMaxRetries(editingColumn.error_handling.max_retries);
        setErrorRetryBackoff(editingColumn.error_handling.retry_backoff);
        setShowErrorHandling(true);
      }
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
      } else if (columnType === "http") {
        let bodyParsed: Record<string, unknown> | string | null = null;
        if (httpBody) {
          try {
            bodyParsed = JSON.parse(httpBody);
          } catch {
            bodyParsed = httpBody;
          }
        }
        config.http_config = {
          method: httpMethod,
          url: httpUrl,
          headers: Object.fromEntries(httpHeaders.filter(([k]) => k)),
          body: bodyParsed,
          extract: httpExtract || "$",
          if_empty: httpIfEmpty || null,
        };
      } else if (columnType === "lookup") {
        config.lookup_config = {
          source_table_id: lookupSourceTable,
          match_column: lookupMatchColumn,
          match_value: lookupMatchValue,
          match_operator: lookupMatchOperator,
          return_column: lookupReturnColumn || null,
          return_type: lookupReturnType,
          match_mode: "first",
        };
      } else if (columnType === "script") {
        config.script_config = {
          language: scriptLanguage,
          code: scriptCode,
          script_name: null,
          extract: scriptExtract || null,
          timeout: 30,
        };
      }

      // Error handling (for action columns)
      if (showErrorHandling && ["enrichment", "ai", "http", "waterfall", "script"].includes(columnType)) {
        config.error_handling = {
          on_error: errorOnError,
          fallback_value: errorOnError === "fallback" ? errorFallbackValue : null,
          max_retries: errorMaxRetries,
          retry_delay_ms: 1000,
          retry_backoff: errorRetryBackoff,
        };
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
    columnType === "http" ? <Unplug className="w-4 h-4 text-orange-400" /> :
    columnType === "waterfall" ? <Shuffle className="w-4 h-4 text-emerald-400" /> :
    columnType === "lookup" ? <Link2 className="w-4 h-4 text-cyan-400" /> :
    columnType === "script" ? <Terminal className="w-4 h-4 text-rose-400" /> :
    <Type className="w-4 h-4 text-clay-200" />;

  return (
    <Sheet open={open} onOpenChange={(o) => !o && onClose()}>
      <SheetContent
        side="right"
        className="w-[400px] bg-clay-950 border-clay-700 text-white overflow-y-auto"
      >
        <SheetHeader className="mb-6">
          <SheetTitle className="flex items-center gap-2 text-white">
            {typeIcon}
            {editingColumn ? "Edit Column" : "Configure Column"}
          </SheetTitle>
          <SheetDescription className="text-clay-300">
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
            <Label className="text-clay-200 text-xs">Column Name</Label>
            <Input
              value={name}
              onChange={(e) => setName(e.target.value)}
              placeholder="e.g. Email Address"
              className="mt-1.5 bg-clay-900 border-clay-500 text-white"
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
                className="text-[10px] text-clay-300 hover:text-clay-100 underline"
              >
                Clear
              </button>
            </div>
          )}

          {/* Enrichment params */}
          {columnType === "enrichment" && selectedTool?.inputs && (
            <div className="space-y-3">
              <Label className="text-clay-200 text-xs">Parameters</Label>
              {selectedTool.inputs.map((input) => {
                const isEmpty = !params[input.name];
                return (
                  <div key={input.name}>
                    <label className="text-xs text-clay-300 mb-1 block">
                      {input.name}
                      {input.type && (
                        <span className="text-clay-300 ml-1">({input.type})</span>
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
                <Label className="text-clay-200 text-xs">Prompt</Label>
                <Textarea
                  value={aiPrompt}
                  onChange={(e) => setAiPrompt(e.target.value)}
                  placeholder="e.g. Based on the company description, score their fit for IoT solutions from 1-10"
                  className="mt-1.5 bg-clay-900 border-clay-500 text-white min-h-[100px]"
                />
                <p className="text-xs text-clay-300 mt-1">
                  Type / to reference other column values
                </p>
              </div>
              <div>
                <Label className="text-clay-200 text-xs">Model</Label>
                <Select value={aiModel} onValueChange={setAiModel}>
                  <SelectTrigger className="mt-1.5 bg-clay-900 border-clay-500 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-clay-900 border-clay-500">
                    <SelectItem value="sonnet" className="text-clay-100">Sonnet (fast)</SelectItem>
                    <SelectItem value="opus" className="text-clay-100">Opus (best)</SelectItem>
                    <SelectItem value="haiku" className="text-clay-100">Haiku (cheapest)</SelectItem>
                  </SelectContent>
                </Select>
              </div>
            </>
          )}

          {/* Formula */}
          {columnType === "formula" && (
            <div>
              <Label className="text-clay-200 text-xs">Formula</Label>
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
                <Label className="text-clay-200 text-xs">Condition</Label>
                <ColumnReferenceInput
                  value={condition}
                  onChange={setCondition}
                  availableColumns={availableColumns}
                  placeholder="e.g. /employee_count >= 50"
                />
              </div>
              <div>
                <Label className="text-clay-200 text-xs">Label (optional)</Label>
                <Input
                  value={conditionLabel}
                  onChange={(e) => setConditionLabel(e.target.value)}
                  placeholder="e.g. Only companies with 50+ employees"
                  className="mt-1.5 bg-clay-900 border-clay-500 text-white"
                />
              </div>
            </>
          )}

          {/* HTTP config */}
          {columnType === "http" && (
            <div className="space-y-3">
              <div className="flex gap-2">
                <div className="w-24">
                  <Label className="text-clay-200 text-xs">Method</Label>
                  <Select value={httpMethod} onValueChange={setHttpMethod}>
                    <SelectTrigger className="mt-1.5 bg-clay-900 border-clay-500 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-clay-900 border-clay-500">
                      {["GET", "POST", "PUT", "PATCH", "DELETE"].map((m) => (
                        <SelectItem key={m} value={m} className="text-clay-100">{m}</SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex-1">
                  <Label className="text-clay-200 text-xs">URL</Label>
                  <ColumnReferenceInput
                    value={httpUrl}
                    onChange={setHttpUrl}
                    availableColumns={availableColumns}
                    placeholder="https://api.example.com/{{domain}}"
                  />
                </div>
              </div>

              <div>
                <div className="flex items-center justify-between">
                  <Label className="text-clay-200 text-xs">Headers</Label>
                  <button
                    className="text-[10px] text-clay-300 hover:text-clay-100"
                    onClick={() => setHttpHeaders([...httpHeaders, ["", ""]])}
                  >
                    <Plus className="w-3 h-3 inline mr-0.5" />Add
                  </button>
                </div>
                {httpHeaders.map(([key, val], i) => (
                  <div key={i} className="flex gap-1.5 mt-1.5">
                    <Input
                      value={key}
                      onChange={(e) => {
                        const h = [...httpHeaders];
                        h[i] = [e.target.value, val];
                        setHttpHeaders(h);
                      }}
                      placeholder="Header name"
                      className="flex-1 bg-clay-900 border-clay-500 text-white text-xs h-8"
                    />
                    <Input
                      value={val}
                      onChange={(e) => {
                        const h = [...httpHeaders];
                        h[i] = [key, e.target.value];
                        setHttpHeaders(h);
                      }}
                      placeholder="Value"
                      className="flex-1 bg-clay-900 border-clay-500 text-white text-xs h-8"
                    />
                    <button onClick={() => setHttpHeaders(httpHeaders.filter((_, j) => j !== i))} className="text-clay-300 hover:text-clay-200">
                      <X className="w-3.5 h-3.5" />
                    </button>
                  </div>
                ))}
              </div>

              {(httpMethod === "POST" || httpMethod === "PUT" || httpMethod === "PATCH") && (
                <div>
                  <Label className="text-clay-200 text-xs">Body (JSON)</Label>
                  <Textarea
                    value={httpBody}
                    onChange={(e) => setHttpBody(e.target.value)}
                    placeholder='{"query": "{{company_name}}"}'
                    className="mt-1.5 bg-clay-900 border-clay-500 text-white font-mono text-xs min-h-[60px]"
                  />
                </div>
              )}

              <div>
                <Label className="text-clay-200 text-xs">Extract (JSONPath)</Label>
                <Input
                  value={httpExtract}
                  onChange={(e) => setHttpExtract(e.target.value)}
                  placeholder="$.data.company.name"
                  className="mt-1.5 bg-clay-900 border-clay-500 text-white font-mono text-xs"
                />
                <p className="text-[10px] text-clay-300 mt-1">$ = entire response, $.field = nested field</p>
              </div>

              <div>
                <Label className="text-clay-200 text-xs">Fallback if empty</Label>
                <Input
                  value={httpIfEmpty}
                  onChange={(e) => setHttpIfEmpty(e.target.value)}
                  placeholder="N/A"
                  className="mt-1.5 bg-clay-900 border-clay-500 text-white text-xs"
                />
              </div>
            </div>
          )}

          {/* Lookup config */}
          {columnType === "lookup" && (
            <div className="space-y-3">
              <div>
                <Label className="text-clay-200 text-xs">Source Table ID</Label>
                <Input
                  value={lookupSourceTable}
                  onChange={(e) => setLookupSourceTable(e.target.value)}
                  placeholder="table-id-to-search"
                  className="mt-1.5 bg-clay-900 border-clay-500 text-white text-xs"
                />
              </div>
              <div>
                <Label className="text-clay-200 text-xs">Match Column (in source table)</Label>
                <Input
                  value={lookupMatchColumn}
                  onChange={(e) => setLookupMatchColumn(e.target.value)}
                  placeholder="company_domain"
                  className="mt-1.5 bg-clay-900 border-clay-500 text-white text-xs"
                />
              </div>
              <div>
                <Label className="text-clay-200 text-xs">Match Value</Label>
                <ColumnReferenceInput
                  value={lookupMatchValue}
                  onChange={setLookupMatchValue}
                  availableColumns={availableColumns}
                  placeholder="{{domain}}"
                />
              </div>
              <div className="flex gap-2">
                <div className="flex-1">
                  <Label className="text-clay-200 text-xs">Operator</Label>
                  <Select value={lookupMatchOperator} onValueChange={setLookupMatchOperator}>
                    <SelectTrigger className="mt-1.5 bg-clay-900 border-clay-500 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-clay-900 border-clay-500">
                      <SelectItem value="equals" className="text-clay-100">Equals</SelectItem>
                      <SelectItem value="contains" className="text-clay-100">Contains</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="flex-1">
                  <Label className="text-clay-200 text-xs">Return</Label>
                  <Select value={lookupReturnType} onValueChange={setLookupReturnType}>
                    <SelectTrigger className="mt-1.5 bg-clay-900 border-clay-500 text-white">
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent className="bg-clay-900 border-clay-500">
                      <SelectItem value="value" className="text-clay-100">Value</SelectItem>
                      <SelectItem value="boolean" className="text-clay-100">True/False</SelectItem>
                      <SelectItem value="count" className="text-clay-100">Count</SelectItem>
                      <SelectItem value="rows" className="text-clay-100">All Rows</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
              </div>
              {lookupReturnType === "value" && (
                <div>
                  <Label className="text-clay-200 text-xs">Return Column</Label>
                  <Input
                    value={lookupReturnColumn}
                    onChange={(e) => setLookupReturnColumn(e.target.value)}
                    placeholder="email (column ID in source table)"
                    className="mt-1.5 bg-clay-900 border-clay-500 text-white text-xs"
                  />
                </div>
              )}
            </div>
          )}

          {/* Script config */}
          {columnType === "script" && (
            <div className="space-y-3">
              <div>
                <Label className="text-clay-200 text-xs">Language</Label>
                <Select value={scriptLanguage} onValueChange={setScriptLanguage}>
                  <SelectTrigger className="mt-1.5 bg-clay-900 border-clay-500 text-white">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent className="bg-clay-900 border-clay-500">
                    <SelectItem value="python" className="text-clay-100">Python</SelectItem>
                    <SelectItem value="bash" className="text-clay-100">Bash</SelectItem>
                    <SelectItem value="node" className="text-clay-100">Node.js</SelectItem>
                  </SelectContent>
                </Select>
              </div>
              <div>
                <Label className="text-clay-200 text-xs">Code</Label>
                <Textarea
                  value={scriptCode}
                  onChange={(e) => setScriptCode(e.target.value)}
                  placeholder={scriptLanguage === "python"
                    ? "import json, sys\ndata = json.load(sys.stdin)\nprint(json.dumps({'result': data['company']}))"
                    : "# Row data arrives on stdin as JSON"}
                  className="mt-1.5 bg-clay-900 border-clay-500 text-white font-mono text-xs min-h-[120px]"
                  spellCheck={false}
                />
                <p className="text-[10px] text-clay-300 mt-1">Row data is piped as JSON via stdin. Output JSON to stdout.</p>
              </div>
              <div>
                <Label className="text-clay-200 text-xs">Extract (JSONPath, optional)</Label>
                <Input
                  value={scriptExtract}
                  onChange={(e) => setScriptExtract(e.target.value)}
                  placeholder="$.result"
                  className="mt-1.5 bg-clay-900 border-clay-500 text-white font-mono text-xs"
                />
              </div>
            </div>
          )}

          {/* Error Handling — for action columns */}
          {["enrichment", "ai", "http", "waterfall", "script"].includes(columnType) && (
            <div className="border-t border-clay-700 pt-4">
              <button
                className="flex items-center gap-2 text-xs text-clay-200 hover:text-clay-100 w-full"
                onClick={() => setShowErrorHandling(!showErrorHandling)}
              >
                <ChevronDown className={`w-3.5 h-3.5 transition-transform ${showErrorHandling ? "" : "-rotate-90"}`} />
                Error Handling & Retries
              </button>
              {showErrorHandling && (
                <div className="mt-3 space-y-3">
                  <div>
                    <Label className="text-clay-200 text-xs">On Error</Label>
                    <Select value={errorOnError} onValueChange={setErrorOnError}>
                      <SelectTrigger className="mt-1.5 bg-clay-900 border-clay-500 text-white">
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent className="bg-clay-900 border-clay-500">
                        <SelectItem value="skip" className="text-clay-100">Skip (mark as error)</SelectItem>
                        <SelectItem value="fallback" className="text-clay-100">Use fallback value</SelectItem>
                        <SelectItem value="stop" className="text-clay-100">Stop execution</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>
                  {errorOnError === "fallback" && (
                    <div>
                      <Label className="text-clay-200 text-xs">Fallback Value</Label>
                      <Input
                        value={errorFallbackValue}
                        onChange={(e) => setErrorFallbackValue(e.target.value)}
                        placeholder="N/A"
                        className="mt-1.5 bg-clay-900 border-clay-500 text-white text-xs"
                      />
                    </div>
                  )}
                  <div className="flex gap-2">
                    <div className="flex-1">
                      <Label className="text-clay-200 text-xs">Max Retries</Label>
                      <Input
                        type="number"
                        min={0}
                        max={5}
                        value={errorMaxRetries}
                        onChange={(e) => setErrorMaxRetries(Number(e.target.value))}
                        className="mt-1.5 bg-clay-900 border-clay-500 text-white text-xs"
                      />
                    </div>
                    <div className="flex-1">
                      <Label className="text-clay-200 text-xs">Backoff</Label>
                      <Select value={errorRetryBackoff} onValueChange={setErrorRetryBackoff}>
                        <SelectTrigger className="mt-1.5 bg-clay-900 border-clay-500 text-white">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent className="bg-clay-900 border-clay-500">
                          <SelectItem value="exponential" className="text-clay-100">Exponential</SelectItem>
                          <SelectItem value="linear" className="text-clay-100">Linear</SelectItem>
                          <SelectItem value="fixed" className="text-clay-100">Fixed (1s)</SelectItem>
                        </SelectContent>
                      </Select>
                    </div>
                  </div>
                </div>
              )}
            </div>
          )}

          {/* Only Run If — for enrichment and AI columns */}
          {(columnType === "enrichment" || columnType === "ai") && (
            <div className="border-t border-clay-700 pt-4">
              <button
                className="flex items-center gap-2 text-xs text-clay-200 hover:text-clay-100 w-full"
                onClick={() => setCondition(condition ? "" : " ")}
              >
                <div
                  className={`w-3.5 h-3.5 rounded border ${
                    condition
                      ? "bg-amber-500/20 border-amber-500 text-amber-400"
                      : "border-clay-400"
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
              className="flex-1 border-clay-500 text-clay-100"
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
