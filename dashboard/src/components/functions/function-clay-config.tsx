"use client";

import { useState, useMemo } from "react";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Copy, ChevronRight, X, Terminal, Key, Clock, Globe, Search } from "lucide-react";
import { toast } from "sonner";
import type {
  FunctionDefinition,
  FunctionInput,
  ToolCategory,
  ToolDefinition,
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

function CopyButton({ text, label }: { text: string; label?: string }) {
  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={() => {
        navigator.clipboard.writeText(text);
        toast.success(label || "Copied");
      }}
      className="h-7 w-7 p-0 text-clay-300 hover:text-clay-200 shrink-0"
    >
      <Copy className="h-3 w-3" />
    </Button>
  );
}

function ToolCatalogPanel({
  toolCategories,
  onAddStep,
}: {
  toolCategories: ToolCategory[];
  onAddStep: (tool: string) => void;
}) {
  const [catalogSearch, setCatalogSearch] = useState("");

  const allTools = useMemo(
    () => toolCategories.flatMap((cat) => cat.tools),
    [toolCategories]
  );

  const filtered = useMemo(() => {
    if (!catalogSearch.trim()) return null;
    const q = catalogSearch.toLowerCase();
    return allTools.filter(
      (t) =>
        t.name.toLowerCase().includes(q) ||
        t.description.toLowerCase().includes(q)
    );
  }, [catalogSearch, allTools]);

  return (
    <Card className="border-clay-600">
      <CardHeader className="pb-3">
        <CardTitle className="text-sm text-clay-200">Tool Catalog</CardTitle>
      </CardHeader>
      <CardContent className="space-y-2">
        {/* Search input */}
        <div className="relative">
          <Search className="absolute left-2 top-1/2 -translate-y-1/2 h-3 w-3 text-clay-300" />
          <Input
            value={catalogSearch}
            onChange={(e) => setCatalogSearch(e.target.value)}
            placeholder="Search tools..."
            className="bg-clay-900 border-clay-600 text-clay-100 text-xs h-7 pl-7 pr-7"
          />
          {catalogSearch && (
            <button
              onClick={() => setCatalogSearch("")}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-clay-300 hover:text-clay-300"
            >
              <X className="h-3 w-3" />
            </button>
          )}
        </div>

        {filtered && (
          <div className="text-[10px] text-clay-300">
            {filtered.length} of {allTools.length} tools
          </div>
        )}

        <div className="max-h-96 overflow-auto">
          {filtered ? (
            /* Flat filtered list */
            <div className="space-y-1">
              {filtered.map((tool) => (
                <button
                  key={tool.id}
                  onClick={() => onAddStep(tool.id)}
                  className="w-full text-left px-2 py-1.5 rounded text-xs hover:bg-clay-700 transition-colors"
                >
                  <div className="font-medium text-clay-100">{tool.name}</div>
                  <div className="text-[10px] text-clay-300 line-clamp-1">
                    {tool.description}
                  </div>
                </button>
              ))}
              {filtered.length === 0 && (
                <div className="text-xs text-clay-300 py-2 text-center">
                  No tools match &ldquo;{catalogSearch}&rdquo;
                </div>
              )}
            </div>
          ) : (
            /* Category-grouped list */
            toolCategories.map((cat) => (
              <div key={cat.category} className="mb-3">
                <div className="text-[10px] text-clay-300 uppercase tracking-wider mb-1">
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
                      <div className="text-[10px] text-clay-300 line-clamp-1">
                        {tool.description}
                      </div>
                    </button>
                  ))}
                </div>
              </div>
            ))
          )}
        </div>
      </CardContent>
    </Card>
  );
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
  const webhookUrl = `https://clay.nomynoms.com/webhook/functions/${func.id}`;
  const apiKey = (clayConfig?.headers as Record<string, string>)?.["x-api-key"] || "";
  const curlExample = clayConfig?.curl_example as string || "";
  const timeout = (clayConfig?.timeout as number) || 120000;

  return (
    <>
      <div className="space-y-4">
        {/* Clay config preview */}
        <Card className="border-clay-600">
          <CardHeader className="pb-3">
            <CardTitle className="text-sm text-clay-200">Clay HTTP Action Config</CardTitle>
          </CardHeader>
          <CardContent className="space-y-3">
            {/* Webhook URL */}
            <div>
              <div className="text-[10px] text-clay-300 uppercase tracking-wider mb-1 flex items-center gap-1">
                <Globe className="h-3 w-3" /> Webhook URL
              </div>
              <div className="flex items-center gap-1">
                <code className="flex-1 text-xs text-kiln-teal bg-clay-900 px-2 py-1.5 rounded border border-clay-700 truncate">
                  {webhookUrl}
                </code>
                <CopyButton text={webhookUrl} label="URL copied" />
              </div>
            </div>

            {/* Method */}
            <div>
              <div className="text-[10px] text-clay-300 uppercase tracking-wider mb-1">
                Method
              </div>
              <code className="text-xs text-clay-200 bg-clay-900 px-2 py-1 rounded border border-clay-700">
                POST
              </code>
            </div>

            {/* Headers */}
            <div>
              <div className="text-[10px] text-clay-300 uppercase tracking-wider mb-1 flex items-center gap-1">
                <Key className="h-3 w-3" /> Headers
              </div>
              <div className="bg-clay-900 rounded border border-clay-700 divide-y divide-clay-700">
                <div className="flex items-center justify-between px-2 py-1.5">
                  <code className="text-[10px] text-clay-300">
                    Content-Type: <span className="text-clay-200">application/json</span>
                  </code>
                  <CopyButton text="application/json" label="Header copied" />
                </div>
                <div className="flex items-center justify-between px-2 py-1.5">
                  <code className="text-[10px] text-clay-300 truncate mr-1">
                    x-api-key: <span className="text-kiln-teal">{apiKey ? `${apiKey.slice(0, 8)}...${apiKey.slice(-4)}` : "Loading..."}</span>
                  </code>
                  <CopyButton text={apiKey} label="API key copied" />
                </div>
              </div>
            </div>

            {/* Timeout */}
            <div>
              <div className="text-[10px] text-clay-300 uppercase tracking-wider mb-1 flex items-center gap-1">
                <Clock className="h-3 w-3" /> Timeout
              </div>
              <code className="text-xs text-clay-200 bg-clay-900 px-2 py-1 rounded border border-clay-700">
                {timeout}ms ({timeout / 60000} min)
              </code>
            </div>

            {/* Body Template */}
            <div>
              <div className="text-[10px] text-clay-300 uppercase tracking-wider mb-1">
                Body Template
              </div>
              <pre className="text-[10px] text-clay-300 bg-clay-900 p-2 rounded border border-clay-700 overflow-auto max-h-32">
                {JSON.stringify(
                  {
                    data: Object.fromEntries(
                      inputs.map((i) => [i.name, `/Column Name`])
                    ),
                  },
                  null,
                  2
                )}
              </pre>
              <p className="text-[10px] text-clay-300 mt-1">
                Replace <code className="text-clay-300">/Column Name</code> with your actual Clay column names using <code className="text-clay-300">/</code> prefix
              </p>
            </div>

            {/* Curl Example */}
            {curlExample && (
              <div>
                <div className="text-[10px] text-clay-300 uppercase tracking-wider mb-1 flex items-center gap-1">
                  <Terminal className="h-3 w-3" /> Quick Test (curl)
                </div>
                <div className="relative">
                  <pre className="text-[10px] text-clay-300 bg-clay-900 p-2 rounded border border-clay-700 overflow-auto max-h-32 pr-8">
                    {curlExample}
                  </pre>
                  <div className="absolute top-1 right-1">
                    <CopyButton text={curlExample} label="curl command copied" />
                  </div>
                </div>
              </div>
            )}

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
          <ToolCatalogPanel
            toolCategories={toolCategories}
            onAddStep={onAddStep}
          />
        )}

        {/* Metadata */}
        <Card className="border-clay-600">
          <CardContent className="p-4 text-xs text-clay-300 space-y-1">
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
                <span className="text-xs text-clay-300">
                  Step {clayWizardStep + 1} of 4
                </span>
                <Button
                  variant="ghost"
                  size="sm"
                  onClick={() => setClayWizardOpen(false)}
                  className="text-clay-300"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            <div className="p-6">
              {/* Step 1: Create column */}
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
                      <div className="text-xs text-clay-300">
                        Add a new column and select &quot;HTTP API&quot; as the type
                      </div>
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

              {/* Step 2: URL + Headers + Timeout */}
              {clayWizardStep === 1 && (
                <div className="space-y-4">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="h-8 w-8 rounded-full bg-kiln-teal/10 flex items-center justify-center text-kiln-teal font-bold text-sm">
                      2
                    </div>
                    <div>
                      <div className="text-sm font-medium text-clay-100">
                        Configure the request
                      </div>
                      <div className="text-xs text-clay-300">
                        Set the URL, headers, and timeout
                      </div>
                    </div>
                  </div>

                  <div className="space-y-3">
                    {/* URL */}
                    <div className="bg-clay-900 rounded-lg p-3">
                      <div className="text-[10px] text-clay-300 uppercase tracking-wider mb-1">Method & URL</div>
                      <div className="flex items-center gap-2">
                        <span className="text-xs font-mono text-emerald-400 bg-clay-800 px-2 py-0.5 rounded">POST</span>
                        <code className="text-xs text-kiln-teal flex-1 truncate">{webhookUrl}</code>
                        <CopyButton text={webhookUrl} label="URL copied" />
                      </div>
                    </div>

                    {/* Headers */}
                    <div className="bg-clay-900 rounded-lg p-3">
                      <div className="text-[10px] text-clay-300 uppercase tracking-wider mb-2">Headers (add both)</div>
                      <div className="space-y-2">
                        <div className="flex items-center gap-2">
                          <code className="text-[10px] text-clay-300 flex-1">
                            <span className="text-clay-300">Content-Type:</span> application/json
                          </code>
                          <CopyButton text="application/json" label="Copied" />
                        </div>
                        <div className="flex items-center gap-2">
                          <code className="text-[10px] text-clay-300 flex-1 truncate">
                            <span className="text-clay-300">x-api-key:</span>{" "}
                            <span className="text-kiln-teal">{apiKey}</span>
                          </code>
                          <CopyButton text={apiKey} label="API key copied" />
                        </div>
                      </div>
                    </div>

                    {/* Timeout */}
                    <div className="bg-clay-900 rounded-lg p-3">
                      <div className="text-[10px] text-clay-300 uppercase tracking-wider mb-1">Timeout</div>
                      <code className="text-xs text-clay-200">{timeout}</code>
                      <span className="text-[10px] text-clay-300 ml-2">({timeout / 60000} minutes)</span>
                    </div>
                  </div>
                </div>
              )}

              {/* Step 3: Body + Column Mapping */}
              {clayWizardStep === 2 && (
                <div className="space-y-4">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="h-8 w-8 rounded-full bg-kiln-teal/10 flex items-center justify-center text-kiln-teal font-bold text-sm">
                      3
                    </div>
                    <div>
                      <div className="text-sm font-medium text-clay-100">
                        Set the body & map columns
                      </div>
                      <div className="text-xs text-clay-300">
                        Paste the body and replace column references
                      </div>
                    </div>
                  </div>

                  <div className="bg-clay-900 rounded-lg p-3">
                    <div className="text-[10px] text-clay-300 uppercase tracking-wider mb-2">Body (JSON)</div>
                    <pre className="text-[10px] text-clay-300 overflow-auto max-h-32">
                      {JSON.stringify(
                        clayConfig.body_template || { data: {} },
                        null,
                        2
                      )}
                    </pre>
                  </div>
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
                      toast.success("Body template copied!");
                    }}
                    className="w-full bg-kiln-teal text-clay-950 hover:bg-kiln-teal-light"
                  >
                    <Copy className="h-3.5 w-3.5 mr-2" />
                    Copy Body Template
                  </Button>

                  <div className="bg-clay-900/50 rounded-lg p-3 border border-clay-700">
                    <div className="text-[10px] text-clay-300 mb-2">Replace the placeholder values with your Clay column references:</div>
                    <div className="space-y-1">
                      {func.inputs.map((inp) => (
                        <div key={inp.name} className="flex items-center gap-2 text-[10px]">
                          <code className="text-clay-300">/{'{{Column Name}}'}</code>
                          <span className="text-clay-300">→</span>
                          <code className="text-kiln-teal">/Your {inp.name.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase())} Column</code>
                          {inp.required && <span className="text-red-400">required</span>}
                        </div>
                      ))}
                    </div>
                  </div>
                </div>
              )}

              {/* Step 4: Outputs + Test */}
              {clayWizardStep === 3 && (
                <div className="space-y-4">
                  <div className="flex items-center gap-3 mb-4">
                    <div className="h-8 w-8 rounded-full bg-kiln-teal/10 flex items-center justify-center text-kiln-teal font-bold text-sm">
                      4
                    </div>
                    <div>
                      <div className="text-sm font-medium text-clay-100">
                        Map outputs & test
                      </div>
                      <div className="text-xs text-clay-300">
                        Map response fields to Clay columns, then run on one row
                      </div>
                    </div>
                  </div>

                  {/* Output mapping */}
                  <div>
                    <div className="text-xs text-clay-300 uppercase tracking-wider mb-1">
                      Output Columns (Function → Clay)
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
                          <span className="text-clay-300">→</span>
                          <span className="text-clay-200">
                            {out.key} ({out.type})
                          </span>
                        </div>
                      ))}
                      {func.outputs.length === 0 && (
                        <div className="px-3 py-2 text-xs text-clay-300">
                          No outputs defined yet
                        </div>
                      )}
                    </div>
                  </div>

                  {/* Curl test */}
                  {curlExample && (
                    <div>
                      <div className="text-xs text-clay-300 uppercase tracking-wider mb-1 flex items-center gap-1">
                        <Terminal className="h-3 w-3" /> Quick Test
                      </div>
                      <div className="relative">
                        <pre className="text-[10px] text-clay-300 bg-clay-900 p-3 rounded-lg overflow-auto max-h-32 pr-8">
                          {curlExample}
                        </pre>
                        <div className="absolute top-1 right-1">
                          <CopyButton text={curlExample} label="curl copied" />
                        </div>
                      </div>
                      <p className="text-[10px] text-clay-300 mt-1">
                        Run this in your terminal to verify the function works before enabling in Clay
                      </p>
                    </div>
                  )}
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
              {clayWizardStep < 3 ? (
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
