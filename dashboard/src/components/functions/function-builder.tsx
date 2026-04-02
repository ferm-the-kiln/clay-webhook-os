"use client";

import { useCallback, useRef, useState } from "react";
import {
  DndContext,
  closestCenter,
  DragEndEvent,
  PointerSensor,
  useSensor,
  useSensors,
} from "@dnd-kit/core";
import {
  SortableContext,
  verticalListSortingStrategy,
  arrayMove,
  useSortable,
} from "@dnd-kit/sortable";
import { CSS } from "@dnd-kit/utilities";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select";
import { Badge } from "@/components/ui/badge";
import {
  Tooltip,
  TooltipTrigger,
  TooltipContent,
} from "@/components/ui/tooltip";
import {
  Popover,
  PopoverTrigger,
  PopoverContent,
} from "@/components/ui/popover";
import {
  Plus,
  Trash2,
  ChevronDown,
  ChevronRight,
  Blocks,
  GripVertical,
  Wrench,
  Search,
  Filter,
  Globe,
  Bot,
  Zap,
  Settings,
} from "lucide-react";
import { cn } from "@/lib/utils";
import type {
  FunctionDefinition,
  FunctionInput,
  FunctionOutput,
  FunctionStep,
  ToolCategory,
  ToolDefinition,
} from "@/lib/types";

/** Highlight {{input_name}} template vars with teal spans */
function highlightTemplateVars(value: string) {
  const parts = value.split(/(\\{\\{[^}]+\\}\\})/g);
  return parts.map((part, i) =>
    /^\\{\\{.+\\}\\}$/.test(part) ? (
      <span
        key={i}
        className="text-kiln-teal bg-kiln-teal/10 px-1 rounded text-[10px] font-medium"
      >
        {part}
      </span>
    ) : (
      <span key={i}>{part}</span>
    )
  );
}

interface FunctionBuilderProps {
  func: FunctionDefinition;
  editing: boolean;
  // Editable fields
  name: string;
  setName: (v: string) => void;
  description: string;
  setDescription: (v: string) => void;
  folder: string;
  setFolder: (v: string) => void;
  inputs: FunctionInput[];
  setInputs: (v: FunctionInput[]) => void;
  outputs: FunctionOutput[];
  setOutputs: (v: FunctionOutput[]) => void;
  steps: FunctionStep[];
  setSteps: (v: FunctionStep[]) => void;
  // Tool catalog
  toolCategories: ToolCategory[];
  toolMap: Record<string, ToolDefinition>;
  catalogOpen: boolean;
  setCatalogOpen: (v: boolean) => void;
  // Data flow maps
  inputUsageMap: Record<string, number[]>;
  stepInputMap: Record<number, string[]>;
  // Step editing
  editingStepIdx: number | null;
  setEditingStepIdx: (v: number | null) => void;
  expandedSteps: Set<number>;
  toggleStepExpanded: (i: number) => void;
}

export function FunctionBuilder({
  func,
  editing,
  name,
  setName,
  description,
  setDescription,
  folder,
  setFolder,
  inputs,
  setInputs,
  outputs,
  setOutputs,
  steps,
  setSteps,
  toolCategories,
  toolMap,
  catalogOpen,
  setCatalogOpen,
  inputUsageMap,
  stepInputMap,
  editingStepIdx,
  setEditingStepIdx,
  expandedSteps,
  toggleStepExpanded,
}: FunctionBuilderProps) {
  const addInput = () => {
    setInputs([
      ...inputs,
      { name: "", type: "string", required: true, description: "" },
    ]);
  };

  const removeInput = (i: number) => {
    setInputs(inputs.filter((_, idx) => idx !== i));
  };

  const updateInput = (
    i: number,
    field: keyof FunctionInput,
    value: string | boolean
  ) => {
    const updated = [...inputs];
    (updated[i] as unknown as Record<string, unknown>)[field] = value;
    setInputs(updated);
  };

  const addOutput = () => {
    setOutputs([...outputs, { key: "", type: "string", description: "" }]);
  };

  const removeOutput = (i: number) => {
    setOutputs(outputs.filter((_, idx) => idx !== i));
  };

  const updateOutput = (
    i: number,
    field: keyof FunctionOutput,
    value: string
  ) => {
    const updated = [...outputs];
    (updated[i] as unknown as Record<string, unknown>)[field] = value;
    setOutputs(updated);
  };

  const addStep = (tool?: string) => {
    const toolId = tool || "";
    const toolDef = toolMap[toolId];
    // Auto-populate params from tool catalog inputs
    const params: Record<string, string> = {};
    if (toolDef?.inputs) {
      for (const inp of toolDef.inputs) {
        params[inp.name] = "";
      }
    }
    setSteps([...steps, { tool: toolId, params }]);
    setCatalogOpen(false);
  };

  const removeStep = (i: number) => {
    setSteps(steps.filter((_, idx) => idx !== i));
    if (editingStepIdx === i) setEditingStepIdx(null);
  };

  const updateStepTool = (i: number, tool: string) => {
    const updated = [...steps];
    updated[i] = { ...updated[i], tool };
    setSteps(updated);
  };

  const updateStepParam = (
    stepIdx: number,
    key: string,
    value: string,
    oldKey?: string
  ) => {
    const updated = [...steps];
    const params = { ...updated[stepIdx].params };
    if (oldKey && oldKey !== key) {
      delete params[oldKey];
    }
    params[key] = value;
    updated[stepIdx] = { ...updated[stepIdx], params };
    setSteps(updated);
  };

  const removeStepParam = (stepIdx: number, key: string) => {
    const updated = [...steps];
    const params = { ...updated[stepIdx].params };
    delete params[key];
    updated[stepIdx] = { ...updated[stepIdx], params };
    setSteps(updated);
  };

  const addStepParam = (stepIdx: number) => {
    const updated = [...steps];
    const params = { ...updated[stepIdx].params };
    let newKey = "param";
    let n = 1;
    while (params[newKey]) {
      newKey = `param${n++}`;
    }
    params[newKey] = "";
    updated[stepIdx] = { ...updated[stepIdx], params };
    setSteps(updated);
  };

  // Stable drag IDs for steps — generate once, extend on add
  const stepIdCounter = useRef(0);
  const [stepIds, setStepIds] = useState<string[]>(() =>
    steps.map(() => `step-${stepIdCounter.current++}`)
  );

  // Keep stepIds in sync when steps array length changes externally (load/save)
  const prevStepsLen = useRef(steps.length);
  if (steps.length !== prevStepsLen.current) {
    if (steps.length > stepIds.length) {
      const newIds = [...stepIds];
      while (newIds.length < steps.length) {
        newIds.push(`step-${stepIdCounter.current++}`);
      }
      setStepIds(newIds);
    } else if (steps.length < stepIds.length) {
      setStepIds(stepIds.slice(0, steps.length));
    }
    prevStepsLen.current = steps.length;
  }

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 5 } })
  );

  const handleDragEnd = useCallback(
    (event: DragEndEvent) => {
      const { active, over } = event;
      if (!over || active.id === over.id) return;
      const oldIndex = stepIds.indexOf(String(active.id));
      const newIndex = stepIds.indexOf(String(over.id));
      if (oldIndex === -1 || newIndex === -1) return;
      setSteps(arrayMove(steps, oldIndex, newIndex));
      setStepIds(arrayMove(stepIds, oldIndex, newIndex));
    },
    [steps, stepIds, setSteps]
  );

  // Collect output keys from prior steps for step output references
  const getOutputKeysFromPriorSteps = useCallback(
    (stepIdx: number) => {
      const keys: { stepIdx: number; stepLabel: string; outputKeys: string[] }[] = [];
      for (let i = 0; i < stepIdx; i++) {
        const s = steps[i];
        const td = toolMap[s.tool];
        if (td?.outputs) {
          keys.push({
            stepIdx: i,
            stepLabel: td.name || s.tool,
            outputKeys: td.outputs.map((o) => o.key),
          });
        }
      }
      return keys;
    },
    [steps, toolMap]
  );

  return (
    <div className="lg:col-span-2 space-y-6">
      {/* Details */}
      <Card className="border-clay-600">
        <CardHeader className="pb-3">
          <CardTitle className="text-sm text-clay-200 flex items-center gap-2">
            <Settings className="h-4 w-4" />
            Details
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          {editing ? (
            <>
              <div>
                <label className="text-xs text-clay-300 mb-1 block">Name</label>
                <Input
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="bg-clay-900 border-clay-600 text-clay-100"
                />
              </div>
              <div>
                <label className="text-xs text-clay-300 mb-1 block">
                  Description
                </label>
                <Textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  rows={2}
                />
              </div>
              <div>
                <label className="text-xs text-clay-300 mb-1 block">
                  Folder
                </label>
                <Input
                  value={folder}
                  onChange={(e) => setFolder(e.target.value)}
                  className="bg-clay-900 border-clay-600 text-clay-100"
                />
              </div>
            </>
          ) : (
            <>
              <div className="text-sm text-clay-200">
                {func.description || "No description"}
              </div>
              <div className="text-xs text-clay-300">
                Folder: {func.folder} | ID: {func.id}
              </div>
            </>
          )}
        </CardContent>
      </Card>

      {/* Inputs */}
      <Card className="border-clay-600">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm text-clay-200">
              Inputs ({inputs.length})
            </CardTitle>
            {editing && (
              <Button
                variant="ghost"
                size="sm"
                onClick={addInput}
                className="text-clay-300 h-7 text-xs"
              >
                <Plus className="h-3 w-3 mr-1" /> Add
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {inputs.length === 0 ? (
            <div className="text-xs text-clay-300 py-2">No inputs defined</div>
          ) : (
            <div className="space-y-2">
              {inputs.map((inp, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 p-2 rounded bg-clay-900/50 border border-clay-700"
                >
                  {editing ? (
                    <>
                      <Input
                        value={inp.name}
                        onChange={(e) => updateInput(i, "name", e.target.value)}
                        placeholder="Name"
                        className="bg-clay-900 border-clay-600 text-clay-100 text-xs h-7 flex-1"
                      />
                      <Select value={inp.type} onValueChange={(v) => updateInput(i, "type", v)}>
                        <SelectTrigger size="sm" className="w-auto h-7 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {["string", "number", "url", "email", "boolean"].map((t) => (
                            <SelectItem key={t} value={t}>{t}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <label className="flex items-center gap-1 text-xs text-clay-300">
                        <input
                          type="checkbox"
                          checked={inp.required}
                          onChange={(e) =>
                            updateInput(i, "required", e.target.checked)
                          }
                          className="rounded"
                        />
                        Req
                      </label>
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeInput(i)}
                        className="h-6 w-6 p-0 text-red-400"
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </>
                  ) : (
                    <div className="flex items-center gap-2 text-xs flex-1">
                      <span className="font-medium text-clay-100">
                        {inp.name}
                      </span>
                      <span className="text-clay-300">({inp.type})</span>
                      {inp.required && (
                        <span className="text-red-400 text-[10px]">
                          required
                        </span>
                      )}
                      {inp.description && (
                        <span className="text-clay-300">
                          — {inp.description}
                        </span>
                      )}
                      <span className="ml-auto flex items-center gap-1">
                        {inputUsageMap[inp.name] ? (
                          inputUsageMap[inp.name].map((stepIdx) => (
                            <Badge
                              key={stepIdx}
                              variant="secondary"
                              className="text-[9px] px-1.5 py-0 h-4"
                            >
                              Step {stepIdx + 1}
                            </Badge>
                          ))
                        ) : (
                          <Badge
                            variant="destructive"
                            className="text-[9px] px-1.5 py-0 h-4"
                          >
                            unused
                          </Badge>
                        )}
                      </span>
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Outputs */}
      <Card className="border-clay-600">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm text-clay-200">
              Outputs ({outputs.length})
            </CardTitle>
            {editing && (
              <Button
                variant="ghost"
                size="sm"
                onClick={addOutput}
                className="text-clay-300 h-7 text-xs"
              >
                <Plus className="h-3 w-3 mr-1" /> Add
              </Button>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {outputs.length === 0 ? (
            <div className="text-xs text-clay-300 py-2">
              No outputs defined
            </div>
          ) : (
            <div className="space-y-2">
              {outputs.map((out, i) => (
                <div
                  key={i}
                  className="flex items-center gap-2 p-2 rounded bg-clay-900/50 border border-clay-700"
                >
                  {editing ? (
                    <>
                      <Input
                        value={out.key}
                        onChange={(e) => updateOutput(i, "key", e.target.value)}
                        placeholder="Key"
                        className="bg-clay-900 border-clay-600 text-clay-100 text-xs h-7 flex-1"
                      />
                      <Select value={out.type} onValueChange={(v) => updateOutput(i, "type", v)}>
                        <SelectTrigger size="sm" className="w-auto h-7 text-xs">
                          <SelectValue />
                        </SelectTrigger>
                        <SelectContent>
                          {["string", "number", "boolean", "json"].map((t) => (
                            <SelectItem key={t} value={t}>{t}</SelectItem>
                          ))}
                        </SelectContent>
                      </Select>
                      <Input
                        value={out.description}
                        onChange={(e) =>
                          updateOutput(i, "description", e.target.value)
                        }
                        placeholder="Description"
                        className="bg-clay-900 border-clay-600 text-clay-100 text-xs h-7 flex-1"
                      />
                      <Button
                        variant="ghost"
                        size="sm"
                        onClick={() => removeOutput(i)}
                        className="h-6 w-6 p-0 text-red-400"
                      >
                        <Trash2 className="h-3 w-3" />
                      </Button>
                    </>
                  ) : (
                    <div className="flex items-center gap-2 text-xs">
                      <span className="font-medium text-kiln-teal">
                        {out.key}
                      </span>
                      <span className="text-clay-300">({out.type})</span>
                      {out.description && (
                        <span className="text-clay-300">
                          — {out.description}
                        </span>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>

      {/* Steps */}
      <Card className="border-clay-600">
        <CardHeader className="pb-3">
          <div className="flex items-center justify-between">
            <CardTitle className="text-sm text-clay-200 flex items-center gap-2">
              <Wrench className="h-4 w-4" />
              Steps ({steps.length})
            </CardTitle>
            {editing && (
              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setCatalogOpen(!catalogOpen)}
                  className="text-clay-300 h-7 text-xs"
                >
                  <Blocks className="h-3 w-3 mr-1" /> Browse Tools
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => addStep()}
                  className="text-clay-300 h-7 text-xs"
                >
                  <Plus className="h-3 w-3 mr-1" /> Add Step
                </Button>
              </div>
            )}
          </div>
        </CardHeader>
        <CardContent>
          {steps.length === 0 ? (
            <div className="text-center py-6 space-y-2">
              <Wrench className="h-6 w-6 text-clay-500 mx-auto" />
              <div className="text-xs text-clay-300">
                Steps are the tools that process your data.
              </div>
              <div className="text-[10px] text-clay-400">
                Add AI analysis, web search, gates to filter rows, or reference other functions.
              </div>
              {editing && (
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => addStep()}
                  className="text-clay-300 h-7 text-xs mt-2 border-clay-600"
                >
                  <Plus className="h-3 w-3 mr-1" /> Add Your First Step
                </Button>
              )}
            </div>
          ) : editing ? (
            <DndContext
              sensors={sensors}
              collisionDetection={closestCenter}
              onDragEnd={handleDragEnd}
            >
              <SortableContext
                items={stepIds}
                strategy={verticalListSortingStrategy}
              >
                <div>
                  {steps.map((step, i) => (
                    <div key={stepIds[i]}>
                      <SortableStepItem
                        id={stepIds[i]}
                        step={step}
                        index={i}
                        editing={editing}
                        toolMap={toolMap}
                        toolCategories={toolCategories}
                        inputs={inputs}
                        steps={steps}
                        setSteps={setSteps}
                        editingStepIdx={editingStepIdx}
                        setEditingStepIdx={setEditingStepIdx}
                        updateStepTool={updateStepTool}
                        updateStepParam={updateStepParam}
                        removeStepParam={removeStepParam}
                        addStepParam={addStepParam}
                        removeStep={removeStep}
                        priorStepOutputs={getOutputKeysFromPriorSteps(i)}
                      />
                      {/* Flow connector between steps */}
                      {i < steps.length - 1 && (
                        <div className="flex justify-center py-0.5">
                          {steps[i + 1]?.tool === "gate" ? (
                            <div className="flex flex-col items-center">
                              <div className="w-px h-2 bg-clay-600" />
                              <div className="w-4 h-4 rounded-full border border-amber-700/60 bg-amber-950/30 flex items-center justify-center">
                                <Filter className="h-2 w-2 text-amber-500" />
                              </div>
                              <div className="w-px h-2 bg-clay-600" />
                            </div>
                          ) : (
                            <div className="w-px h-4 bg-clay-600" />
                          )}
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </SortableContext>
            </DndContext>
          ) : (
            <div>
              {steps.map((step, i) => {
                const toolDef = toolMap[step.tool];
                const hasParams =
                  step.params && Object.keys(step.params).length > 0;
                const isExpanded = expandedSteps.has(i);
                const wiredInputs = stepInputMap[i] || [];

                return (
                  <div key={i}>
                  <div
                    className={cn(
                      "rounded border border-l-4",
                      step.tool === "gate"
                        ? "bg-amber-950/30 border-amber-700/50 border-l-amber-500"
                        : step.tool.startsWith("function:")
                          ? "bg-indigo-950/20 border-indigo-700/40 border-l-indigo-500"
                          : step.tool === "call_ai"
                            ? "bg-clay-900/50 border-clay-700 border-l-blue-500"
                            : step.tool.startsWith("skill:")
                              ? "bg-clay-900/50 border-clay-700 border-l-emerald-500"
                              : "bg-clay-900/50 border-clay-700 border-l-clay-500"
                    )}
                  >
                    <div className="flex items-center gap-2 p-2">
                      <span className="flex items-center justify-center h-5 w-5 rounded-full bg-clay-800 border border-clay-600 text-[10px] text-clay-300 shrink-0">
                        {i + 1}
                      </span>
                      {hasParams ? (
                        <button
                          onClick={() => toggleStepExpanded(i)}
                          className="text-clay-300 hover:text-clay-200"
                        >
                          {isExpanded ? (
                            <ChevronDown className="h-3 w-3" />
                          ) : (
                            <ChevronRight className="h-3 w-3" />
                          )}
                        </button>
                      ) : (
                        <span className="w-3" />
                      )}
                      {toolDef ? (
                        <Tooltip>
                          <TooltipTrigger asChild>
                            <span className="text-xs font-medium text-clay-100 border-b border-dotted border-clay-500 cursor-help">
                              {toolDef.name}
                            </span>
                          </TooltipTrigger>
                          <TooltipContent className="max-w-xs">
                            <div className="space-y-1">
                              <div className="font-medium">
                                {toolDef.name}
                              </div>
                              <div className="text-clay-300 text-[10px]">
                                {toolDef.category} &middot; {step.tool}
                              </div>
                              {toolDef.description && (
                                <div className="text-clay-300 text-[10px]">
                                  {toolDef.description}
                                </div>
                              )}
                              {toolDef.execution_mode && (
                                <div className="text-clay-300 text-[10px]">
                                  Executor: {toolDef.execution_mode === "native" ? "Native API" : toolDef.execution_mode === "ai_agent" ? "AI Agent (web search)" : "AI Single-turn"}
                                  {toolDef.speed && ` · Speed: ${toolDef.speed}`}
                                  {toolDef.cost && ` · Cost: ${toolDef.cost}`}
                                </div>
                              )}
                              {toolDef.ai_fallback_description && (
                                <div className="text-clay-300 text-[10px] italic">
                                  {toolDef.ai_fallback_description}
                                </div>
                              )}
                            </div>
                          </TooltipContent>
                        </Tooltip>
                      ) : (
                        <span className="text-xs font-medium text-clay-100">
                          {step.tool}
                        </span>
                      )}
                      {/* Executor badge */}
                      {toolDef && (
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-[9px] px-1.5 py-0 h-4 shrink-0 border",
                            toolDef.execution_mode === "gate"
                              ? "bg-amber-500/15 text-amber-400 border-amber-500/30"
                              : toolDef.execution_mode === "function"
                                ? "bg-indigo-500/15 text-indigo-400 border-indigo-500/30"
                                : toolDef.has_native_api
                                  ? "bg-emerald-500/15 text-emerald-400 border-emerald-500/30"
                                  : toolDef.execution_mode === "ai_agent"
                                    ? "bg-purple-500/15 text-purple-400 border-purple-500/30"
                                    : "bg-amber-500/15 text-amber-400 border-amber-500/30"
                          )}
                        >
                          {toolDef.execution_mode === "gate"
                            ? "Gate"
                            : toolDef.execution_mode === "function"
                              ? "Function"
                              : toolDef.has_native_api
                                ? `API: ${toolDef.native_api_provider || "Native"}`
                                : toolDef.execution_mode === "ai_agent"
                                  ? "AI Agent"
                                  : "AI Powered"}
                        </Badge>
                      )}
                      {/* Speed badge */}
                      {toolDef?.speed && (
                        <Badge
                          variant="outline"
                          className={cn(
                            "text-[9px] px-1.5 py-0 h-4 shrink-0 border",
                            toolDef.speed === "fast" ? "bg-emerald-500/10 text-emerald-400/70 border-emerald-500/20"
                              : toolDef.speed === "slow" ? "bg-amber-500/10 text-amber-400/70 border-amber-500/20"
                              : "bg-blue-500/10 text-blue-400/70 border-blue-500/20"
                          )}
                        >
                          {toolDef.speed}
                        </Badge>
                      )}
                      {step.tool === "call_ai" && !toolDef && (
                        <Badge
                          variant="outline"
                          className="text-[9px] px-1.5 py-0 h-4 bg-blue-500/15 text-blue-400 border-blue-500/30"
                        >
                          AI Analysis
                        </Badge>
                      )}
                      {step.tool.startsWith("skill:") && !toolDef && (
                        <Badge
                          variant="outline"
                          className="text-[9px] px-1.5 py-0 h-4 bg-blue-500/15 text-blue-400 border-blue-500/30"
                        >
                          Skill
                        </Badge>
                      )}
                      {wiredInputs.length > 0 && (
                        <span className="flex items-center gap-1 ml-1">
                          {wiredInputs.map((wiredName) => (
                            <Badge
                              key={wiredName}
                              variant="outline"
                              className="text-[9px] px-1.5 py-0 h-4 text-kiln-teal border-kiln-teal/30"
                            >
                              {`{{${wiredName}}}`}
                            </Badge>
                          ))}
                        </span>
                      )}
                      {hasParams && (
                        <span className="text-[10px] text-clay-300 ml-auto">
                          {Object.keys(step.params).length} param
                          {Object.keys(step.params).length !== 1
                            ? "s"
                            : ""}
                        </span>
                      )}
                    </div>

                    {/* Expanded params view */}
                    {isExpanded && hasParams && (
                      <div className="border-t border-clay-700 px-4 py-2 space-y-1">
                        {Object.entries(step.params).map(([key, val]) => (
                          <div
                            key={key}
                            className="flex items-baseline gap-2 text-[11px]"
                          >
                            <span className="text-clay-300 font-mono shrink-0">
                              {key}
                            </span>
                            <span className="text-clay-300">=</span>
                            <span className="text-clay-200 break-all">
                              {highlightTemplateVars(val)}
                            </span>
                          </div>
                        ))}
                      </div>
                    )}

                    {/* Output badges */}
                    {toolDef?.outputs && toolDef.outputs.length > 0 && (
                      <div className="px-3 pb-1.5 flex items-center gap-1">
                        <span className="text-[9px] text-clay-400">produces:</span>
                        {toolDef.outputs.map((o) => (
                          <Badge key={o.key} variant="outline" className="text-[9px] px-1 py-0 h-3.5 text-kiln-teal/70 border-kiln-teal/20">
                            {o.key}
                          </Badge>
                        ))}
                      </div>
                    )}
                  </div>
                  {/* Flow connector */}
                  {i < steps.length - 1 && (
                    <div className="flex justify-center py-0.5">
                      {steps[i + 1]?.tool === "gate" ? (
                        <div className="flex flex-col items-center">
                          <div className="w-px h-2 bg-clay-600" />
                          <div className="w-4 h-4 rounded-full border border-amber-700/60 bg-amber-950/30 flex items-center justify-center">
                            <Filter className="h-2 w-2 text-amber-500" />
                          </div>
                          <div className="w-px h-2 bg-clay-600" />
                        </div>
                      ) : (
                        <div className="w-px h-4 bg-clay-600" />
                      )}
                    </div>
                  )}
                  </div>
                );
              })}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

/** Sortable step item for drag-to-reorder in edit mode */
function SortableStepItem({
  id,
  step,
  index: i,
  editing,
  toolMap,
  toolCategories,
  inputs,
  steps,
  setSteps,
  editingStepIdx,
  setEditingStepIdx,
  updateStepTool,
  updateStepParam,
  removeStepParam,
  addStepParam,
  removeStep,
  priorStepOutputs,
}: {
  id: string;
  step: FunctionStep;
  index: number;
  editing: boolean;
  toolMap: Record<string, ToolDefinition>;
  toolCategories: ToolCategory[];
  inputs: FunctionInput[];
  steps: FunctionStep[];
  setSteps: (v: FunctionStep[]) => void;
  editingStepIdx: number | null;
  setEditingStepIdx: (v: number | null) => void;
  updateStepTool: (i: number, tool: string) => void;
  updateStepParam: (stepIdx: number, key: string, value: string, oldKey?: string) => void;
  removeStepParam: (stepIdx: number, key: string) => void;
  addStepParam: (stepIdx: number) => void;
  removeStep: (i: number) => void;
  priorStepOutputs: { stepIdx: number; stepLabel: string; outputKeys: string[] }[];
}) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging,
  } = useSortable({ id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const [toolSearch, setToolSearch] = useState("");
  const toolDef = toolMap[step.tool];
  const isGate = step.tool === "gate";
  const isFunction = step.tool.startsWith("function:");
  const isCallAi = step.tool === "call_ai";
  const hasParams = step.params && Object.keys(step.params).length > 0;

  // Tool icon based on type
  const toolIcon = isGate
    ? <Filter className="h-3 w-3 text-amber-400" />
    : isFunction
      ? <Blocks className="h-3 w-3 text-indigo-400" />
      : isCallAi
        ? <Bot className="h-3 w-3 text-blue-400" />
        : toolDef?.execution_mode === "ai_agent"
          ? <Globe className="h-3 w-3 text-purple-400" />
          : toolDef?.has_native_api
            ? <Zap className="h-3 w-3 text-emerald-400" />
            : <Wrench className="h-3 w-3 text-clay-400" />;

  // Filter tools for search
  const filteredCategories = toolCategories
    .map(cat => ({
      ...cat,
      tools: cat.tools.filter(t =>
        !toolSearch || t.name.toLowerCase().includes(toolSearch.toLowerCase()) ||
        t.id.toLowerCase().includes(toolSearch.toLowerCase()) ||
        t.description?.toLowerCase().includes(toolSearch.toLowerCase())
      ),
    }))
    .filter(cat => cat.tools.length > 0);

  return (
    <div
      ref={setNodeRef}
      style={style}
      className={cn(
        "rounded border border-l-4",
        isGate
          ? "bg-amber-950/30 border-amber-700/50 border-l-amber-500"
          : isFunction
            ? "bg-indigo-950/20 border-indigo-700/40 border-l-indigo-500"
            : isCallAi
              ? "bg-clay-900/50 border-clay-700 border-l-blue-500"
              : step.tool.startsWith("skill:")
                ? "bg-clay-900/50 border-clay-700 border-l-emerald-500"
                : "bg-clay-900/50 border-clay-700 border-l-clay-500",
        isDragging && "opacity-50 z-50"
      )}
    >
      {/* Step header */}
      <div className="flex items-center gap-2 p-2">
        <button
          className="cursor-grab text-clay-300 hover:text-clay-200 touch-none"
          {...attributes}
          {...listeners}
        >
          <GripVertical className="h-3.5 w-3.5" />
        </button>
        <span className="flex items-center justify-center h-5 w-5 rounded-full bg-clay-800 border border-clay-600 text-[10px] text-clay-300 shrink-0">
          {i + 1}
        </span>

        {/* Searchable tool picker */}
        {toolIcon}
        <Popover>
          <PopoverTrigger asChild>
            <button className="text-xs font-medium text-clay-100 hover:text-white border-b border-dotted border-clay-500 truncate max-w-[200px]">
              {toolDef?.name || step.tool || "Select tool..."}
            </button>
          </PopoverTrigger>
          <PopoverContent className="w-72 p-0 bg-clay-900 border-clay-600" align="start">
            <div className="p-2 border-b border-clay-700">
              <div className="relative">
                <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-clay-400" />
                <Input
                  value={toolSearch}
                  onChange={(e) => setToolSearch(e.target.value)}
                  placeholder="Search tools..."
                  className="h-7 pl-7 text-xs bg-clay-800 border-clay-600"
                  autoFocus
                />
              </div>
            </div>
            <div className="max-h-60 overflow-auto p-1">
              {filteredCategories.map(cat => (
                <div key={cat.category} className="mb-1">
                  <div className="text-[10px] text-clay-400 font-medium px-2 py-1 sticky top-0 bg-clay-900">{cat.category}</div>
                  {cat.tools.map(tool => (
                    <button
                      key={tool.id}
                      onClick={() => {
                        // Auto-populate params from tool definition
                        const params: Record<string, string> = {};
                        for (const inp of tool.inputs) params[inp.name] = "";
                        const updated = [...steps];
                        updated[i] = { tool: tool.id, params };
                        setSteps(updated);
                        setToolSearch("");
                      }}
                      className={cn(
                        "w-full text-left px-2 py-1.5 rounded text-xs hover:bg-clay-800 flex items-center gap-2",
                        tool.id === step.tool && "bg-clay-800"
                      )}
                    >
                      <span className="text-clay-100 font-medium truncate flex-1">{tool.name}</span>
                      {tool.speed && (
                        <span className={cn(
                          "text-[9px] px-1 rounded",
                          tool.speed === "fast" || tool.speed === "instant" ? "text-emerald-400" :
                          tool.speed === "slow" ? "text-amber-400" : "text-clay-400"
                        )}>
                          {tool.speed}
                        </span>
                      )}
                    </button>
                  ))}
                </div>
              ))}
              {filteredCategories.length === 0 && (
                <div className="text-xs text-clay-400 text-center py-3">No tools found</div>
              )}
            </div>
          </PopoverContent>
        </Popover>

        {/* Category badge */}
        {toolDef?.category && (
          <span className="text-[9px] text-clay-400 hidden sm:inline">{toolDef.category}</span>
        )}

        <div className="flex-1" />

        <Button
          variant="ghost"
          size="sm"
          onClick={() => removeStep(i)}
          className="h-6 w-6 p-0 text-clay-400 hover:text-red-400"
        >
          <Trash2 className="h-3 w-3" />
        </Button>
      </div>

      {/* Gate inline config */}
      {isGate && editing && (
        <div className="border-t border-amber-700/30 px-3 py-2 space-y-1.5">
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-amber-400 font-medium w-16 shrink-0">Condition</span>
            <Input
              value={step.params.condition || ""}
              onChange={(e) => updateStepParam(i, "condition", e.target.value)}
              placeholder="e.g. qualified == 'Y' or score >= 70"
              className="h-6 text-xs bg-amber-950/20 border-amber-700/30 text-amber-200 placeholder:text-amber-800"
            />
          </div>
          <div className="flex items-center gap-2">
            <span className="text-[10px] text-amber-400 font-medium w-16 shrink-0">Label</span>
            <Input
              value={step.params.label || ""}
              onChange={(e) => updateStepParam(i, "label", e.target.value)}
              placeholder="e.g. qualification-gate"
              className="h-6 text-xs bg-amber-950/20 border-amber-700/30 text-amber-200 placeholder:text-amber-800"
            />
          </div>
        </div>
      )}

      {/* Function step info */}
      {isFunction && toolDef && (
        <div className="border-t border-indigo-700/30 px-3 py-1.5">
          <div className="text-[10px] text-indigo-300/70">{toolDef.description}</div>
          {toolDef.outputs && toolDef.outputs.length > 0 && (
            <div className="flex items-center gap-1 mt-1">
              <span className="text-[9px] text-clay-400">outputs:</span>
              {toolDef.outputs.map(o => (
                <Badge key={o.key} variant="outline" className="text-[9px] px-1 py-0 h-3.5 text-indigo-400/70 border-indigo-500/20">
                  {o.key}
                </Badge>
              ))}
            </div>
          )}
        </div>
      )}

      {/* Step params (always visible in edit mode, except gate which has custom UI) */}
      {editing && !isGate && hasParams && (
        <div className="border-t border-clay-700 px-3 py-2 space-y-2">
          {Object.entries(step.params).map(([key, val]) => (
            <div key={key} className="flex items-start gap-2">
              <Input
                value={key}
                onChange={(e) => updateStepParam(i, e.target.value, val, key)}
                className="bg-clay-900 border-clay-600 text-clay-100 text-xs h-7 w-24 font-mono shrink-0"
                placeholder="key"
              />
              <span className="text-clay-300 text-xs mt-1.5">=</span>
              {isCallAi && key === "prompt" ? (
                <div className="flex-1 space-y-1">
                  <Textarea
                    value={val}
                    onChange={(e) => updateStepParam(i, key, e.target.value)}
                    rows={4}
                    className="bg-clay-900 border-clay-600 text-clay-100 text-xs font-mono resize-y"
                    placeholder="Enter your AI prompt..."
                  />
                  {val && (
                    <div className="text-[10px] text-clay-300 leading-relaxed px-1">
                      {highlightTemplateVars(val)}
                    </div>
                  )}
                </div>
              ) : (
                <Input
                  value={val}
                  onChange={(e) => updateStepParam(i, key, e.target.value)}
                  className="bg-clay-900 border-clay-600 text-clay-100 text-xs h-7 flex-1"
                  placeholder="value or {{variable}}"
                />
              )}
              <Button
                variant="ghost"
                size="sm"
                onClick={() => removeStepParam(i, key)}
                className="h-6 w-6 p-0 text-clay-400 hover:text-red-400 shrink-0"
              >
                <Trash2 className="h-3 w-3" />
              </Button>
            </div>
          ))}

          {/* Insert variable buttons */}
          <div className="flex flex-wrap items-center gap-1.5 pt-1">
            <Button variant="ghost" size="sm" onClick={() => addStepParam(i)} className="text-clay-300 h-5 text-[10px] px-1.5">
              <Plus className="h-2.5 w-2.5 mr-0.5" /> param
            </Button>
            {inputs.length > 0 && (
              <>
                <span className="text-[9px] text-clay-400">|</span>
                {inputs.map((inp) => (
                  <button
                    key={inp.name}
                    onClick={() => {
                      const paramKeys = Object.keys(step.params);
                      if (paramKeys.length > 0) {
                        const lastKey = paramKeys[paramKeys.length - 1];
                        updateStepParam(i, lastKey, step.params[lastKey] + `{{${inp.name}}}`);
                      } else {
                        addStepParam(i);
                        const updated = [...steps];
                        const params = { ...updated[i].params };
                        const newKey = Object.keys(params).pop() || "param";
                        params[newKey] = `{{${inp.name}}}`;
                        updated[i] = { ...updated[i], params };
                        setSteps(updated);
                      }
                    }}
                    className="text-[10px] px-1.5 py-0.5 rounded bg-kiln-teal/10 text-kiln-teal hover:bg-kiln-teal/20 transition-colors"
                  >
                    {`{{${inp.name}}}`}
                  </button>
                ))}
              </>
            )}
            {priorStepOutputs.length > 0 && (
              <>
                <span className="text-[9px] text-clay-400">|</span>
                {priorStepOutputs.flatMap((ps) =>
                  ps.outputKeys.map((outKey) => (
                    <button
                      key={`${ps.stepIdx}-${outKey}`}
                      onClick={() => {
                        const paramKeys = Object.keys(step.params);
                        if (paramKeys.length > 0) {
                          const lastKey = paramKeys[paramKeys.length - 1];
                          updateStepParam(i, lastKey, step.params[lastKey] + `{{${outKey}}}`);
                        } else {
                          addStepParam(i);
                          const updated = [...steps];
                          const params = { ...updated[i].params };
                          const newKey = Object.keys(params).pop() || "param";
                          params[newKey] = `{{${outKey}}}`;
                          updated[i] = { ...updated[i], params };
                          setSteps(updated);
                        }
                      }}
                      className="text-[10px] px-1.5 py-0.5 rounded bg-purple-500/10 text-purple-400 hover:bg-purple-500/20 transition-colors"
                      title={`From step ${ps.stepIdx + 1}: ${ps.stepLabel}`}
                    >
                      {`{{${outKey}}}`}
                    </button>
                  ))
                )}
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
}
