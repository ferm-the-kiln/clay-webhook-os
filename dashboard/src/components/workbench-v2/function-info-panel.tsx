"use client";

import type { FunctionDefinition } from "@/lib/types";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import {
  ArrowRightLeft,
  Layers,
  FolderOpen,
  CircleDot,
  ArrowDownRight,
} from "lucide-react";

interface FunctionInfoPanelProps {
  func: FunctionDefinition;
}

export function FunctionInfoPanel({ func }: FunctionInfoPanelProps) {
  const requiredInputs = func.inputs.filter((i) => i.required);

  return (
    <Card className="bg-clay-900/50 border-clay-700">
      <CardContent className="p-4">
        <Tabs defaultValue="overview">
          <TabsList variant="line" className="mb-3">
            <TabsTrigger value="overview">Overview</TabsTrigger>
            <TabsTrigger value="inputs">
              Inputs ({func.inputs.length})
            </TabsTrigger>
            <TabsTrigger value="outputs">
              Outputs ({func.outputs.length})
            </TabsTrigger>
            {func.steps.length > 0 && (
              <TabsTrigger value="pipeline">
                Pipeline ({func.steps.length})
              </TabsTrigger>
            )}
          </TabsList>

          <TabsContent value="overview">
            {func.description && (
              <p className="text-sm text-clay-200 mb-3">{func.description}</p>
            )}
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-2">
              <StatCard
                icon={<ArrowRightLeft className="h-3.5 w-3.5 text-kiln-teal" />}
                label="Inputs"
                value={`${requiredInputs.length} required / ${func.inputs.length} total`}
              />
              <StatCard
                icon={<ArrowDownRight className="h-3.5 w-3.5 text-kiln-teal" />}
                label="Outputs"
                value={String(func.outputs.length)}
              />
              <StatCard
                icon={<Layers className="h-3.5 w-3.5 text-kiln-teal" />}
                label="Steps"
                value={String(func.steps.length)}
              />
              <StatCard
                icon={<FolderOpen className="h-3.5 w-3.5 text-kiln-teal" />}
                label="Folder"
                value={func.folder || "—"}
              />
            </div>
          </TabsContent>

          <TabsContent value="inputs">
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-clay-700">
                    <th className="text-left py-1.5 pr-3 text-clay-400 font-medium">
                      Field
                    </th>
                    <th className="text-left py-1.5 pr-3 text-clay-400 font-medium">
                      Type
                    </th>
                    <th className="text-left py-1.5 pr-3 text-clay-400 font-medium">
                      Required
                    </th>
                    <th className="text-left py-1.5 text-clay-400 font-medium">
                      Description
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {func.inputs.map((input) => (
                    <tr
                      key={input.name}
                      className="border-b border-clay-700/50"
                    >
                      <td className="py-1.5 pr-3 font-mono text-clay-100">
                        {input.name}
                      </td>
                      <td className="py-1.5 pr-3">
                        <Badge variant="secondary" className="text-[10px]">
                          {input.type}
                        </Badge>
                      </td>
                      <td className="py-1.5 pr-3">
                        {input.required ? (
                          <Badge className="text-[10px] bg-kiln-teal/15 text-kiln-teal border-kiln-teal/25">
                            required
                          </Badge>
                        ) : (
                          <span className="text-clay-500">optional</span>
                        )}
                      </td>
                      <td className="py-1.5 text-clay-300">
                        {input.description || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </TabsContent>

          <TabsContent value="outputs">
            <div className="overflow-x-auto">
              <table className="w-full text-xs">
                <thead>
                  <tr className="border-b border-clay-700">
                    <th className="text-left py-1.5 pr-3 text-clay-400 font-medium">
                      Key
                    </th>
                    <th className="text-left py-1.5 pr-3 text-clay-400 font-medium">
                      Type
                    </th>
                    <th className="text-left py-1.5 text-clay-400 font-medium">
                      Description
                    </th>
                  </tr>
                </thead>
                <tbody>
                  {func.outputs.map((output) => (
                    <tr
                      key={output.key}
                      className="border-b border-clay-700/50"
                    >
                      <td className="py-1.5 pr-3 font-mono text-kiln-teal">
                        {output.key}
                      </td>
                      <td className="py-1.5 pr-3">
                        <Badge variant="secondary" className="text-[10px]">
                          {output.type}
                        </Badge>
                      </td>
                      <td className="py-1.5 text-clay-300">
                        {output.description || "—"}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </TabsContent>

          {func.steps.length > 0 && (
            <TabsContent value="pipeline">
              <div className="space-y-0">
                {func.steps.map((step, i) => (
                  <div key={i} className="flex gap-3">
                    {/* Timeline */}
                    <div className="flex flex-col items-center">
                      <div className="flex items-center justify-center h-6 w-6 rounded-full bg-clay-800 border border-clay-600 text-[10px] font-bold text-kiln-teal shrink-0">
                        {i + 1}
                      </div>
                      {i < func.steps.length - 1 && (
                        <div className="w-px flex-1 bg-clay-700 min-h-[16px]" />
                      )}
                    </div>
                    {/* Content */}
                    <div className="pb-3 min-w-0">
                      <div className="flex items-center gap-2">
                        <span className="text-sm font-medium text-clay-100">
                          {formatToolName(step.tool)}
                        </span>
                      </div>
                      {Object.keys(step.params).length > 0 && (
                        <div className="mt-1 flex flex-wrap gap-1">
                          {Object.entries(step.params).map(([k, v]) => (
                            <span
                              key={k}
                              className="text-[10px] text-clay-400 bg-clay-800 rounded px-1.5 py-0.5"
                            >
                              {k}={v}
                            </span>
                          ))}
                        </div>
                      )}
                    </div>
                  </div>
                ))}
              </div>
            </TabsContent>
          )}
        </Tabs>
      </CardContent>
    </Card>
  );
}

function StatCard({
  icon,
  label,
  value,
}: {
  icon: React.ReactNode;
  label: string;
  value: string;
}) {
  return (
    <div className="bg-clay-800/60 rounded-lg px-3 py-2">
      <div className="flex items-center gap-1.5 mb-0.5">
        {icon}
        <span className="text-[10px] text-clay-400 uppercase tracking-wider">
          {label}
        </span>
      </div>
      <div className="text-sm font-medium text-clay-100">{value}</div>
    </div>
  );
}

function formatToolName(tool: string): string {
  if (tool.startsWith("skill:")) return tool;
  return tool
    .split(/[-_]/)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");
}
