"use client";

import { useState, useEffect, useCallback } from "react";
import { useParams, useRouter } from "next/navigation";
import { Header } from "@/components/layout/header";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import {
  fetchFunction,
  updateFunction,
  deleteFunction,
  fetchToolCategories,
  generateFunctionClayConfig,
} from "@/lib/api";
import type {
  FunctionDefinition,
  FunctionInput,
  FunctionOutput,
  FunctionStep,
  ToolCategory,
} from "@/lib/types";
import { cn } from "@/lib/utils";
import {
  ArrowLeft,
  Plus,
  Trash2,
  GripVertical,
  Play,
  Copy,
  Save,
  ChevronDown,
  ChevronRight,
  Pencil,
  Blocks,
  Settings,
  Wrench,
  X,
} from "lucide-react";
import { toast } from "sonner";

export default function FunctionDetailPage() {
  const params = useParams();
  const router = useRouter();
  const funcId = params.id as string;

  const [func, setFunc] = useState<FunctionDefinition | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [toolCategories, setToolCategories] = useState<ToolCategory[]>([]);
  const [catalogOpen, setCatalogOpen] = useState(false);
  const [clayWizardOpen, setClayWizardOpen] = useState(false);
  const [clayConfig, setClayConfig] = useState<Record<string, unknown> | null>(null);
  const [clayWizardStep, setClayWizardStep] = useState(0);

  // Editable fields
  const [name, setName] = useState("");
  const [description, setDescription] = useState("");
  const [folder, setFolder] = useState("");
  const [inputs, setInputs] = useState<FunctionInput[]>([]);
  const [outputs, setOutputs] = useState<FunctionOutput[]>([]);
  const [steps, setSteps] = useState<FunctionStep[]>([]);

  const load = useCallback(async () => {
    try {
      const f = await fetchFunction(funcId);
      setFunc(f);
      setName(f.name);
      setDescription(f.description);
      setFolder(f.folder);
      setInputs(f.inputs);
      setOutputs(f.outputs);
      setSteps(f.steps);
    } catch {
      toast.error("Function not found");
      router.push("/");
    } finally {
      setLoading(false);
    }
  }, [funcId, router]);

  useEffect(() => {
    load();
    fetchToolCategories().then(r => setToolCategories(r.categories)).catch(() => {});
  }, [load]);

  const handleSave = async () => {
    setSaving(true);
    try {
      const updated = await updateFunction(funcId, {
        name,
        description,
        folder,
        inputs,
        outputs,
        steps,
      });
      setFunc(updated);
      setEditing(false);
      toast.success("Function saved");
    } catch {
      toast.error("Failed to save");
    } finally {
      setSaving(false);
    }
  };

  const handleDelete = async () => {
    if (!confirm("Delete this function?")) return;
    try {
      await deleteFunction(funcId);
      toast.success("Function deleted");
      router.push("/");
    } catch {
      toast.error("Failed to delete");
    }
  };

  const handleCopyClayConfig = () => {
    if (!func) return;
    const config = {
      url: `{{API_URL}}/webhook`,
      method: "POST",
      headers: { "Content-Type": "application/json", "x-api-key": "{{API_KEY}}" },
      body: {
        function: func.id,
        data: Object.fromEntries(func.inputs.map(i => [i.name, `{{${i.name}}}`])),
      },
    };
    navigator.clipboard.writeText(JSON.stringify(config, null, 2));
    toast.success("Clay config copied");
  };

  const openClayWizard = async () => {
    if (!func) return;
    try {
      const config = await generateFunctionClayConfig(func.id);
      setClayConfig(config);
      setClayWizardStep(0);
      setClayWizardOpen(true);
    } catch {
      toast.error("Failed to generate Clay config");
    }
  };

  const addInput = () => {
    setInputs([...inputs, { name: "", type: "string", required: true, description: "" }]);
  };

  const removeInput = (i: number) => {
    setInputs(inputs.filter((_, idx) => idx !== i));
  };

  const updateInput = (i: number, field: keyof FunctionInput, value: string | boolean) => {
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

  const updateOutput = (i: number, field: keyof FunctionOutput, value: string) => {
    const updated = [...outputs];
    (updated[i] as unknown as Record<string, unknown>)[field] = value;
    setOutputs(updated);
  };

  const addStep = (tool?: string) => {
    setSteps([...steps, { tool: tool || "", params: {} }]);
    setCatalogOpen(false);
  };

  const removeStep = (i: number) => {
    setSteps(steps.filter((_, idx) => idx !== i));
  };

  const updateStepTool = (i: number, tool: string) => {
    const updated = [...steps];
    updated[i] = { ...updated[i], tool };
    setSteps(updated);
  };

  if (loading) {
    return (
      <div className="flex flex-col h-full">
        <Header title="Function" />
        <div className="flex-1 flex items-center justify-center text-clay-300">Loading...</div>
      </div>
    );
  }

  if (!func) return null;

  return (
    <div className="flex flex-col h-full">
      <Header
        title={func.name}
        breadcrumbs={[
          { label: "Functions", href: "/" },
          { label: func.name },
        ]}
      />

      <div className="flex-1 overflow-auto p-4 md:p-6 pb-20 md:pb-6">
        {/* Toolbar */}
        <div className="flex items-center justify-between mb-6">
          <Button
            variant="ghost"
            size="sm"
            onClick={() => router.push("/")}
            className="text-clay-300 hover:text-clay-100"
          >
            <ArrowLeft className="h-4 w-4 mr-1" />
            Back
          </Button>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={openClayWizard}
              className="border-clay-600 text-clay-300"
            >
              <Copy className="h-3.5 w-3.5 mr-1.5" />
              Copy to Clay
            </Button>
            <Button
              variant="outline"
              size="sm"
              onClick={() => router.push(`/workbench?function=${func.id}`)}
              className="border-clay-600 text-clay-300"
            >
              <Play className="h-3.5 w-3.5 mr-1.5" />
              Run in Workbench
            </Button>
            {editing ? (
              <>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={() => { setEditing(false); load(); }}
                  className="border-clay-600 text-clay-300"
                >
                  Cancel
                </Button>
                <Button
                  size="sm"
                  onClick={handleSave}
                  disabled={saving}
                  className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light"
                >
                  <Save className="h-3.5 w-3.5 mr-1.5" />
                  {saving ? "Saving..." : "Save"}
                </Button>
              </>
            ) : (
              <>
                <Button
                  size="sm"
                  onClick={() => setEditing(true)}
                  className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light"
                >
                  <Pencil className="h-3.5 w-3.5 mr-1.5" />
                  Edit
                </Button>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={handleDelete}
                  className="text-red-400 hover:text-red-300"
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </Button>
              </>
            )}
          </div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          {/* Main content */}
          <div className="lg:col-span-2 space-y-6">
            {/* Info */}
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
                      <label className="text-xs text-clay-400 mb-1 block">Name</label>
                      <Input value={name} onChange={e => setName(e.target.value)} className="bg-clay-900 border-clay-600 text-clay-100" />
                    </div>
                    <div>
                      <label className="text-xs text-clay-400 mb-1 block">Description</label>
                      <textarea value={description} onChange={e => setDescription(e.target.value)} rows={2} className="w-full rounded-md bg-clay-900 border border-clay-600 text-clay-100 text-sm p-2.5 focus:outline-none focus:ring-1 focus:ring-kiln-teal" />
                    </div>
                    <div>
                      <label className="text-xs text-clay-400 mb-1 block">Folder</label>
                      <Input value={folder} onChange={e => setFolder(e.target.value)} className="bg-clay-900 border-clay-600 text-clay-100" />
                    </div>
                  </>
                ) : (
                  <>
                    <div className="text-sm text-clay-200">{func.description || "No description"}</div>
                    <div className="text-xs text-clay-400">Folder: {func.folder} | ID: {func.id}</div>
                  </>
                )}
              </CardContent>
            </Card>

            {/* Inputs */}
            <Card className="border-clay-600">
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-sm text-clay-200">Inputs ({inputs.length})</CardTitle>
                  {editing && (
                    <Button variant="ghost" size="sm" onClick={addInput} className="text-clay-300 h-7 text-xs">
                      <Plus className="h-3 w-3 mr-1" /> Add
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {inputs.length === 0 ? (
                  <div className="text-xs text-clay-500 py-2">No inputs defined</div>
                ) : (
                  <div className="space-y-2">
                    {inputs.map((inp, i) => (
                      <div key={i} className="flex items-center gap-2 p-2 rounded bg-clay-900/50 border border-clay-700">
                        {editing ? (
                          <>
                            <Input value={inp.name} onChange={e => updateInput(i, "name", e.target.value)} placeholder="Name" className="bg-clay-900 border-clay-600 text-clay-100 text-xs h-7 flex-1" />
                            <select value={inp.type} onChange={e => updateInput(i, "type", e.target.value)} className="bg-clay-900 border border-clay-600 text-clay-100 text-xs rounded h-7 px-1">
                              {["string", "number", "url", "email", "boolean"].map(t => <option key={t} value={t}>{t}</option>)}
                            </select>
                            <label className="flex items-center gap-1 text-xs text-clay-300">
                              <input type="checkbox" checked={inp.required} onChange={e => updateInput(i, "required", e.target.checked)} className="rounded" />
                              Req
                            </label>
                            <Button variant="ghost" size="sm" onClick={() => removeInput(i)} className="h-6 w-6 p-0 text-red-400"><Trash2 className="h-3 w-3" /></Button>
                          </>
                        ) : (
                          <div className="flex items-center gap-2 text-xs">
                            <span className="font-medium text-clay-100">{inp.name}</span>
                            <span className="text-clay-400">({inp.type})</span>
                            {inp.required && <span className="text-red-400 text-[10px]">required</span>}
                            {inp.description && <span className="text-clay-500">— {inp.description}</span>}
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
                  <CardTitle className="text-sm text-clay-200">Outputs ({outputs.length})</CardTitle>
                  {editing && (
                    <Button variant="ghost" size="sm" onClick={addOutput} className="text-clay-300 h-7 text-xs">
                      <Plus className="h-3 w-3 mr-1" /> Add
                    </Button>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {outputs.length === 0 ? (
                  <div className="text-xs text-clay-500 py-2">No outputs defined</div>
                ) : (
                  <div className="space-y-2">
                    {outputs.map((out, i) => (
                      <div key={i} className="flex items-center gap-2 p-2 rounded bg-clay-900/50 border border-clay-700">
                        {editing ? (
                          <>
                            <Input value={out.key} onChange={e => updateOutput(i, "key", e.target.value)} placeholder="Key" className="bg-clay-900 border-clay-600 text-clay-100 text-xs h-7 flex-1" />
                            <select value={out.type} onChange={e => updateOutput(i, "type", e.target.value)} className="bg-clay-900 border border-clay-600 text-clay-100 text-xs rounded h-7 px-1">
                              {["string", "number", "boolean", "json"].map(t => <option key={t} value={t}>{t}</option>)}
                            </select>
                            <Input value={out.description} onChange={e => updateOutput(i, "description", e.target.value)} placeholder="Description" className="bg-clay-900 border-clay-600 text-clay-100 text-xs h-7 flex-1" />
                            <Button variant="ghost" size="sm" onClick={() => removeOutput(i)} className="h-6 w-6 p-0 text-red-400"><Trash2 className="h-3 w-3" /></Button>
                          </>
                        ) : (
                          <div className="flex items-center gap-2 text-xs">
                            <span className="font-medium text-kiln-teal">{out.key}</span>
                            <span className="text-clay-400">({out.type})</span>
                            {out.description && <span className="text-clay-500">— {out.description}</span>}
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
                      <Button variant="ghost" size="sm" onClick={() => setCatalogOpen(!catalogOpen)} className="text-clay-300 h-7 text-xs">
                        <Blocks className="h-3 w-3 mr-1" /> Browse Tools
                      </Button>
                      <Button variant="ghost" size="sm" onClick={() => addStep()} className="text-clay-300 h-7 text-xs">
                        <Plus className="h-3 w-3 mr-1" /> Add Step
                      </Button>
                    </div>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {steps.length === 0 ? (
                  <div className="text-xs text-clay-500 py-2">No steps defined. Add tools to build this function.</div>
                ) : (
                  <div className="space-y-2">
                    {steps.map((step, i) => (
                      <div key={i} className="flex items-center gap-2 p-2 rounded bg-clay-900/50 border border-clay-700">
                        <span className="text-[10px] text-clay-500 w-4">{i + 1}</span>
                        {editing ? (
                          <>
                            <Input value={step.tool} onChange={e => updateStepTool(i, e.target.value)} placeholder="Tool ID" className="bg-clay-900 border-clay-600 text-clay-100 text-xs h-7 flex-1" />
                            <Button variant="ghost" size="sm" onClick={() => removeStep(i)} className="h-6 w-6 p-0 text-red-400"><Trash2 className="h-3 w-3" /></Button>
                          </>
                        ) : (
                          <span className="text-xs font-medium text-clay-100">{step.tool}</span>
                        )}
                      </div>
                    ))}
                  </div>
                )}
              </CardContent>
            </Card>
          </div>

          {/* Sidebar: Tool catalog browser (when editing) */}
          <div className="space-y-4">
            {/* Clay config preview */}
            <Card className="border-clay-600">
              <CardHeader className="pb-3">
                <CardTitle className="text-sm text-clay-200">Clay Config</CardTitle>
              </CardHeader>
              <CardContent>
                <pre className="text-[10px] text-clay-300 bg-clay-900 p-2 rounded overflow-auto max-h-40">
                  {JSON.stringify({
                    function: func.id,
                    data: Object.fromEntries(inputs.map(i => [i.name, `{{${i.name}}}`])),
                  }, null, 2)}
                </pre>
                <Button
                  variant="outline"
                  size="sm"
                  onClick={handleCopyClayConfig}
                  className="w-full mt-2 border-clay-600 text-clay-300 text-xs"
                >
                  <Copy className="h-3 w-3 mr-1" />
                  Copy Config
                </Button>
              </CardContent>
            </Card>

            {/* Tool catalog (when browsing) */}
            {editing && catalogOpen && (
              <Card className="border-clay-600">
                <CardHeader className="pb-3">
                  <CardTitle className="text-sm text-clay-200">Tool Catalog</CardTitle>
                </CardHeader>
                <CardContent className="max-h-96 overflow-auto">
                  {toolCategories.map(cat => (
                    <div key={cat.category} className="mb-3">
                      <div className="text-[10px] text-clay-400 uppercase tracking-wider mb-1">{cat.category}</div>
                      <div className="space-y-1">
                        {cat.tools.map(tool => (
                          <button
                            key={tool.id}
                            onClick={() => addStep(tool.id)}
                            className="w-full text-left px-2 py-1.5 rounded text-xs hover:bg-clay-700 transition-colors"
                          >
                            <div className="font-medium text-clay-100">{tool.name}</div>
                            <div className="text-[10px] text-clay-400 line-clamp-1">{tool.description}</div>
                          </button>
                        ))}
                      </div>
                    </div>
                  ))}
                </CardContent>
              </Card>
            )}

            {/* Metadata */}
            <Card className="border-clay-600">
              <CardContent className="p-4 text-xs text-clay-400 space-y-1">
                <div>Created: {new Date(func.created_at * 1000).toLocaleDateString()}</div>
                <div>Updated: {new Date(func.updated_at * 1000).toLocaleDateString()}</div>
                <div>ID: {func.id}</div>
              </CardContent>
            </Card>
          </div>
        </div>
      </div>

      {/* Copy-to-Clay Wizard (CLAY-03) */}
      {clayWizardOpen && clayConfig && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-clay-800 border border-clay-600 rounded-xl w-full max-w-lg mx-4 shadow-2xl">
            {/* Wizard header */}
            <div className="flex items-center justify-between p-4 border-b border-clay-600">
              <h3 className="text-lg font-semibold text-clay-100">Copy to Clay</h3>
              <div className="flex items-center gap-2">
                <span className="text-xs text-clay-400">Step {clayWizardStep + 1} of 3</span>
                <Button variant="ghost" size="sm" onClick={() => setClayWizardOpen(false)} className="text-clay-400">
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Step content */}
            <div className="p-6">
              {clayWizardStep === 0 && (
                <div className="space-y-4">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="h-8 w-8 rounded-full bg-kiln-teal/10 flex items-center justify-center text-kiln-teal font-bold text-sm">1</div>
                    <div>
                      <div className="text-sm font-medium text-clay-100">Create an HTTP API column in Clay</div>
                      <div className="text-xs text-clay-400">Add a new column and select &quot;HTTP API&quot; as the type</div>
                    </div>
                  </div>
                  <div className="bg-clay-900 rounded-lg p-4 text-xs text-clay-300 space-y-2">
                    <p>1. Open your Clay table</p>
                    <p>2. Click &quot;+ Add Column&quot;</p>
                    <p>3. Search for &quot;HTTP API&quot; and select it</p>
                    <p>4. Name the column (e.g., &quot;{func.name}&quot;)</p>
                  </div>
                </div>
              )}

              {clayWizardStep === 1 && (
                <div className="space-y-4">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="h-8 w-8 rounded-full bg-kiln-teal/10 flex items-center justify-center text-kiln-teal font-bold text-sm">2</div>
                    <div>
                      <div className="text-sm font-medium text-clay-100">Paste this configuration</div>
                      <div className="text-xs text-clay-400">Copy the config below and paste it into the HTTP API column settings</div>
                    </div>
                  </div>
                  <pre className="bg-clay-900 rounded-lg p-3 text-[10px] text-clay-300 overflow-auto max-h-48">
                    {JSON.stringify(clayConfig.body_template || clayConfig, null, 2)}
                  </pre>
                  <Button
                    size="sm"
                    onClick={() => {
                      navigator.clipboard.writeText(JSON.stringify(clayConfig.body_template || clayConfig, null, 2));
                      toast.success("Configuration copied!");
                    }}
                    className="w-full bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light"
                  >
                    <Copy className="h-3.5 w-3.5 mr-2" />
                    Copy Configuration
                  </Button>
                </div>
              )}

              {clayWizardStep === 2 && (
                <div className="space-y-4">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="h-8 w-8 rounded-full bg-kiln-teal/10 flex items-center justify-center text-kiln-teal font-bold text-sm">3</div>
                    <div>
                      <div className="text-sm font-medium text-clay-100">Map these columns</div>
                      <div className="text-xs text-clay-400">Ensure your Clay columns match these inputs and outputs</div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <div className="text-xs text-clay-400 uppercase tracking-wider mb-1">Inputs (Clay columns → Function)</div>
                      <div className="bg-clay-900 rounded-lg divide-y divide-clay-700">
                        {func.inputs.map(inp => (
                          <div key={inp.name} className="flex items-center justify-between px-3 py-2 text-xs">
                            <span className="text-clay-200">{`{{${inp.name}}}`}</span>
                            <span className="text-clay-400">→</span>
                            <span className="text-clay-100 font-medium">{inp.name}</span>
                            {inp.required && <span className="text-red-400 text-[10px]">required</span>}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <div className="text-xs text-clay-400 uppercase tracking-wider mb-1">Outputs (Function → Clay columns)</div>
                      <div className="bg-clay-900 rounded-lg divide-y divide-clay-700">
                        {func.outputs.map(out => (
                          <div key={out.key} className="flex items-center justify-between px-3 py-2 text-xs">
                            <span className="text-kiln-teal font-medium">{out.key}</span>
                            <span className="text-clay-400">→</span>
                            <span className="text-clay-200">{out.key} ({out.type})</span>
                          </div>
                        ))}
                        {func.outputs.length === 0 && (
                          <div className="px-3 py-2 text-xs text-clay-500">No outputs defined yet</div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            {/* Wizard footer */}
            <div className="flex items-center justify-between p-4 border-t border-clay-600">
              <Button
                variant="outline"
                size="sm"
                onClick={() => setClayWizardStep(Math.max(0, clayWizardStep - 1))}
                disabled={clayWizardStep === 0}
                className="border-clay-600 text-clay-300"
              >
                Back
              </Button>
              {clayWizardStep < 2 ? (
                <Button
                  size="sm"
                  onClick={() => setClayWizardStep(clayWizardStep + 1)}
                  className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light"
                >
                  Next
                  <ChevronRight className="h-3.5 w-3.5 ml-1" />
                </Button>
              ) : (
                <Button
                  size="sm"
                  onClick={() => setClayWizardOpen(false)}
                  className="bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light"
                >
                  Done
                </Button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
