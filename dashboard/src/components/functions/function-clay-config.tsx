"use client";

import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Copy, ChevronRight, X } from "lucide-react";
import { toast } from "sonner";
import type {
  FunctionDefinition,
  FunctionInput,
  ToolCategory,
} from "@/lib/types";

interface FunctionClayConfigProps {
  func: FunctionDefinition;
  inputs: FunctionInput[];
  // Tool catalog
  editing: boolean;
  catalogOpen: boolean;
  toolCategories: ToolCategory[];
  onAddStep: (tool: string) => void;
  // Clay wizard
  clayWizardOpen: boolean;
  setClayWizardOpen: (v: boolean) => void;
  clayConfig: Record<string, unknown> | null;
  clayWizardStep: number;
  setClayWizardStep: (v: number) => void;
  onCopyConfig: () => void;
  onOpenWizard: () => void;
}

export function FunctionClayConfig({
  func,
  inputs,
  editing,
  catalogOpen,
  toolCategories,
  onAddStep,
  clayWizardOpen,
  setClayWizardOpen,
  clayConfig,
  clayWizardStep,
  setClayWizardStep,
  onCopyConfig,
  onOpenWizard,
}: FunctionClayConfigProps) {
  return (
    <>
      <div className="space-y-4">
        {/* Clay config preview */}
        <Card className="border-clay-600">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm text-clay-200">Clay Config</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            <div>
              <div className="text-[10px] text-clay-400 uppercase tracking-wider mb-1">
                Webhook URL
              </div>
              <div className="flex items-center gap-1">
                <code className="flex-1 text-xs text-kiln-teal bg-clay-900 px-2 py-1.5 rounded border border-clay-700 truncate">
                  {`https://clay.nomynoms.com/webhook/functions/${func.id}`}
                </code>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => {
                    navigator.clipboard.writeText(
                      `https://clay.nomynoms.com/webhook/functions/${func.id}`
                    );
                    toast.success("URL copied");
                  }}
                  className="h-7 w-7 p-0 text-clay-400 hover:text-clay-200 shrink-0"
                >
                  <Copy className="h-3 w-3" />
                </Button>
              </div>
            </div>

            <div>
              <div className="text-[10px] text-clay-400 uppercase tracking-wider mb-1">
                Method
              </div>
              <code className="text-xs text-clay-200 bg-clay-900 px-2 py-1 rounded border border-clay-700">
                POST
              </code>
            </div>

            <div>
              <div className="text-[10px] text-clay-400 uppercase tracking-wider mb-1">
                Body Template
              </div>
              <pre className="text-[10px] text-clay-300 bg-clay-900 p-2 rounded border border-clay-700 overflow-auto max-h-32">
                {JSON.stringify(
                  {
                    data: Object.fromEntries(
                      inputs.map((i) => [i.name, `{{${i.name}}}`])
                    ),
                  },
                  null,
                  2
                )}
              </pre>
            </div>

            <div className="flex gap-2">
              <Button
                variant="outline"
                size="sm"
                onClick={onCopyConfig}
                className="flex-1 border-clay-600 text-clay-300 text-xs"
              >
                <Copy className="h-3 w-3 mr-1" />
                Copy Full Config
              </Button>
              <Button
                variant="outline"
                size="sm"
                onClick={onOpenWizard}
                className="flex-1 border-clay-600 text-clay-300 text-xs"
              >
                Setup Wizard
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Tool catalog (when browsing) */}
        {editing && catalogOpen && (
          <Card className="border-clay-600">
            <CardHeader className="pb-3">
              <CardTitle className="text-sm text-clay-200">
                Tool Catalog
              </CardTitle>
            </CardHeader>
            <CardContent className="max-h-96 overflow-auto">
              {toolCategories.map((cat) => (
                <div key={cat.category} className="mb-3">
                  <div className="text-[10px] text-clay-400 uppercase tracking-wider mb-1">
                    {cat.category}
                  </div>
                  <div className="space-y-1">
                    {cat.tools.map((tool) => (
                      <button
                        key={tool.id}
                        onClick={() => onAddStep(tool.id)}
                        className="w-full text-left px-2 py-1.5 rounded text-xs hover:bg-clay-700 transition-colors"
                      >
                        <div className="font-medium text-clay-100">
                          {tool.name}
                        </div>
                        <div className="text-[10px] text-clay-400 line-clamp-1">
                          {tool.description}
                        </div>
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
            <div>
              Created:{" "}
              {new Date(func.created_at * 1000).toLocaleDateString()}
            </div>
            <div>
              Updated:{" "}
              {new Date(func.updated_at * 1000).toLocaleDateString()}
            </div>
            <div>ID: {func.id}</div>
          </CardContent>
        </Card>
      </div>

      {/* Copy-to-Clay Wizard */}
      {clayWizardOpen && clayConfig && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 backdrop-blur-sm">
          <div className="bg-clay-800 border border-clay-600 rounded-xl w-full max-w-lg mx-4 shadow-2xl">
            <div className="flex items-center justify-between p-4 border-b border-clay-600">
              <h3 className="text-lg font-semibold text-clay-100">
                Copy to Clay
              </h3>
              <div className="flex items-center gap-2">
                <span className="text-xs text-clay-400">
                  Step {clayWizardStep + 1} of 3
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setClayWizardOpen(false)}
                  className="text-clay-400"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="p-6">
              {clayWizardStep === 0 && (
                <div className="space-y-4">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="h-8 w-8 rounded-full bg-kiln-teal/10 flex items-center justify-center text-kiln-teal font-bold text-sm">
                      1
                    </div>
                    <div>
                      <div className="text-sm font-medium text-clay-100">
                        Create an HTTP API column in Clay
                      </div>
                      <div className="text-xs text-clay-400">
                        Add a new column and select &quot;HTTP API&quot; as the
                        type
                      </div>
                    </div>
                  </div>
                  <div className="bg-clay-900 rounded-lg p-4 text-xs text-clay-300 space-y-2">
                    <p>1. Open your Clay table</p>
                    <p>2. Click &quot;+ Add Column&quot;</p>
                    <p>
                      3. Search for &quot;HTTP API&quot; and select it
                    </p>
                    <p>
                      4. Name the column (e.g., &quot;{func.name}&quot;)
                    </p>
                  </div>
                </div>
              )}

              {clayWizardStep === 1 && (
                <div className="space-y-4">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="h-8 w-8 rounded-full bg-kiln-teal/10 flex items-center justify-center text-kiln-teal font-bold text-sm">
                      2
                    </div>
                    <div>
                      <div className="text-sm font-medium text-clay-100">
                        Paste this configuration
                      </div>
                      <div className="text-xs text-clay-400">
                        Copy the config below and paste it into the HTTP API
                        column settings
                      </div>
                    </div>
                  </div>
                  <pre className="bg-clay-900 rounded-lg p-3 text-[10px] text-clay-300 overflow-auto max-h-48">
                    {JSON.stringify(
                      clayConfig.body_template || clayConfig,
                      null,
                      2
                    )}
                  </pre>
                  <Button
                    size="sm"
                    onClick={() => {
                      navigator.clipboard.writeText(
                        JSON.stringify(
                          clayConfig.body_template || clayConfig,
                          null,
                          2
                        )
                      );
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
                    <div className="h-8 w-8 rounded-full bg-kiln-teal/10 flex items-center justify-center text-kiln-teal font-bold text-sm">
                      3
                    </div>
                    <div>
                      <div className="text-sm font-medium text-clay-100">
                        Map these columns
                      </div>
                      <div className="text-xs text-clay-400">
                        Ensure your Clay columns match these inputs and outputs
                      </div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    <div>
                      <div className="text-xs text-clay-400 uppercase tracking-wider mb-1">
                        Inputs (Clay columns → Function)
                      </div>
                      <div className="bg-clay-900 rounded-lg divide-y divide-clay-700">
                        {func.inputs.map((inp) => (
                          <div
                            key={inp.name}
                            className="flex items-center justify-between px-3 py-2 text-xs"
                          >
                            <span className="text-clay-200">{`{{${inp.name}}}`}</span>
                            <span className="text-clay-400">→</span>
                            <span className="text-clay-100 font-medium">
                              {inp.name}
                            </span>
                            {inp.required && (
                              <span className="text-red-400 text-[10px]">
                                required
                              </span>
                            )}
                          </div>
                        ))}
                      </div>
                    </div>

                    <div>
                      <div className="text-xs text-clay-400 uppercase tracking-wider mb-1">
                        Outputs (Function → Clay columns)
                      </div>
                      <div className="bg-clay-900 rounded-lg divide-y divide-clay-700">
                        {func.outputs.map((out) => (
                          <div
                            key={out.key}
                            className="flex items-center justify-between px-3 py-2 text-xs"
                          >
                            <span className="text-kiln-teal font-medium">
                              {out.key}
                            </span>
                            <span className="text-clay-400">→</span>
                            <span className="text-clay-200">
                              {out.key} ({out.type})
                            </span>
                          </div>
                        ))}
                        {func.outputs.length === 0 && (
                          <div className="px-3 py-2 text-xs text-clay-500">
                            No outputs defined yet
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>

            <div className="flex items-center justify-between p-4 border-t border-clay-600">
              <Button
                variant="outline"
                size="sm"
                onClick={() =>
                  setClayWizardStep(Math.max(0, clayWizardStep - 1))
                }
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
    </>
  );
}
